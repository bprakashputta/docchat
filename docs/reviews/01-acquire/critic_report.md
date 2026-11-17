# Stage 7: Critic Review, round 1 (docs/01-acquire.md, lines 1–44)

**Reviewers** (each completed; each ran with no history from our conversation):
- design (standard: feature-spec)
- structural (standard: feature-spec)
- style (no standard; the persona's own rules)

**Context:** README.md, backend/app/config.py, backend/app/db.py.

**Totals after merging:** 1 blocker, 9 major findings, 10 nits.

**Finding IDs** use the form `<reviewer>-1-<n>`: D = design, S = structural, T = style.
"Prior" points to the same finding raised in an earlier stage: Z = Stage 5
zoom-out, C = Stage 6 comprehension.

---

## 🔴 Blocker

### K1. The doc has no "Alternatives considered" or "Risks and mitigations" section (D-1-1, S-1-out-of-range)
- **Where:** the whole document.
- **Problem:** the feature-spec standard fails any spec that proposes a single path
  without recording the alternatives it rejected.
- **Choices that need alternatives written down:**
  - `manifest.json` vs. Postgres vs. a filesystem-only cache
  - a CSV list of companies vs. looking them up live
  - sync vs. async
  - a worker container vs. running locally only
  - token bucket vs. a fixed gap between requests
- **Risks that are scattered or missing:** 403 handling, partial downloads,
  `SEC_USER_AGENT`, and scaling to Phase 2.

## 🟡 Major

| ID | Finding | Lines | Reviewers | Prior |
|---|---|---|---|---|
| K2 | **False reference.** The README never mentions `manifest.json`. Remove or correct the reference. | 34–35 | D-1-4, S-1-3, T-1-1 | — |
| K3 | **Module, Block, Stage and Phase are mixed.** README Block 2 is called "Module 1" here, and "Stage 3" is undefined. Map the terms or use the README's. | 1, 20, 22 | S-1-2, T-1-2 | C1, Z-N8 |
| K4 | **The ticker → CIK endpoint has no stated use.** The CSV already has CIKs. Also undefined: what happens on a mismatch, and ticker renames (FB → META) that leave old directories orphaned. | 25, 40 | D-1-6, S-1-4, T-1-3 | Z-N2, C5 |
| K5 | **Universe and dedup rules are unclear.** Is it 10 tickers or 10 CIKs? Are GOOG/GOOGL weights summed? Which ticker names the folder (must be deterministic)? Where do weights come from, and as of what date? | 25–28 | D-1-5, T-1-4 | C2, C6 |
| K6 | **The container run path doesn't work as written.** In the container `localhost:5433` doesn't reach the database. With `--rm` and no bind mount of `./data`, every download is lost when the container exits. The spec never says `env_file` passes `.env` to the container, and the worker needs AI keys it never uses. | 4–6, 31–33 | D-1-2 | Z-M4, Z-M5 |
| K7 | **Sync worker vs. async-only database layer and Alembic.** The spec doesn't name which driver or engine the worker and migrations use. | 17, 84–88 | D-1-3 | Z-M1 |
| K8 | **Disk and database are both treated as the source of truth, with no reconciliation.** | 34–35, 68 | D-1-4 | Z-M3 |
| K9 | **The file name depends on companyfacts, which is fetched later.** No fallback is defined. The labels are fiscal-year labels, but the doc doesn't say so here. | 31–32 | D-1-7, T-1-5 | Z-M2, C4 |
| K10 | **No problem statement.** The doc never says why this data is needed, only what it hands to ingest. Add one, or point to the README's purpose. | 8–10 | S-1-1 | — |

## 🟢 Nits
- **K11.** "Reliable list" can't be checked. Add a completeness criterion and say what
  happens on a partial failure (D-1-8, T-1-6; Z-M7).
- **K12.** Is `universe.csv` Phase 1 only or all ~100 companies? Is it committed?
  Define `filer_type`, `phase` and `index_weight` units (D-1-9, T-1-8; C3).
- **K13.** URL placeholders mix styles: `{cik:010d}` vs `{cik}`, snake_case vs
  camelCase. Add a legend, and note that Archives paths use the unpadded CIK
  (D-1-10, S-1-9, T-1-11).
- **K14.** Non-goals missing from the list: 20-F handling and 8-K Ex. 99.1 earnings
  releases, which the README lists as Tier 1 (D-1-11).
- **K15.** The Status and Container lines render as one paragraph (S-1-5).
- **K16.** Use real H3 headings instead of bold labels such as "In scope" (S-1-6).
- **K17.** The in-scope and output bullets don't follow one pattern (S-1-7, S-1-8, T-1-9).
- **K18.** Section 3 has no introductory sentence (S-1-10).
- **K19.** "The raw cache" is vague. Say what it caches and when it's refreshed
  (T-1-10; C13).
- **K20.** The index isn't named in §2. The "confirm list" step is passive and
  duplicated; keep it only in §9 (T-1-7; C2).

## Out of range, routed to later stages
Structural reviewer: there is no end-to-end data-flow section
(universe → submissions → companyfacts → selection → download → database). This
overlaps Z-M2 and should be checked in Stage 9.

## Status
- Round 1 is **not clean**: K1–K10 are open.
- None of the findings is settled yet.
