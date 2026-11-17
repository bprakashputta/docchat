# DocChat: RAG over Nasdaq-100 SEC filings

A full-stack retrieval-augmented generation (RAG) app for questions about Nasdaq-100
(NQ100) companies. It pulls SEC filings (10-K, 10-Q, earnings releases), indexes them, and
answers in a chat UI. Answers stream back and cite the company, filing, section and page
each claim comes from. Numeric questions go to structured XBRL data instead of text
retrieval.

**Purpose:**
1. Practice project for a Toptal AI-application-developer interview. The builder should
   become fluent in VS Code, FastAPI, Postgres, React and the Claude and Voyage APIs, and
   be able to explain every design decision. Clear, explainable code matters more than
   clever code.
2. A real research tool over the NQ100 universe, with a later use in trading research
   such as tracking how risk factors change year over year.

## Status
Nothing is built yet. This folder has `.env`, `.gitignore` and this README. Start at
Block 1.

`.env` holds `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY` and the LangSmith settings
(`LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT`, `LANGSMITH_TRACING`,
`LANGSMITH_PROJECT=docchat`). It still needs `SEC_USER_AGENT`, which the builder adds.
**Never print, log or commit `.env`.**

## Architecture

```
React UI (Vite + TS)  ──►  FastAPI  ──►  Postgres 16 + pgvector (Docker)
  chat · filters ·           │
  citations panel            │  acquire: EDGAR downloader → data/raw/
                             │  ingest:  parse (HTML/PDF) → section-aware chunk
                             │           → Voyage embed → store with metadata
                             │  query:   router ─┬─ numeric → XBRL companyfacts (structured)
                             │                   └─ text → metadata filter → hybrid search
                             │                       → Voyage rerank → Claude → stream
                             └─ eval:    retrieval hit-rate + answer faithfulness
```

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (async), SQLAlchemy 2.x, Pydantic v2 | The Python standard; easy to debug in VS Code |
| Storage | Postgres 16 + pgvector, run with Docker Compose | Filings, chunks, vectors and XBRL facts in one database |
| Embeddings | Voyage AI `voyage-4-large`, 1024 dimensions (`input_type="document"` when ingesting, `"query"` when searching), stored in pgvector `vector(1024)` | Same setup as the Placewise project. Compare `voyage-finance-2`, which is tuned for financial text, on the eval set |
| Retrieval | Metadata filter (ticker, form, fiscal period, section), then hybrid search: pgvector cosine similarity + Postgres full-text search (`tsvector`), merged with reciprocal rank fusion (RRF, k=60), then Voyage `rerank-3` on the top ~50 | Filtering keeps companies and years apart. Keyword search catches exact terms (`Item 1A`, product names). Reranking makes the final top-k more precise |
| Numbers | SEC XBRL `companyfacts` API, loaded into a `facts` table | Revenue or EPS should come from reported data, not from text chunks |
| Generation | Claude `claude-opus-5-5` through the official `anthropic` Python SDK, streamed | Answers only from the retrieved context, cites it as `[1]`, `[2]`, and says "I don't know" when the context doesn't support an answer |
| Frontend | React + Vite + TypeScript (npm) | A real full-stack setup |
| Quality | pytest; an eval script for retrieval hit-rate@k and answer faithfulness, graded by an LLM judge (`claude-haiku-5-5`) | Shows the system demonstrably works |

## Data scope

**Universe:** Nasdaq-100 constituents. Keep the list in `data/universe.csv` with the
columns ticker, company name, CIK, filer type (10-K or 20-F) and index weight.

**Phase 1 (build against this):** the 10 largest constituents by index weight. Check the
current list, because weights shift. At the time of writing: MSFT, NVDA, AAPL, AMZN,
AVGO, META, GOOGL, TSLA, COST, NFLX. For each one, use the latest 10-K and the two
most recent 10-Qs, about 30 filings in total.

**Phase 2:** all NQ100 companies, 10-Ks only, downloaded automatically.

**Phase 3:** 10-Qs, earnings releases (8-K Exhibit 99.1), proxy statements (DEF 14A),
earnings slides from investor-relations sites, the Nasdaq-100 methodology document, and a
year-over-year comparison of risk factors.

