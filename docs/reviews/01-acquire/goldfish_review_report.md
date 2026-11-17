# Goldfish Annotated Review Report

**Target:** `docs/01-acquire.md` (lines 1–44 for Stage 7). Some fixes reach into §4–§9
because the finding spans the whole document; this is noted per item.
**Source:** [critic_report.md](critic_report.md), round 1.
**Tally:** 17 proposed fixes, 2 declined nits, 0 contested, 0 escalated. Two findings
carried over from Stage 5 are also proposed as fixes.

---

## Prioritized Findings & AI Suggestions

### [Issue 1] [`design`, `structural`]: Severity: Blocker (K1)
*   **Affected Scope:** whole document
*   **Discrepancy Description:** There is no "Alternatives considered" section and no
    "Risks and mitigations" section.
*   **Rationale:** The feature-spec standard fails a spec that proposes a single path
    without saying which alternatives it rejected.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** This is valid. The choices were all made in our conversation
    but never written into the doc, so a reader can't see why each option lost.
*   ***Proposed Edit:***
    *   Location: new sections, `## 8. Alternatives considered` and
        `## 9. Risks and mitigations`, inserted before "Tests". Later sections are
        renumbered.
    *   Change, alternatives table:
        | Decision | Chosen | Rejected | Why |
        |---|---|---|---|
        | Download record | Postgres `filings` table | `manifest.json` per ticker; filesystem only | Ingest and the API query it; one place to check; upserts make re-runs safe |
        | Universe | Committed CSV | Live lookup of index members | No free official API for index weights; a CSV is reviewable and reproducible |
        | Concurrency | Async, one request at a time | Sync httpx with a second sync database engine; concurrent async | Reuses the existing async `db.py`; one driver; the rate limit caps throughput anyway |
        | Rate limiter | Fixed minimum gap (125 ms) | Token bucket | A single sequential client never bursts, so a gap gives the same guarantee with less code |
        | Where it runs | `worker` container (also runnable with `uv run`) | API container; local only | Keeps heavy parsing and download jobs away from live chat (CLAUDE.md §1); same image runs on a schedule later |
        | File name | `{form}_{report_date}.htm` | `{form}_{fiscal label}.htm`; accession number | The report date is known when the filing is selected, so naming no longer depends on companyfacts; still readable |
    *   Change, risks list:
        - EDGAR blocks a bad User-Agent (403). The CLI validates `SEC_USER_AGENT` at
          start and aborts the run on a 403.
        - Throttling (429). Backoff that honors `Retry-After`; at most 8 requests per
          second.
        - A crash mid-download. Write to a temp file, then rename.
        - Disk and database drift apart. The database is authoritative; see the
          reconciliation rule in §5.
        - Ticker renames. CIK validation at start; folders follow the CSV ticker.
        - companyfacts lags a new filing. The fiscal labels stay null and are filled
          on a later run.
        - Phase 2 is about 10× the requests. Same code; revisit concurrency then.

