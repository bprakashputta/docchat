# Module 1: acquire (design)

**Status:** design, awaiting approval.
**Container:** `worker`, which this module introduces. It runs as a one-off job
(`docker compose run --rm worker python -m backend.acquire --phase 1`) or locally with
`uv run python -m backend.acquire --phase 1`.

## 1. Goal
Download the Phase 1 source data from SEC EDGAR and record what was downloaded in
Postgres, so the ingest module has a reliable list of filings to work from.

**In scope:**
- `data/universe.csv`
- An EDGAR HTTP client with rate limiting and retries
- Picking which filings to download, and downloading them
- Loading XBRL `companyfacts` into the `facts` table
- Alembic migrations for `companies`, `filings` and `facts`

**Out of scope:**
- Parsing, chunking and embedding (Module 2)
- Phases 2 and 3
- Scheduled runs (Stage 3)

## 2. Inputs and outputs
**Input:** `data/universe.csv` with the columns `ticker, name, cik, filer_type,
index_weight, phase`. Phase 1 has the 10 largest constituents by weight; the list is
confirmed against current weights before the first run. Rows are deduplicated by CIK, so
GOOGL and GOOG count as one company.

**Outputs:**
- `data/raw/{ticker}/{form}_{period}.htm`, where the period is `FY2025` for a 10-K and
  `FY2026Q1` for a 10-Q. Examples: `10-K_FY2025.htm`, `10-Q_FY2026Q1.htm`.
- `data/raw/{ticker}/companyfacts.json`: the raw cache.
- Database rows in `companies`, `filings` and `facts`. Postgres replaces the per-ticker
  `manifest.json` the README mentions: one source of truth that can be queried.

## 3. EDGAR endpoints
| Purpose | URL |
|---|---|
| Ticker → CIK | `https://www.sec.gov/files/company_tickers.json` |
| List a company's filings | `https://data.sec.gov/submissions/CIK{cik:010d}.json` |
| Download a filing document | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primaryDocument}` |
| XBRL facts | `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json` |

## 4. Code layout
```
backend/acquire/
  __main__.py      CLI: argument parsing, runs the pipeline, prints a summary
  edgar_client.py  EdgarClient: User-Agent, rate limiter, retries, download to disk
  universe.py      reads and validates universe.csv, dedupes by CIK
  filings.py       picks which filings to download from the submissions JSON
  xbrl.py          parses companyfacts into rows and upserts them into facts
backend/app/models.py   SQLAlchemy models: Company, Filing, Fact
migrations/             Alembic
docker/worker.Dockerfile
```

## 5. Key design decisions
1. **Rate limiting.** A token bucket allows about 8 requests per second, under SEC's
   limit of 10. Every request goes through one `EdgarClient`, so the limit can't be
   bypassed.
2. **Retries.**
   - **429 and 5xx:** exponential backoff with jitter, honoring `Retry-After`, up to
     5 attempts.
   - **403:** fail fast with a clear message. A 403 from EDGAR usually means a missing
     or bad `SEC_USER_AGENT`, and retrying won't fix that.
3. **Idempotency.**
   - If a file already exists, it's skipped.
   - Every database write is an upsert (`ON CONFLICT`).
   - Re-running is always safe, and a warm re-run makes no document downloads.
   - `--refresh-facts` re-downloads `companyfacts.json`, which changes when a company
     files.
4. **Picking filings.**
   - Use `filings.recent` from the submissions JSON.
   - Keep the latest `10-K` and the two latest `10-Q`s.
   - Exclude amendments (`10-K/A`, `10-Q/A`).
   - 20-F filers are skipped in Phase 1 and logged.
5. **Fiscal year and quarter.** These come from `companyfacts`. Each fact carries `fy`,
   `fp` and `accn`, so matching on accession number gives the company's own fiscal
   labels. Apple's fiscal year ends in September, so calendar dates would mislabel it.
6. **Streaming downloads.** Documents (10-Ks run 5–15 MB) are streamed to a temporary
   file and renamed into place when complete. A crash mid-download never leaves a
   partial file that a re-run would wrongly skip.
7. **Sync, not async.**
   - Phase 1 is about 51 requests.
   - The rate limit, not the concurrency model, is what caps throughput.
   - Sync code is simpler to read and debug.
   - We revisit this in Phase 2, when there are about 500 requests.

## 6. Data model
- **companies:** `cik` (primary key), `ticker`, `name`, `filer_type`, `index_weight`
- **filings:**
  - `accession_no` (primary key), `cik` (foreign key), `form`
  - `fiscal_year`, `fiscal_quarter` (null for a 10-K), `period_end`, `filed_date`
  - `url`, `local_path`, `downloaded_at`
- **facts:**
  - `cik`, `taxonomy` (us-gaap or dei), `concept`, `unit`, `value`
  - `period_start` (null for point-in-time facts), `period_end`
  - `fy`, `fp`, `form`, `accession_no`, `filed_date`
  - **Unique key:** `(cik, taxonomy, concept, unit, period_end, period_start,
    accession_no)`. The same value appears once for each filing that reports it. We
    keep every row and query the latest `filed_date`, which also keeps restatements.
  - **Index:** `(cik, concept, period_end)` for numeric lookups.

## 7. Performance budget
| Metric | Budget | Basis |
|---|---|---|
| Cold Phase 1 run | < 2 min | about 51 requests at ≤8/s, plus about 150 MB of downloads |
| Warm re-run | < 10 s | submissions JSON only, no document downloads |
| Peak memory | < 300 MB | downloads stream to disk; companyfacts is parsed per company |
| Facts load | O(n) in the number of facts | batched upserts of 1,000 rows each |

## 8. Tests
`respx` mocks httpx, so tests never touch the network.
- **Rate limiter:** spacing between requests
- **Retries:** 429 then 200 succeeds; a 403 fails immediately; `Retry-After` is honored
- **Filing selection:** latest 10-K, two latest 10-Qs, amendments excluded
- **Universe:** CIK zero-padding, deduplicating GOOG and GOOGL
- **Idempotency:** a second run makes no downloads and inserts no duplicate rows
- **XBRL parsing:** a small fixture of companyfacts data produces the expected rows
- **Integration:** an end-to-end run against the Docker database using mocked HTTP

## 9. Before building
- `SEC_USER_AGENT` must be added to `.env`, in the format `Name email@example.com`.
- The Phase 1 top-10 list must be confirmed against current Nasdaq-100 weights.
- This design gets an EGM review (`/egm:egm-review docs/01-acquire.md`).
