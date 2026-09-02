# SEC Filing RAG Assistant

A full-stack, deployed, agentic RAG (Retrieval-Augmented Generation) system for
querying SEC 10-K filings with cited, grounded answers — built end-to-end from
retrieval logic through a production API, CI/CD pipeline, cloud deployment, and
a React frontend.

**Live demo:** https://green-coast-0a1aa2d00.6.azurestaticapps.net
**Backend API:** https://sec-rag-assistant-hdgbhvbmfhdna3ej.centralindia-01.azurewebsites.net

> ⚠️ The backend runs on Azure App Service's free (F1) tier, which sleeps after
> inactivity. The first request after idle time can take 20–60 seconds to
> cold-start (you may see a `504 Gateway Timeout` — just retry after ~30s).
> This is expected free-tier behavior, not a bug.

---

## What it does

Ask natural-language questions about three synthetic 10-K filings — Aster
Robotics (ASTR), Bluepeak Analytics (BPKA), and Coral Harbor Foods (CHFI) —
and get back an answer grounded in the actual filing text, with every factual
claim tagged to the exact source chunk it came from (e.g. `[ASTR-2025-chunk0]`).

If a question can't be answered from the filings, the system explicitly says
so rather than guessing — this refusal behavior is deliberately tested in the
eval harness (see below).

---

## Architecture

The core of the system is a **LangGraph** state machine, not a single-shot
RAG chain. This lets the agent recover from a bad initial retrieval instead of
just failing silently:

```
        ┌───────────┐
        │  retrieve │◄────────────┐
        └─────┬─────┘             │
              │                   │
        ┌─────▼─────┐       ┌─────┴─────┐
        │  verify   │──────►│  rewrite  │
        └─────┬─────┘  no   └───────────┘
              │  (query mentions a
              │   company whose chunks
              │   weren't retrieved)
       sufficient / max attempts reached
              │
        ┌─────▼─────┐
        │ generate  │──► answer + cited sources
        └───────────┘
```

- **retrieve** — semantic search over the vector store (top-k chunks)
- **verify** — if the question names a specific company, checks whether that
  company's chunks actually came back; general questions pass through
