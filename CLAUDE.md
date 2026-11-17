# DocChat: development rules

Project rules for every session. The README covers what we're building; this file covers
how we build it. Keep it short and organized. Put design notes for each module in
`docs/` (one file per module), not here.

## 1. Modules vs containers
**Modules are build units; containers are failure units.** They're decided separately.

**Modules** (built in this order, one at a time through the gate in section 2):
acquire → ingest → retrieval → eval → generation (router + synthesizer) → api → frontend.
Eval comes right after retrieval so retrieval quality is measured as soon as it exists;
the eval module adds answer-quality metrics when generation lands.
Each module is its own package with a typed interface, its own tests and its own gate report.

**Containers** (5). Split only where a crash in one container doesn't break the others:
- `db`: Postgres + pgvector, on a persistent volume.
- `api`: the whole live query path (router, retrieval, facts lookup, synthesizer). Every
  `/chat` request needs all of these in sequence, so splitting them adds network hops
  without isolating failures.
- `worker`: acquire + ingest jobs. Isolates heavy, crash-prone parsing and embedding from
  live chat.
- `frontend`: nginx serving the React build.
- `eval`: an on-demand job.

**Fault tolerance comes from replicas and degradation, not more containers:**
- Two `api` replicas, with health checks and `restart: unless-stopped` on every container.
- Timeouts and retries with backoff on every external call.
- Degradation: if the reranker fails, return RRF results; if Voyage is down, fall back to
  keyword-only search; if the worker is down, chat keeps serving already-indexed data.
- Worker jobs are idempotent, so a crashed job can be re-run safely.

**Move retrieval into its own container only on a measured trigger:** its p95 latency
breaks the budget because it runs inside `api`, or it needs to scale separately. Typed
module interfaces keep that move mechanical.

## 2. Workflow: the per-module gate
A module goes through every step of this gate before the next one starts:

1. **Design:** the user approves the interface, data flow and latency budget.
2. **Build:** small, typed functions.
3. **Test:** pytest unit and integration tests; aim for ≥80% coverage of the module's logic.
4. **Review:** the reviewer agent runs `/code-review`; fix what it finds.
5. **Performance:** measure p50/p95 latency against the budget, note Big-O on hot paths,
   and check queries with `EXPLAIN ANALYZE`.
6. **Quality:** `ruff` lint and format, `mypy --strict`, no dead code.
7. **Interview check:** the interview-coach agent quizzes the user on the module.
8. **User verifies:** then commit, and write a short gate report in `docs/`.

Never start the next module before the user has verified the current one.

## 3. Code comments
- Every function gets a docstring saying what it does and why, plus any inputs and
  outputs that aren't obvious.
- Every non-trivial block of logic gets a short comment explaining the reasoning:
  trade-offs, edge cases (EDGAR quirks, retries), and the Big-O of hot paths.
- Don't comment line by line. Explain the *why*, don't restate the code.
- Goal: anyone (including Claude in a later session) can open a function and understand
  what it does and why.

## 4. Agents
- **Development agents** (`.claude/agents/`): reviewer, eval-runner, interview-coach.
  The main session is the builder.
- **In-app agents:** router (Haiku), retriever (a tool), facts tool, synthesizer (Opus),
  and judge (Haiku, evals only). Start as a fixed pipeline; upgrade to Claude tool-calling
  once the evals show where the pipeline fails.

## 5. Evals
We don't fine-tune models. The app improves by turning observed failures into eval cases
and fixing prompts and retrieval against them.

**Offline evals (local, required before any deploy or merge)**
- Dataset: a LangSmith dataset of labelled questions (numeric, text, comparison,
  should-refuse), each with an expected answer and expected source section. Starts at
  about 20 and grows.
- Run: `uv run python -m eval.run` runs LangSmith `evaluate()` against the local stack.
  Each run is saved as an experiment so runs can be compared.
- Metrics: hit-rate@5 and MRR, faithfulness and citation correctness (LLM judge, Haiku),
  routing accuracy, refusal correctness, p95 latency, and cost per query.
- Gate: block the deploy or merge if any metric falls below its threshold or regresses
  beyond its tolerance. Run locally first; in CI from Stage 2.

**Online evals (LangSmith, on real usage; from Stage 2)**
- Every `/chat` request is traced to the `docchat` LangSmith project.
- Online LLM-as-judge evaluators score a sample of traces (~20%) for faithfulness,
  relevance and citation correctness.
- The frontend's 👍/👎 buttons attach user feedback to the trace.
- Low-scoring and 👎 traces go to an annotation queue. Once the user reviews them, good
  cases join the offline dataset.

**Flywheel:** usage → online judge → reviewed failure → new dataset case → offline
regression → fix → deploy.

## 6. Git workflow
- One branch per module, e.g. `module/01-acquire`. Never commit directly to `main`.
- Commit as you build: small, focused commits, pushed to the branch as they land.
- Open a PR for each module. The Claude GitHub reviewer reviews every push to the PR.
- Merge only after the Claude review is addressed and the user has verified the module
  (gate step 8).

## 7. Design reviews
Each module's design note in `docs/` gets an Elephant-Goldfish review (`/egm:egm-review`)
before the user approves it. The user starts it; the plugin blocks agents from running it.

## 8. Open decisions
- Whether `.vscode/` stays tracked in git.
