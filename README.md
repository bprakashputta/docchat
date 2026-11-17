# DocChat: document Q&A with RAG

A full-stack retrieval-augmented generation (RAG) app. You upload PDF, Markdown or text
files, ask questions in a chat UI, and get answers that stream back and cite the document
and page each claim comes from.

**Purpose:** practice project for a Toptal AI-application-developer interview. Its goal is
to make the builder fluent in VS Code, FastAPI, Postgres, React and the Claude API, and
able to explain every design decision. Clear code that someone can explain matters more
here than clever code.

## Status
Nothing is built yet. This folder has only `.env` (which holds `ANTHROPIC_API_KEY`;
never print or commit it), `.gitignore` and this README. Start at Block 1.

## Architecture

```
React UI (Vite + TS)  ──►  FastAPI  ──►  Postgres 16 + pgvector (Docker)
  upload · chat ·            │  ingest:  parse → chunk → embed → store
  citations panel            │  query:   hybrid search (vector + keyword)
                             │           → (optional rerank) → Claude → stream
                             └─ eval:    retrieval hit-rate + answer faithfulness
```

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (async), SQLAlchemy 2.x, Pydantic v2 | The Python standard; easy to debug in VS Code |
| Storage | Postgres 16 + pgvector, run with Docker Compose | Documents, chunks and vectors in one database |
| Embeddings | Local `fastembed` (`BAAI/bge-small-en-v1.5`, 384 dimensions) | Anthropic has no embeddings API; this needs no second key and costs nothing |
| Retrieval | Hybrid: pgvector cosine similarity + Postgres full-text search (`tsvector`), merged with reciprocal rank fusion (RRF) | Vector-only search misses exact terms (IDs, names, error codes) |
| Generation | Claude `claude-opus-5-5` through the official `anthropic` Python SDK, streamed | Answers only from the retrieved chunks, cites them as `[1]`, `[2]`, and says "I don't know" when the context is insufficient |
| Frontend | React + Vite + TypeScript (npm) | A real full-stack setup |
| Quality | pytest; an eval script for retrieval hit-rate@k and answer faithfulness, graded by an LLM judge (`claude-haiku-5-5`) | Shows the system demonstrably works |

## Build plan
Build one block at a time. Agree on the design of each block with the user before writing
its code, and check in when it's done. Don't build ahead.

1. **Infrastructure:** `docker-compose.yml` (pgvector/pgvector:pg16), Python virtualenv
   managed with `uv`, `backend/` FastAPI app with a `/health` endpoint that checks the
   database connection, and `.vscode/launch.json` to run and debug the API.
2. **Ingestion:** `POST /documents` uploads a file and parses it (`pypdf` for PDF, plain
   reads for MD/TXT). Chunks are about 800 tokens with about 15% overlap and keep their
   page numbers. Embed the chunks and store them in the `documents` and `chunks` tables.
   Also add `GET /documents` and `DELETE /documents/{id}`.
3. **Retrieval:** a hybrid search function using RRF (k=60). `GET /search?q=` is a debug
   endpoint that returns the ranked chunks with their scores.
4. **Generation:** `POST /chat` retrieves the top-k chunks, builds a grounded prompt and
   streams Claude's answer as server-sent events (SSE) with citation metadata. It
   refuses when the context doesn't support an answer.
5. **Frontend:** `frontend/` (Vite React TS). It has a document upload and list, a chat
   that streams answers, and clickable citations that show the source chunk.
6. **Evaluation and tests:** pytest for the chunker, RRF and the API, and `eval/` with
   about 15 question-and-answer pairs over the sample documents, reporting hit-rate@5
   and faithfulness.

**Later, after the core works:** a reranker, conversation memory, per-user collections,
prompt caching, and observability (token and cost logging).

## Conventions
- Python 3.13. Manage dependencies with `uv`; tests use pytest.
- Never hardcode the API key. Load it from `.env` with `python-dotenv` or
  pydantic-settings.
- Handle API errors explicitly: rate limits, timeouts and `stop_reason == "refusal"`.
- Keep functions small and typed. The builder must be able to explain each one in an
  interview.

## Running (fill in as each block lands)
```bash
docker compose up -d                       # Postgres + pgvector
uv run uvicorn backend.app.main:app --reload
cd frontend && npm run dev
```
