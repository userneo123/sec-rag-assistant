"""LangGraph state machine: retrieve -> verify -> (rewrite -> retrieve)* -> generate."""
import re
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import logging

from .vectorstore import retrieve as vs_retrieve
from .llm import get_llm

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # caps the retrieve->verify->rewrite loop so it can't spin forever

_llm = get_llm()
_parser = StrOutputParser()

_GENERATE_PROMPT = ChatPromptTemplate.from_template("""You are a financial research assistant. Answer the question using ONLY the
filing excerpts and computed metrics below.

CITATION FORMAT RULES (follow exactly, no exceptions):
- Every factual claim must end with a citation in ASCII square brackets: [chunk_id]
- Use ONLY the standard keyboard characters '[' and ']' -- never use full-width
  brackets, angle brackets, or any other bracket style.
- Do NOT put a space right after '[' or right before ']'.
- Do NOT invent suffixes on the chunk id -- copy it exactly as given, e.g. [ASTR-2025-chunk0],
  not [ASTR-2025-chunk0-computed] or any other variant.
- Correct example:   Revenue was $412.6 million [ASTR-2025-chunk0].
- Incorrect example: Revenue was $412.6 million【ASTR-2025-chunk0】.
- Incorrect example: Revenue was $412.6 million [ ASTR-2025-chunk0 ].

If the excerpts don't contain the answer, say so explicitly instead of guessing.

FILING EXCERPTS:
{context}

COMPUTED FINANCIAL METRICS:
{metrics_block}

QUESTION: {question}

ANSWER (with inline citations):""")

_REWRITE_PROMPT = ChatPromptTemplate.from_template("""The following search query failed to retrieve any filing excerpts that mention
the company/ticker the user asked about. Rewrite the query to be more likely to
retrieve the right filing excerpts via semantic search. Keep it a single question,
no preamble, no explanation -- output ONLY the rewritten query.

ORIGINAL QUESTION: {original_query}
CURRENT QUERY: {query}
COMPANIES/TICKERS MENTIONED IN THE ORIGINAL QUESTION: {mentioned}

REWRITTEN QUERY:""")

_generate_chain = _GENERATE_PROMPT | _llm | _parser
_rewrite_chain = _REWRITE_PROMPT | _llm | _parser


class GraphState(TypedDict):
    original_query: str
    query: str
    retrieved: list
    attempts: int
    sufficient: bool
    answer: Optional[str]


def _find_mentioned_entities(query, all_metrics):
    """Which known tickers/company names are named in the query, if any."""
    mentioned = []
    q_lower = query.lower()
    for ticker, m in all_metrics.items():
        company_clean = m["company"].lower().rstrip(".")
        if ticker.lower() in q_lower or company_clean in q_lower:
            mentioned.append(ticker)
    return mentioned


def build_graph(vectorstore, all_metrics, k=4):
    mentioned_cache = {}  # original_query -> [tickers], computed once per run

    def retrieve_node(state: GraphState) -> GraphState:
        retrieved = vs_retrieve(vectorstore, state["query"], k=k)
        return {**state, "retrieved": retrieved}

    def verify_node(state: GraphState) -> GraphState:
        original = state["original_query"]
        if original not in mentioned_cache:
            mentioned_cache[original] = _find_mentioned_entities(original, all_metrics)
        mentioned = mentioned_cache[original]

        if not mentioned:
            # General question, nothing specific to verify against -- treat as sufficient.
            return {**state, "sufficient": True}

        retrieved_tickers = {hit["metadata"]["ticker"] for hit in state["retrieved"]}
        sufficient = any(t in retrieved_tickers for t in mentioned)
        logger.debug(f"verify attempt={state['attempts']} mentioned={mentioned} retrieved_tickers={retrieved_tickers} sufficient={sufficient}")
        return {**state, "sufficient": sufficient}

    def rewrite_node(state: GraphState) -> GraphState:
        mentioned = mentioned_cache.get(state["original_query"], [])
        new_query = _rewrite_chain.invoke({
            "original_query": state["original_query"],
            "query": state["query"],
            "mentioned": ", ".join(mentioned) if mentioned else "(none detected)",
        })
        return {
            **state,
            "query": new_query.strip(),
            "attempts": state["attempts"] + 1,
        }

    def generate_node(state: GraphState) -> GraphState:
        retrieved = state["retrieved"]
        relevant_tickers = {hit["metadata"]["ticker"] for hit in retrieved}
        relevant_metrics = {t: all_metrics[t] for t in relevant_tickers if t in all_metrics}

        context = "\n\n".join(
            f"[{hit['id']} — {hit['metadata']['company']} {hit['metadata']['filing_type']} FY{hit['metadata']['fiscal_year']}]\n{hit['text']}"
            for hit in retrieved
        )
        metrics_block = "\n".join(f"{ticker}: {m}" for ticker, m in relevant_metrics.items())

        answer = _generate_chain.invoke({
            "context": context,
            "metrics_block": metrics_block,
            "question": state["original_query"],
        })
        return {**state, "answer": answer}

    def route_after_verify(state: GraphState) -> str:
        if state["sufficient"] or state["attempts"] >= MAX_ATTEMPTS:
            return "generate"
        return "rewrite"

    graph = StateGraph(GraphState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("verify", verify_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "verify")
    graph.add_conditional_edges("verify", route_after_verify, {"generate": "generate", "rewrite": "rewrite"})
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", END)

    compiled = graph.compile()

    def answer_question(query):
        result = compiled.invoke({
            "original_query": query,
            "query": query,
            "retrieved": [],
            "attempts": 0,
            "sufficient": False,
            "answer": None,
        })
        return result["answer"], result["retrieved"]

    return answer_question
