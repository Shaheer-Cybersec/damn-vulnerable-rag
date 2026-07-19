"""
Central config for damn-vulnerable-rag.
Swap models here — nothing else in the codebase should hardcode model names.
"""

LLM_MODEL = "llama3.2:1b"
EMBED_MODEL = "nomic-embed-text"

VECTORSTORE_DIR = "vectorstore"
COLLECTION_NAME = "dvr_corpus"

DATA_DIRS = [
    "data/clean",
    "data/malicious",  # <-- intentionally ingested, no vetting. That's the vuln.
]

CHUNK_SIZE = 800
CHUNK_OVERLAP = 50
TOP_K = 3