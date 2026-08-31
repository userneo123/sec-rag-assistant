"""LCEL chain: retrieve -> merge computed metrics -> cited-answer prompt -> generate."""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .vectorstore import retrieve
from .llm import get_llm

PROMPT_TEMPLATE = """You are a financial research assistant. Answer the question using ONLY the
filing excerpts and computed metrics below. Every factual claim must end with a citation
in square brackets referencing the exact chunk id it came from, e.g. [ASTR-2025-chunk0].
If the excerpts don't contain the answer, say so explicitly instead of guessing.

FILING EXCERPTS:
{context}

COMPUTED FINANCIAL METRICS:
{metrics_block}

QUESTION: {question}

ANSWER (with inline citations):"""

_prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
_llm = get_llm()
_parser = StrOutputParser()
_chain = _prompt | _llm | _parser  # the LCEL chain


def _format_context(retrieved_chunks):
    blocks = []
    for hit in retrieved_chunks:
        cid = hit["id"]
        meta = hit["metadata"]
        blocks.append(
            f"[{cid} — {meta['company']} {meta['filing_type']} FY{meta['fiscal_year']}]\n{hit['text']}"
        )
    return "\n\n".join(blocks)


def _format_metrics(metrics_context):
    return "\n".join(f"{ticker}: {m}" for ticker, m in metrics_context.items())


def build_chain(vectorstore, all_metrics, k=4):
    """Returns answer_question(query) -> (answer, retrieved_chunks)."""

    def answer_question(query):
        retrieved = retrieve(vectorstore, query, k=k)
        relevant_tickers = {hit["metadata"]["ticker"] for hit in retrieved}
        relevant_metrics = {t: all_metrics[t] for t in relevant_tickers if t in all_metrics}

        answer = _chain.invoke({
            "context": _format_context(retrieved),
            "metrics_block": _format_metrics(relevant_metrics),
            "question": query,
        })
        return answer, retrieved

    return answer_question