### [Issue 2] [`design`, `structural`, `style`]: Severity: Major (K2)
*   **Affected Scope:** [Lines 34-35](../../01-acquire.md#L34-L35) (Outputs)
*   **Discrepancy Description:** The doc says the README mentions `manifest.json`. It
    doesn't.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** This is valid. The manifest idea came from planning
    discussion, not from the README.
*   ***Proposed Edit:*** "Postgres replaces the per-ticker `manifest.json` the README
    mentions…" → "Rows in `companies`, `filings` and `facts`. The `filings` table is
    the record of what was downloaded; ingest reads it instead of scanning folders."

### [Issue 3] [`structural`, `style`]: Severity: Major (K3)
*   **Affected Scope:** [Lines 1-22](../../01-acquire.md#L1-L22)
*   **Discrepancy Description:** Module, Block, Stage and Phase are mixed, and
    "Stage 3" is undefined.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** This is a comprehension gap, so it can't be contested.
    "Stage" comes from a roadmap that was never written down, and the README's
    "Block" numbering predates the module order.
*   ***Proposed Edit:*** Add a short "Terms" line under the title:
    - **Module 1** is the README's **Block 2** (data acquisition). **Module 2** is
      ingest (Block 3).
    - **Phase** is data scope, as in the README.
    - "Stage 3" → "scheduled runs (a later roadmap item)".
    - Separately, the README's build plan needs updating to the module order in
      CLAUDE.md. That's outside this doc and tracked as a follow-up.

### [Issue 4] [`design`, `structural`, `style`]: Severity: Major (K4)
*   **Affected Scope:** [Lines 25, 40](../../01-acquire.md#L25-L40)
*   **Discrepancy Description:** The ticker → CIK endpoint has no stated use, and
    there's no policy for a mismatch.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Add a "Used for" column to the endpoint table. For
    `company_tickers.json`: "Validate the CSV once per run. If a CSV ticker maps to a
    different CIK, or is missing, abort and print the mismatch. The CSV is never
    overwritten."

### [Issue 5] [`design`, `style`]: Severity: Major (K5)
*   **Affected Scope:** [Lines 25-28](../../01-acquire.md#L25-L28)
*   **Discrepancy Description:** Is it 10 tickers or 10 CIKs? Which ticker survives
    deduplication? Where do the weights come from?
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:***
    - The CSV holds **one row per company (CIK)**, using the class-A ticker (GOOGL,
      not GOOG). Combined weights for multi-class companies are summed by hand.
    - The loader rejects duplicate CIKs instead of silently merging them, so the
      folder name is always the CSV ticker.
    - Phase 1 means the 10 largest distinct companies.
    - Weights come from the Invesco QQQ holdings file, which tracks the
      Nasdaq-100. The as-of date goes in an `as_of` column.

### [Issue 6] [`design`]: Severity: Major (K6)
*   **Affected Scope:** [Lines 3-6, 31-33](../../01-acquire.md#L3-L33)
*   **Discrepancy Description:** As written, the container run loses its data and
    can't reach the database.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Add a "Running in the container" paragraph:
    - The compose `worker` service uses `env_file: .env`, and overrides
      `DATABASE_URL` with `db:5432`.
    - It bind-mounts `./data:/app/data`.
    - `filings.local_path` is stored relative to a new `data_dir` setting, so paths
      resolve the same on the host and in the container.
    - The worker gets the full `.env` (including the AI keys) because `Settings`
      requires them. This is acceptable for local development.

### [Issue 7] [`design`]: Severity: Major (K7)
*   **Affected Scope:** [Line 17](../../01-acquire.md#L17) and §5.7
*   **Discrepancy Description:** The worker is sync, but the database layer is
    async-only, and the doc doesn't say which driver Alembic uses.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Replace §5.7 "Sync, not async" with **"Async, one request at
    a time"**:
    - `httpx.AsyncClient` with no `gather` or fan-out.
    - Reuses `db.py`'s engine and `SessionLocal`.
    - Alembic uses the async `env.py` template (`alembic init -t async`).
    - One driver (asyncpg) and one `DATABASE_URL`.

### [Issue 8] [`design`]: Severity: Major (K8)
*   **Affected Scope:** [Lines 34-35](../../01-acquire.md#L34-L35) and §5.3
*   **Discrepancy Description:** Disk and database both act as the source of truth,
    with no reconciliation.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Add a reconciliation rule to §5.3:
    - Postgres is authoritative.
    - Every run upserts each selected filing's row from the submissions data,
      whether or not it downloads.
    - Download a filing only if its file is missing on disk. Then set
      `downloaded_at`.

### [Issue 9] [`design`, `style`]: Severity: Major (K9)
*   **Affected Scope:** [Lines 31-32](../../01-acquire.md#L31-L32) and §5.5
*   **Discrepancy Description:** The file name depends on companyfacts fetched later,
    with no fallback. The labels are fiscal, but the doc doesn't say so.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:***
    - File name becomes `data/raw/{ticker}/{form}_{report_date}.htm`, for example
      `10-Q_2026-03-28.htm`. The report date is taken from the submissions JSON.
    - `fiscal_year` and `fiscal_quarter` become database columns only. They're the
      company's fiscal labels, filled from companyfacts.
    - If no fact matches, both stay null and a warning is logged.
    - State the order for each company: submissions → select → upsert rows →
      download → companyfacts → fill labels.

### [Issue 10] [`structural`]: Severity: Major (K10)
*   **Affected Scope:** [Lines 8-10](../../01-acquire.md#L8-L10)
*   **Discrepancy Description:** There's no problem statement.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Add a "Why" paragraph to §1:
    - DocChat answers questions from SEC filings, and numeric answers must come from
      reported XBRL data.
    - EDGAR has strict access rules: a User-Agent on every request and at most 10
      requests per second.
    - Downloading once and recording each file in Postgres lets ingest re-run
      without hitting EDGAR again.

### [Issue 11] [`design`, `style`]: Severity: Nit (K11), proposed because Stage 5 rated it Major
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Add a "Done when" line to §1: 10 companies, 30 filings and
    their facts loaded.
*   Each company is its own unit of work. A failure is logged, the run continues,
    the summary lists the failures, and the run exits with a non-zero code. A 403
    aborts the whole run.

### [Issue 12] [`design`, `style`]: Severity: Nit (K12)
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Define the CSV columns:
    - `filer_type`: `10-K` or `20-F`. 20-F rows are skipped in Phase 1.
    - `phase`: an integer. `--phase N` selects rows with `phase <= N`.
    - `index_weight`: a percentage.
*   The CSV is committed to git. For now it holds only the Phase 1 rows.

### [Issue 13] [`design`, `structural`, `style`]: Severity: Nit (K13)
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Add a one-line legend under the endpoint table:
    - `{cik:010d}` is the 10-digit, zero-padded CIK.
    - The Archives paths use the unpadded CIK.
    - `primaryDocument` and `reportDate` are fields from the submissions JSON.

### [Issue 14] [`design`]: Severity: Nit (K14)
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** Add to "Out of scope": 20-F filers, and 8-K Ex. 99.1 earnings
    releases (Phase 3).

### [Issue 15–17] [`structural`, `style`]: Severity: Nit (K15, K16, K17)
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:***
    - Make Status and Container a list.
    - Use `###` headings instead of the bold labels.
    - Make every in-scope bullet and output bullet follow the same pattern.

### [Issue 18] [`structural`]: Severity: Nit (K18)
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** The table is self-explanatory once the legend from Issue 13
    is added.

### [Issue 19] [`style`]: Severity: Nit (K19)
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** "The raw cache" becomes: "the unparsed API response.
    Re-downloaded automatically when a selected filing's accession number is missing
    from it, or when `--refresh-facts` is passed."

### [Issue 20] [`style`]: Severity: Nit (K20)
*   ***AI Suggestion:*** DECLINE (partly covered by Issue 5)
*   ***Justification:*** Issue 5 names the index and the weight source. The "confirm
    list" step stays only in "Before building". No separate edit is needed.

---

## Carried over from Stage 5 (outside lines 1–44, proposed now so Stage 8 sees them)

### [Carry 1] [`zoom-out`, `inventive-catalyst`, `comprehension`]: Severity: Blocker (Z-B1)
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** In §6, change the facts unique key:
    - Declare it `UNIQUE NULLS NOT DISTINCT (...)` (Postgres 15+).
    - Deduplicate each batch by key before the upsert.
    - Add a test that re-runs the load with a point-in-time fact and expects no new
      rows.

### [Carry 2] [`inventive-catalyst`, `comprehension`]: Severity: Major (Z-M6)
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Proposed Edit:*** In §6, rename the facts columns `fy`/`fp` to
    `filing_fy`/`filing_fp`, and state that they record which filing reported the
    value. Numeric lookups must go by `period_start`/`period_end`, taking the row
    with the latest `filed_date`. Example: Apple's FY2025 10-K reports revenue for
    FY2025, FY2024 and FY2023, and all three rows carry `filing_fy=2025`.
