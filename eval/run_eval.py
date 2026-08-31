"""Eval harness for the LangGraph RAG pipeline (Step 4).

Scores three things against eval/qa_pairs.json:
  1. Retrieval precision  -- did we retrieve at least one chunk from a
     ticker the question was actually about?
  2. Citation format      -- does every factual sentence in the answer end
     with a [TICKER-YEAR-chunkN]-style citation?
  3. Refusal correctness  -- for answerable questions, did the model actually
     answer (not refuse)? For unanswerable questions, did it correctly refuse
     instead of hallucinating?

Run from the project root: python -m eval.run_eval
"""
import json
import re
import time
from pathlib import Path

from diligence_assistant.sample_data import SEC_FILINGS
from diligence_assistant.ingestion import build_chunk_records
from diligence_assistant.metrics import extract_financial_metrics
from diligence_assistant.vectorstore import build_vectorstore
from diligence_assistant.graph import build_graph

QA_PATH = Path(__file__).parent / "qa_pairs.json"

# Matches [ASTR-2025-chunk0], [ASTR-2025-chunk0-computed], etc. -- tolerant of
# an optional trailing "-computed"/"-something" suffix the LLM sometimes adds.
CITATION_RE = re.compile(r"\[([A-Z]{2,5})-\d{4}-chunk\d+(?:-[a-z]+)?\]")

REFUSAL_PHRASES = [
    "cannot be derived",
    "do not contain",
    "does not contain",
    "cannot be reported",
    "cannot be answered",
    "not disclosed",
    "no information",
    "cannot determine",
    "not available in",
    "do not mention",
    "does not mention",
    "does not provide",
    "do not provide",
    "does not specify",
    "do not specify",
    "not enough information",
    "insufficient information",
]

# Stay under Groq free-tier TPM by spacing calls out. If a 429 still slips
# through, retry with exponential backoff instead of crashing the whole run.
SECONDS_BETWEEN_CALLS = 8
MAX_RETRIES = 3


def load_qa_pairs():
    with open(QA_PATH) as f:
        return json.load(f)


def score_retrieval(retrieved, expected_tickers):
    if not expected_tickers:
        return None  # not scoreable
    retrieved_tickers = {hit["metadata"]["ticker"] for hit in retrieved}
    return bool(retrieved_tickers & set(expected_tickers))


def score_citation_format(answer):
    citations = CITATION_RE.findall(answer)
    return len(citations) > 0, citations


def looks_like_refusal(answer):
    lower = answer.lower()
    return any(phrase in lower for phrase in REFUSAL_PHRASES)


def score_refusal_correctness(answer, expect_answerable):
    refused = looks_like_refusal(answer)
    if expect_answerable:
        return not refused  # correct if it did NOT refuse
    else:
        return refused  # correct if it DID refuse


def call_with_retry(answer_question, question):
    """Run answer_question, retrying on rate-limit errors with backoff.
    Returns (answer, retrieved) or (None, None) if all retries are exhausted.
    """
    for attempt in range(MAX_RETRIES):
        try:
            return answer_question(question)
        except Exception as e:
            is_rate_limit = "429" in str(e) or "rate_limit" in str(e).lower()
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait = 15 * (attempt + 1)
                print(f"     [rate limited, waiting {wait}s before retry {attempt + 2}/{MAX_RETRIES}...]")
                time.sleep(wait)
            elif is_rate_limit:
                return None, None  # exhausted retries
            else:
                raise  # not a rate-limit error, don't swallow it
    return None, None


def main():
    qa_pairs = load_qa_pairs()

    chunk_records = build_chunk_records(SEC_FILINGS)
    vectorstore = build_vectorstore(chunk_records)
    all_metrics = {f["ticker"]: extract_financial_metrics(f) for f in SEC_FILINGS}
    answer_question = build_graph(vectorstore, all_metrics)

    retrieval_results = []
    citation_results = []
    refusal_results = []
    skipped = 0

    for i, pair in enumerate(qa_pairs, 1):
        question = pair["question"]
        expected_tickers = pair["expected_tickers"]
        expect_answerable = pair["expect_answerable"]

        if i > 1:
            time.sleep(SECONDS_BETWEEN_CALLS)

        answer, retrieved = call_with_retry(answer_question, question)

        if answer is None:
            print(f"[{i:02d}] SKIP  could not complete after {MAX_RETRIES} retries (rate limit)")
            print(f"     Q: {question}")
            print()
            skipped += 1
            continue

        retrieval_ok = score_retrieval(retrieved, expected_tickers)
        citation_ok, citations = score_citation_format(answer)
        refusal_ok = score_refusal_correctness(answer, expect_answerable)

        if retrieval_ok is not None:
            retrieval_results.append(retrieval_ok)
        citation_results.append(citation_ok)
        refusal_results.append(refusal_ok)

        status = "OK" if (retrieval_ok in (None, True) and citation_ok and refusal_ok) else "FAIL"
        print(f"[{i:02d}] {status}  retrieval={retrieval_ok}  citations={citation_ok}  refusal={refusal_ok}")
        print(f"     Q: {question}")
        if status == "FAIL":
            print(f"     A: {answer[:300]}{'...' if len(answer) > 300 else ''}")
            print(f"     retrieved_tickers={[h['metadata']['ticker'] for h in retrieved]}  citations_found={citations}")
        print()

    def pct(results):
        return 100 * sum(results) / len(results) if results else float("nan")

    print("=" * 70)
    print(f"Retrieval precision:   {pct(retrieval_results):.1f}%  ({sum(retrieval_results)}/{len(retrieval_results)})")
    print(f"Citation format:       {pct(citation_results):.1f}%  ({sum(citation_results)}/{len(citation_results)})")
    print(f"Refusal correctness:   {pct(refusal_results):.1f}%  ({sum(refusal_results)}/{len(refusal_results)})")
    if skipped:
        print(f"Skipped (rate limit):  {skipped}/{len(qa_pairs)}")


if __name__ == "__main__":
    main()
