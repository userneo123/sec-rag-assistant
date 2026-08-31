"""Unit tests for deterministic, non-LLM logic: chunking, metrics regex, API routes
that don't require a live LLM call."""
import pytest
from fastapi.testclient import TestClient

from diligence_assistant.ingestion import chunk_text, build_chunk_records
from diligence_assistant.metrics import extract_financial_metrics
from diligence_assistant.sample_data import SEC_FILINGS
from diligence_assistant.api import app


def test_chunk_text_respects_chunk_size():
    words = " ".join(f"word{i}" for i in range(300))
    chunks = chunk_text(words, chunk_size=120, overlap=25)
    for chunk in chunks[:-1]:  # last chunk may be shorter
        assert len(chunk.split()) == 120


def test_chunk_text_overlap():
    words = " ".join(f"word{i}" for i in range(300))
    chunks = chunk_text(words, chunk_size=120, overlap=25)
    # word at index 95 should appear in both chunk 0 and chunk 1
    assert "word95" in chunks[0]
    assert "word95" in chunks[1]


def test_build_chunk_records_ids_are_unique():
    records = build_chunk_records(SEC_FILINGS)
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids))


def test_extract_financial_metrics_astr():
    astr = next(f for f in SEC_FILINGS if f["ticker"] == "ASTR")
    metrics = extract_financial_metrics(astr)
    assert metrics["revenue_musd"] == 412.6
    assert metrics["net_income_musd"] == 38.2
    assert metrics["diluted_eps"] == 0.94
    assert metrics["revenue_growth_pct"] == 18.0


def test_extract_financial_metrics_chfi_declining_revenue():
    chfi = next(f for f in SEC_FILINGS if f["ticker"] == "CHFI")
    metrics = extract_financial_metrics(chfi)
    assert metrics["revenue_growth_pct"] == -3.0


@pytest.fixture
def client():
    # Using TestClient as a context manager triggers the app's lifespan
    # (startup/shutdown) events -- without "with", _state never gets populated
    # and any route touching _state raises a KeyError.
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_companies_endpoint_lists_all_tickers(client):
    response = client.get("/companies")
    assert response.status_code == 200
    tickers = {c["ticker"] for c in response.json()}
    assert tickers == {"ASTR", "BPKA", "CHFI"}


def test_ask_endpoint_rejects_empty_question(client):
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400
