# Stage 5: Initial Zoom Out (docs/01-acquire.md)

**Reviewers:** zoom-out and inventive-catalyst, run independently with no conversation
history.
**Standard:** zoom-out-standard.
**Target:** full file, lines 1–126.
**Context:** README.md, backend/app/config.py, backend/app/db.py.
**Verdict:** approve with changes. There is 1 blocker (both reviewers found it), 7 major
findings and 9 nits.

Duplicate findings are merged below. The tag after each title shows which reviewer
raised it: ZO = zoom-out, IC = inventive-catalyst.

---

## 🔴 Blocker

### B1. A nullable `period_start` in the facts unique key breaks idempotency (ZO-M3, IC-B1)
- **Where:** lines 98, 100–102. This conflicts with line 69 ("every write is an upsert")
  and line 119 ("no duplicate rows").
- **Problem:**
  - `period_start` is null for point-in-time facts such as balance-sheet items.
  - By default, Postgres treats NULLs as distinct in a unique constraint, so
    `ON CONFLICT` never matches those rows.
  - Every re-run therefore inserts the point-in-time facts again.
- **Related problem:** if two source entries in the same 1,000-row batch map to the same
  key, `ON CONFLICT DO UPDATE` fails with "cannot affect row a second time".
- **Fix:**
  - Use `UNIQUE NULLS NOT DISTINCT`, which works on pg15+ (we run pg16).
  - Deduplicate each batch by key before the upsert.
  - Add a re-run test whose fixture includes a point-in-time fact.

## 🟡 Major

### M1. "Sync, not async" ignores the async-only database layer (ZO-M1, IC-M1)
- **Where:** lines 84–88 and 53–54.
- **Problem:**
  - `db.py` provides only `create_async_engine`, and `config.py` defaults to the
    `asyncpg` driver.
  - A sync worker therefore needs either a second engine and driver (psycopg) or
    `asyncio.run` wrappers. Alembic's `env.py` faces the same choice.
  - The design doesn't say which.
- **Fix:** pick one of these and state it:
  - (a) Sync httpx for EDGAR, with database writes through the existing async engine
    (one `asyncio.run` at the CLI).
  - (b) An async worker that runs strictly one request at a time, using
    `httpx.AsyncClient` and reusing `SessionLocal`.
  - (c) Keep sync, add a sync engine derived from the same URL, and say why.

### M2. File naming depends on companyfacts, but the run order and fallback aren't stated (ZO-M4, IC-M2)
- **Where:** lines 31–32, 78–80 and 51–52.
- **Problem:**
  - A label like `FY2026Q1` needs companyfacts to be fetched first, but the pipeline
    order isn't written down.
  - Nothing says what happens when an accession number is missing from companyfacts,
    for example a 10-Q that has just been filed.
  - The skip-if-exists check uses the derived path, so if a label changes, the file is
    downloaded again.
- **Fix:**
  - State the order for each company: submissions, then companyfacts, then select and
    label, then download.
  - Add a fallback for a missing label: fail loudly, or derive it from the
    submissions `reportDate` and `fiscalYearEnd`.
  - Consider using the accession number as the file name and as the idempotency key,
    with the fiscal label kept as metadata.

### M3. The filesystem and Postgres both act as source of truth, with no reconciliation (IC-M3)
- **Where:** lines 34–35, 68 and 95.
- **Problem:**
  - A crash after the file rename but before the database upsert leaves a file with no
    row. Ingest then silently misses that filing.
  - The reverse case, a row whose file is missing, isn't handled either.
- **Fix:**
  - Always upsert the `filings` row from submissions metadata, even when the download is
    skipped.
  - Download only when `downloaded_at` is null or the file is missing.

### M4. Host and container runs disagree on paths and the database host (ZO-M2, IC-M4)
- **Where:** lines 4–6 and 95, and `config.py` line 17.
- **Problem:**
  - Inside Compose, the database is reached at `db:5432`, not `localhost:5433`.
  - An absolute `local_path` written by the container (`/app/data/...`) won't resolve on
    the host, and the reverse is also true.
- **Fix:**
  - Store `local_path` relative to a `data_root` setting.
  - State that Compose sets `DATABASE_URL` for the worker.

### M5. A worker container and Dockerfile are premature for Module 1 (ZO-M2, IC-N3)
- **Where:** lines 4 and 55.
- **Problem:** Phase 1 is a one-off job of about 51 requests. Scheduled runs are out of
  scope (line 22), and `uv run python -m backend.acquire` already covers it.
- **Fix:** defer `worker.Dockerfile` until scheduled runs arrive, or reuse the backend
  image with a different command.

### M6. `facts.fy` and `facts.fp` label the filing, not the fact's period (IC-M5)
- **Where:** lines 99 and 102.
- **Problem:** a FY2025 10-K tags its FY2024 and FY2023 comparative figures with
  `fy=2025`. A Block 5 query for "FY2025 revenue" filtered on `fy=2025` would return
  three values.
- **Fix:**
  - State that lookups go by `period_start` and `period_end`, taking the latest
    `filed_date` for each period.
  - Treat `fy` and `fp` as provenance only, and consider renaming them `filing_fy` and
    `filing_fp`.

### M7. What happens on a partial failure isn't defined (IC-M6)
- **Where:** lines 62–66 and 48.
- **Problem:** the design doesn't say what happens after 5 failed retries, or when one
  company fails. Does the run abort or continue? What exit code does it return?
- **Fix:**
  - Treat each company as its own unit of work in its own transaction.
  - Keep going after a company fails, and list the failures in the summary.
  - Exit non-zero if any company failed. A 403 still aborts the whole run.

## 🟢 Nits

| # | Finding | Lines | Source |
|---|---|---|---|
| N1 | Validate `SEC_USER_AGENT` (present, in `Name email` format) from `get_settings()` at CLI start, instead of waiting for a 403 | 65–66, 124 | ZO-N4, IC-N1 |
| N2 | The `company_tickers.json` endpoint has no stated use, since the CSV already has CIKs. Drop it, or say it's only used to validate the CSV | 40 | ZO-N1, IC-N4 |
| N3 | A minimum gap between requests (~125 ms) is simpler than a token bucket for a single-threaded client | 59 | ZO-N2 |
| N4 | Consider `tenacity` for retries instead of hand-written backoff, or say the hand-rolling is deliberate practice | 62–66 | ZO-N3 |
| N5 | Budget rows: "O(n)" isn't a budget; check 300 MB against a `json.load` of the largest companyfacts file; the ~150 MB download figure includes companyfacts | 108–111 | ZO-N5, IC-N5 |
| N6 | The worker needs the Anthropic and Voyage keys only because Settings requires them. State this, or split the settings | 4 | IC-N2 |
| N7 | Just after a 10-K is filed, the "two latest 10-Qs" may belong to the previous fiscal year. State that this is intended | 75–76 | IC-N6 |
| N8 | "Stage 3" isn't defined in this document; the README uses Blocks and Phases | 22 | ZO-N6 |
| N9 | The EGM-review line is a workflow note, not a design prerequisite | 126 | ZO-N7 |

## What survived scrutiny
- Postgres replacing `manifest.json` as the record of what was downloaded.
- One `EdgarClient` that every request goes through, so the rate limit can't be skipped.
- Downloading to a temporary file and renaming it when complete.
- Fiscal labels taken from XBRL rather than calendar dates (Apple's year ends in
  September).
- Sync code for a small workload, once M1's database path is settled.
