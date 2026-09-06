"""
Minimal RAG layer for the UNGUARDED path.

This deliberately does its own naive retrieval + prompt-stuffing with no
verification of what comes back — that's the point of the comparison. The
GUARDED path instead relies on NeMo Guardrails' built-in knowledge base
support (see rails/kb/) plus its self_check_facts rail, so the two paths are
architecturally different on purpose, not just prompt-different.
"""

import os
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "kb"
INDEX_DIR = BASE_DIR / ".faiss_index"

_index_cache = None


def build_or_load_index():
    global _index_cache
    if _index_cache is not None:
        return _index_cache

    embeddings = OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))

    if INDEX_DIR.exists():
        _index_cache = FAISS.load_local(
            str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
        )
        return _index_cache

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []
    for path in sorted(KB_DIR.glob("*.md")):
        loader = TextLoader(str(path))
        docs.extend(splitter.split_documents(loader.load()))

    if not docs:
        raise RuntimeError(f"No documents found in {KB_DIR}. Add some .md files first.")

    index = FAISS.from_documents(docs, embeddings)
    index.save_local(str(INDEX_DIR))
    _index_cache = index
    return index


def retrieve_context(query: str, k: int = 4) -> str:
    index = build_or_load_index()
    retriever = index.as_retriever(search_kwargs={"k": k})
    chunks = retriever.invoke(query)
    if not chunks:
        return "(no relevant documents found)"
    return "\n\n".join(
        f"[source: {Path(c.metadata.get('source', 'unknown')).name}]\n{c.page_content}"
        for c in chunks
    )
