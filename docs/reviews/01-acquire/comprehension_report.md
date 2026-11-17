# Stage 6: Comprehension Test (docs/01-acquire.md)

**Reviewer:** comprehension, given only the target document. It had no other context and
no document standard.
**Ranges:** the feature section is lines 1–44 and the detailed section is lines 45–126.
**Verdict:** no blockers, 7 major findings and 6 nits. The reviewer could paraphrase
both sections. The gaps are undefined terms and parts of the design that don't connect.

## What this proposes
This adds the first pipeline module, "acquire", which runs as a one-off `worker` container job or locally with uv.

- It reads a hand-maintained `data/universe.csv` listing about 10 companies.
- For each company it calls SEC EDGAR through one rate-limited, retrying HTTP client.
- It picks the latest 10-K and the two latest 10-Qs, skipping amendments and 20-F filers.
- It streams those documents to `data/raw/{ticker}/`, named by fiscal period.
- It caches each company's XBRL `companyfacts.json` and loads it into a Postgres `facts` table.
- Company and filing metadata go into `companies` and `filings` tables, created by Alembic migrations.
- Every step is idempotent (skip existing files, upsert rows), so a re-run is cheap and safe.

The output is a queryable list of filings that a later "ingest" module (Module 2) will parse, chunk and embed.

## How the existing system works, per this document
The document says almost nothing about what exists today. From hints, the reviewer gathered that:

- A README describes a per-ticker `manifest.json`, which this design replaces with Postgres (line 35).
- A docker compose setup provides a database that integration tests can use (line 121), and there is a `.env` file (line 124).
- A `backend/app` package exists, where the models will live (line 53).
- The project is staged into Modules, Phases and Stages, and Phase 1 is the top 10 by weight of what turns out to be the Nasdaq-100 (line 125).

The reviewer couldn't tell whether `backend/`, `migrations/`, the compose file or Postgres already exist, or whether this module creates them.

## Findings

### 🟡 Major
1. **Phase, Stage and Module are used without definitions** (lines 3–4, 21–22, 26, 88, 125).
   - Phases 2 and 3, Stage 3 and Module 2 are listed as out of scope.
   - Nothing says what each one contains or how the three terms relate.
   - A new reader can't tell where the scope boundary sits.
2. **The index isn't named until the last section** (lines 25–27, 91).
   - "Nasdaq-100" first appears at line 125.
   - The document doesn't say where the weights come from.
   - It doesn't say who confirms the top-10 list, or how.
3. **`filer_type` and the 20-F skip don't connect** (lines 25, 77).
   - The allowed values of `filer_type` aren't listed.
   - It's unclear whether the 20-F skip uses the CSV column or the forms in the submissions JSON.
   - The values of the `phase` column aren't listed, and neither is how `--phase 1` filters on it.
4. **There's no fallback for fiscal labels** (lines 31–32, 78–80).
   - Nothing says what happens when no XBRL fact carries a filing's accession number.
   - That happens when a filing was just made and companyfacts hasn't caught up.
5. **The ticker-to-CIK endpoint has no stated role** (line 40 vs line 25).
   - The CSV already supplies the CIK.
   - No module in the code layout calls the endpoint.
   - The "~51 requests" figure isn't broken down, so it can't be checked.
6. **Which ticker survives deduplication?** (lines 28, 31)
   - GOOG and GOOGL collapse into one company.
   - The `data/raw/{ticker}/` path and the `companies.ticker` column need one ticker.
   - No rule picks it.
7. **The facts unique-key explanation is hard to follow** (lines 100–102).
   - It could mean "one row per fact per filing, read the newest", or "restatements kept as history".
   - A concrete example is needed.
   - The reviewer also noticed the nullable `period_start` in the unique key, which
     breaks idempotency. This is the same as Stage 5 B1.

### 🟢 Nits
8. Line 10 vs line 20: it's never stated that "the ingest module" is Module 2.
9. Line 35: "the README" isn't linked, and the document doesn't say what the manifest held.
10. Lines 4–6, 53–55, 121, 124: the document doesn't say what exists already and what this
    module creates, such as the compose service entry for `worker`.
11. Line 126: "EGM review" is an undefined acronym.
12. Line 59: "about 8 requests per second" is vague. Give the rate and burst size, because
    the test at line 115 checks the spacing between requests.
13. Line 71: it's unclear whether a run without `--refresh-facts` ever refreshes
    companyfacts. If it never does, labels for new filings could go missing, which ties
    to finding 4.

## Overlap with Stage 5
- Finding 4 = Stage 5 M2.
- Finding 5 = Stage 5 N2.
- Finding 7 = Stage 5 B1 and M6.
- Finding 13 relates to Stage 5 M2.

Findings 1–3, 6 and 8–12 are new.