- **rewrite** — if verification fails, an LLM call rewrites the query to be
  more retrievable, then loops back to `retrieve` (capped at 2 attempts so it
  can't loop forever)
- **generate** — answers strictly from retrieved context + computed metrics,
  with explicit instructions to refuse rather than hallucinate when the
  context doesn't contain the answer

### Pipeline stages

1. **Ingestion** — filings are chunked into overlapping word-based windows
   and tagged with stable IDs (`TICKER-YEAR-chunkN`) and metadata (company,
   filing type, fiscal year).
2. **Structured metric extraction** — a regex layer independently extracts
   hard numbers (revenue, net income, EPS, YoY growth) directly from filing
   text, so the LLM isn't relied on for arithmetic — it's given the computed
   metrics alongside the raw excerpts.
3. **Retrieval** — `all-MiniLM-L6-v2` sentence embeddings, indexed in Chroma,
   queried via cosine similarity.
4. **Generation** — Groq-hosted `openai/gpt-oss-120b` (temperature 0),
   prompted with strict citation-format rules and both the retrieved excerpts
   and the computed metrics.

---

## Tech stack

| Layer | Tools |
|---|---|
| RAG / agent | LangChain, LangGraph |
| Vector store / embeddings | ChromaDB, HuggingFace `all-MiniLM-L6-v2` |
| LLM | Groq (`openai/gpt-oss-120b`) |
| Backend API | FastAPI, Uvicorn |
| Testing | pytest, custom eval harness |
| CI/CD | GitHub Actions |
| Containerization | Docker |
| Cloud (backend) | Azure App Service (Linux, container-based) |
| Frontend | React (Vite) |
| Cloud (frontend) | Azure Static Web Apps |

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/companies` | GET | List of indexed filings (ticker, company, fiscal year) |
| `/ask` | POST | `{"question": "..."}` → `{"answer": "...", "sources": [...]}` |

The vector store, computed metrics, and LangGraph pipeline are all built
**once at process startup** (via FastAPI's `lifespan` context manager) and
kept in memory — not rebuilt per request.

---

## Evaluation

Correctness is measured with a 20-question hand-written eval set
(`eval/qa_pairs.json`), covering:

- 12 single-company factual questions (revenue, net income, EPS, risk factors)
- 4 cross-company comparison questions
- 4 deliberately unanswerable/adversarial questions, to test hallucination
  refusal rather than just retrieval accuracy

`eval/run_eval.py` scores three metrics against the live pipeline:

| Metric | Result | What it measures |
|---|---|---|
| Retrieval precision | **100%** (20/20) | Did retrieval pull at least one chunk from a company the question was actually about |
| Citation format | **75%** (15/20) | Does every answer contain at least one well-formed `[TICKER-YEAR-chunkN]` citation |
| Refusal correctness | **100%** (20/20) | Correctly answers answerable questions and correctly refuses unanswerable ones, rather than hallucinating |

**On the 75% citation score:** this is reported as-is, deliberately not
normalized or post-processed. The eval's purpose is to surface genuine model
behavior rather than produce a polished number — a documented, reproducible
limitation is more informative (and more defensible) than a suspiciously
perfect score achieved by cleaning up the output after the fact.

The eval harness runs automatically in CI on every push to `main` (see below).

---

## CI/CD

Two GitHub Actions jobs, defined in `.github/workflows/ci.yml`:

- **`unit-tests`** — runs on every push and PR to `main`. Fast, deterministic
  tests (chunking logic, metric-extraction regex, API route shape) with no
  live LLM calls.
- **`eval-harness`** — runs only on pushes to `main` (not on every PR, to
  avoid burning free-tier LLM rate limits on small commits). Runs the full
  20-question eval against the real Groq-backed pipeline.

The frontend has its own, separately auto-generated Azure Static Web Apps
workflow that builds and deploys `frontend/` on every push to `main`.

Backend deploys are currently manual (rebuild → push to Docker Hub → swap the
image reference in the Azure Portal) rather than fully automated — a
deliberate scope decision, with full backend CD left as a documented next step.

---

## Running locally

### Backend

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

echo "GROQ_API_KEY=your_key_here" > .env

uvicorn diligence_assistant.api:app --reload
# → http://localhost:8000
```

Run the unit tests:

```bash
pytest tests/ -v
```

Run the eval harness (makes real LLM calls, takes a few minutes due to
rate-limit pacing):

```bash
python -m eval.run_eval
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

By default the frontend points at the deployed Azure backend
(`API_BASE_URL` in `frontend/src/App.jsx`). Point it at
`http://localhost:8000` instead if you want to run fully locally.

### Docker (backend)

```bash
docker build -t sec-rag-assistant .
docker run -p 8000:8000 --env-file .env sec-rag-assistant
```

---

## Project structure

```
diligence_assistant/
  ingestion.py       # chunking + chunk-record construction
  metrics.py         # regex-based structured financial metric extraction
  sample_data.py      # synthetic 10-K filings (ASTR, BPKA, CHFI)
  vectorstore.py      # Chroma vector store wrapper
  llm.py               # Groq LLM wrapper
  chain.py             # simple LCEL chain (reference implementation)
  graph.py             # LangGraph state machine (production pipeline)
  api.py               # FastAPI app
eval/
  qa_pairs.json         # 20 hand-written Q/A pairs
  run_eval.py           # eval harness
tests/
  test_core.py           # unit tests (no LLM calls)
frontend/
  src/App.jsx             # single-page React UI
Dockerfile
.github/workflows/ci.yml
```

---

## Data

Three synthetic 10-K excerpts (MD&A + Risk Factors), used only for
demonstration purposes:

- **Aster Robotics Inc. (ASTR)** — revenue $412.6M (+18% YoY), net income
  $38.2M, EPS $0.94. Risks: semiconductor supply chain, warehouse automation
  competition.
- **Bluepeak Analytics Corp. (BPKA)** — revenue $1.28B (+9.4% YoY), net
  income $94.3M (down from $118.6M due to a restructuring charge), EPS $1.12.
  Risks: cloud infrastructure dependency, foreign currency exposure.
- **Coral Harbor Foods Inc. (CHFI)** — revenue $2.94B (-3% YoY, due to a
  divestiture), net income $187.5M, EPS $2.31. Risks: commodity input costs,
  food safety regulations.