| Tier | Documents | Source |
|---|---|---|
| 1 (core) | 10-K, 10-Q, earnings press release (8-K Ex. 99.1) | SEC EDGAR |
| 2 | Earnings slides (real PDFs), proxy statements (DEF 14A), Nasdaq-100 methodology | Investor-relations sites, EDGAR, Nasdaq |
| Avoid for now | Earnings call transcripts (usually licensed), other 8-Ks (noisy), scanned PDFs (need OCR) | — |

**Things to watch for:**
- **Most EDGAR filings are HTML/iXBRL, not PDF.** Ingestion must parse HTML (for
  example with BeautifulSoup) as well as PDF (`pypdf`). For HTML, which has no pages,
  store the section name and character offsets instead of page numbers.
- **Some constituents are foreign filers** (for example ASML and PDD) that file a 20-F
  instead of a 10-K. Handle that form, or exclude those companies in Phase 1.
- **GOOGL and GOOG are one company.** Deduplicate by CIK, never by ticker.
- **EDGAR's access rules:** every request needs a User-Agent header that identifies you,
  read from the `SEC_USER_AGENT` env var (the builder chooses what goes in it). Stay
  under 10 requests per second. Cache raw downloads in `data/raw/` and never re-download.

**Chunk metadata:** every chunk stores ticker, CIK, company name, form type, fiscal
year, fiscal quarter (null for a 10-K), filing date, section (for example `Item 1A Risk
Factors` or `Item 7 MD&A`), page or character offset, and the source URL.

## Build plan
Build one block at a time. Agree on the design of each block with the user before writing
its code, and check in when it's done. Don't build ahead.

1. **Infrastructure:** `docker-compose.yml` (pgvector/pgvector:pg16), a Python virtualenv
   managed with `uv`, a `backend/` FastAPI app with a `/health` endpoint that checks the
   database connection, `.vscode/launch.json` to run and debug the API, and settings
   loaded from `.env` with pydantic-settings.
2. **Data acquisition:** `data/universe.csv`, and an EDGAR downloader that maps ticker to
   CIK, lists filings through the submissions API, and downloads the Phase 1 filings to
   `data/raw/{ticker}/{form}_{period}.htm`. It is rate-limited and idempotent. Also load
   XBRL `companyfacts` for the same companies.
3. **Ingestion:** parse HTML and PDF, split by 10-K/10-Q Item sections, then chunk at
   about 800 tokens with about 15% overlap inside each section. Keep tables whole where
   possible. Attach the chunk metadata above. Embed with Voyage in batches (up to 128
   inputs per call), with retry and backoff. Store in the `filings` and `chunks` tables.
   Include a CLI command (`python -m backend.ingest --phase 1`) and `GET /filings`.
4. **Retrieval:** metadata filters plus hybrid search with RRF, then the Voyage reranker.
   `GET /search?q=&ticker=&form=&fy=` is a debug endpoint that returns the ranked chunks
   with their scores.
5. **Generation and routing:** `POST /chat` first classifies the question as numeric,
   text or mixed, and extracts the tickers and periods it mentions. Numeric questions
   query the `facts` table; text questions run retrieval. The prompt contains only the
   retrieved context, and Claude's answer streams as server-sent events (SSE) with
   citation metadata. It refuses when the context doesn't support an answer.
6. **Frontend:** `frontend/` (Vite React TS). It has a chat with streamed answers, ticker
   and form filters, clickable citations that show the source chunk and link to the
   filing, and a filings list.
7. **Evaluation and tests:** pytest for the section splitter, chunker, RRF, the router and
   the API. `eval/` holds about 20 labelled questions over the Phase 1 filings, covering
   numeric, text, comparison and "should refuse" questions, each with the expected source
   section. Report hit-rate@5, faithfulness and routing accuracy.

**Later, after the core works:** Phases 2–3 of the data, conversation memory, prompt
caching, observability (token and cost logging), and a page comparing risk factors year
over year.

## Conventions
- Python 3.13. Manage dependencies with `uv`; tests use pytest.
- Never hardcode keys. Load them from `.env` with pydantic-settings.
- Handle API errors explicitly: Anthropic and Voyage rate limits and timeouts, EDGAR 429
  and 403 responses, and Claude's `stop_reason == "refusal"`.
- Keep functions small and typed. The builder must be able to explain each one in an
  interview.
- Don't commit `data/raw/` (it's large). It's listed in `.gitignore`.

## Running (fill in as each block lands)
```bash
docker compose up -d                       # Postgres + pgvector
uv run uvicorn backend.app.main:app --reload
cd frontend && npm run dev
```
