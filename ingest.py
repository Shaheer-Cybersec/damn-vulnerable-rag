"""
ingest.py — loads every .txt file under DATA_DIRS into Chroma.

VULNERABILITY NOTE: this script embeds and stores anything found in
data/clean/ AND data/malicious/ with zero content vetting, zero source
allow-listing, and no separation between trusted and untrusted documents
once they're in the vector store. That's on purpose — see docs/ARCHITECTURE.md.
"""

import os
import glob

from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

import config


def load_documents() -> list[Document]:
    docs = []

    # existing shared corpus (vuln 01) — untouched
    for data_dir in config.DATA_DIRS:
        for path in glob.glob(os.path.join(data_dir, "*.txt")):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": path, "tenant_id": "shared"},
                )
            )

    # tenant-scoped corpus (vuln 02) — metadata exists but is NEVER
    # enforced at retrieval time. That's the vulnerability.
    for tenant_id, tenant_dir in config.TENANT_DATA_DIRS.items():
        for path in glob.glob(os.path.join(tenant_dir, "*.txt")):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": path, "tenant_id": tenant_id},
                )
            )

    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    return splitter.split_documents(docs)


def main():
    print("[*] Loading documents from:", config.DATA_DIRS)
    docs = load_documents()
    print(f"[*] Loaded {len(docs)} raw documents")

    chunks = chunk_documents(docs)
    print(f"[*] Split into {len(chunks)} chunks")

    embeddings = OllamaEmbeddings(model=config.EMBED_MODEL)

    print("[*] Embedding + writing to Chroma at:", config.VECTORSTORE_DIR)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=config.COLLECTION_NAME,
        persist_directory=config.VECTORSTORE_DIR,
    )
    

    sources = sorted({d.metadata["source"] for d in docs})
    print("[*] Ingested sources:")
    for s in sources:
        flag = " <-- MALICIOUS (intentional)" if "malicious" in s else ""
        print(f"    - {s}{flag}")

    print("[*] Done.")


if __name__ == "__main__":
    main()