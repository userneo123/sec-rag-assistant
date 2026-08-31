"""Filing text chunking and chunk-record construction.

Carried over unchanged from the original notebook (sec_rag_assistant.ipynb, Section 3).
"""


def chunk_text(text, chunk_size=120, overlap=25):
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def build_chunk_records(filings):
    """Chunk every filing and attach source metadata + a stable chunk id."""
    records = []
    for filing in filings:
        chunks = chunk_text(filing["text"])
        for i, chunk in enumerate(chunks):
            records.append({
                "id": f"{filing['ticker']}-{filing['fiscal_year']}-chunk{i}",
                "text": chunk,
                "metadata": {
                    "company": filing["company"],
                    "ticker": filing["ticker"],
                    "filing_type": filing["filing_type"],
                    "fiscal_year": filing["fiscal_year"],
                    "chunk_index": i,
                },
            })
    return records
