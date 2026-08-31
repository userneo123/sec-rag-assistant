"""LangChain Chroma vector store wrapper (Step 2: swaps raw chromadb client)."""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def build_vectorstore(chunk_records, collection_name="sec_filings"):
    """Build an in-memory LangChain Chroma vector store from chunk records."""
    documents = [
        Document(
            page_content=r["text"],
            metadata={**r["metadata"], "chunk_id": r["id"]},
        )
        for r in chunk_records
    ]
    ids = [r["id"] for r in chunk_records]
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=_embeddings,
        ids=ids,
        collection_name=collection_name,
    )
    return vectorstore


def retrieve(vectorstore, query, k=4):
    """Return the top-k most relevant chunks, in the same shape as the original notebook's retrieve()."""
    results = vectorstore.similarity_search_with_score(query, k=k)
    retrieved = []
    for doc, score in results:
        retrieved.append({
            "id": doc.metadata["chunk_id"],
            "text": doc.page_content,
            "metadata": doc.metadata,
            "distance": score,
        })
    return retrieved
