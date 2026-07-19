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
    "data/confidential",  # <-- sensitive, but retrieval still has no output filtering
]

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 50
TOP_K = 4

TENANT_DATA_DIRS = {
    "tenant_a": "data/tenants/tenant_a",
    "tenant_b": "data/tenants/tenant_b",
}