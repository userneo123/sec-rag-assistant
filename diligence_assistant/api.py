"""FastAPI app for the SEC filing RAG assistant (Step 5).

Builds the vectorstore, metrics, and LangGraph pipeline once at startup and
keeps them in memory for the life of the process -- not rebuilt per request,
since embedding/indexing is real work and answer_question() is a pure query
function once the index exists.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .sample_data import SEC_FILINGS
from .ingestion import build_chunk_records
from .metrics import extract_financial_metrics
from .vectorstore import build_vectorstore
from .graph import build_graph

_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    chunk_records = build_chunk_records(SEC_FILINGS)
    vectorstore = build_vectorstore(chunk_records)
    all_metrics = {f["ticker"]: extract_financial_metrics(f) for f in SEC_FILINGS}
    answer_question = build_graph(vectorstore, all_metrics)

    _state["answer_question"] = answer_question
    _state["all_metrics"] = all_metrics
    yield
    _state.clear()


app = FastAPI(title="SEC Filing RAG Assistant", lifespan=lifespan)

# Permissive for local dev against the future React frontend (Step 8).
# Tighten to specific origins before any real deployment (Step 7).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    id: str
    company: str
    ticker: str
    filing_type: str
    fiscal_year: int
    distance: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/companies")
def companies():
    all_metrics = _state["all_metrics"]
    return [
        {"ticker": t, "company": m["company"], "fiscal_year": m["fiscal_year"]}
        for t, m in all_metrics.items()
    ]


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    answer_question = _state["answer_question"]
    answer, retrieved = answer_question(request.question)

    sources = [
        SourceChunk(
            id=hit["id"],
            company=hit["metadata"]["company"],
            ticker=hit["metadata"]["ticker"],
            filing_type=hit["metadata"]["filing_type"],
            fiscal_year=hit["metadata"]["fiscal_year"],
            distance=hit["distance"],
        )
        for hit in retrieved
    ]
    return AskResponse(answer=answer, sources=sources)
