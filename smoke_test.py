"""Smoke test for the LangChain-based pipeline (Step 2)."""
from diligence_assistant.sample_data import SEC_FILINGS
from diligence_assistant.ingestion import build_chunk_records
from diligence_assistant.metrics import extract_financial_metrics
from diligence_assistant.vectorstore import build_vectorstore
from diligence_assistant.graph import build_graph

chunk_records = build_chunk_records(SEC_FILINGS)
print(f"Created {len(chunk_records)} chunks from {len(SEC_FILINGS)} filings")

vectorstore = build_vectorstore(chunk_records)
print("Indexed chunks into LangChain Chroma vector store")

all_metrics = {f["ticker"]: extract_financial_metrics(f) for f in SEC_FILINGS}
for ticker, m in all_metrics.items():
    print(ticker, m)

answer_question = build_graph(vectorstore, all_metrics)

query = "What drove revenue growth this year and by how much?"
answer, retrieved = answer_question(query)

print("\nQUESTION:", query)
print("-" * 80)
print(answer)
print("\nSOURCES RETRIEVED:")
for hit in retrieved:
    m = hit["metadata"]
    print(f"  [{hit['id']}] {m['company']} — {m['filing_type']} FY{m['fiscal_year']} (distance={hit['distance']:.3f})")

print("\n\n" + "=" * 80)
query2 = "Tell me about the semiconductor and robotics company's margins"
answer2, retrieved2 = answer_question(query2)
print("QUESTION:", query2)
print("-" * 80)
print(answer2)
print("\nSOURCES RETRIEVED:")
for hit in retrieved2:
    m = hit["metadata"]
    print(f"  [{hit['id']}] {m['company']} — {m['filing_type']} FY{m['fiscal_year']}")

print("\n\n" + "=" * 80)
print("FORCING THE REWRITE LOOP (k=1, misleading phrasing naming BPKA explicitly)")
answer_question_narrow = build_graph(vectorstore, all_metrics, k=1)
query3 = "What semiconductor supply chain risks does Bluepeak Analytics Corp face?"
answer3, retrieved3 = answer_question_narrow(query3)
print("QUESTION:", query3)
print("-" * 80)
print(answer3)
print("\nSOURCES RETRIEVED:")
for hit in retrieved3:
    m = hit["metadata"]
    print(f"  [{hit['id']}] {m['company']} — {m['filing_type']} FY{m['fiscal_year']}")
