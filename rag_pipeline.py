"""
rag_pipeline.py — the vulnerable core.

VULNERABILITY (LLM01 + LLM08): retrieved chunk text AND conversation history
are concatenated directly into the prompt with no delimiter, no
instruction/data separation, and no output-side check. Anything in the
vector store — including data/malicious/*.txt — is treated as equally
trustworthy as the system prompt itself. Because history is now fed back
into every subsequent prompt, a single successful injection can poison the
entire rest of the conversation, not just one answer.
"""

from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM

import config

SYSTEM_PROMPT = "You are a helpful internal knowledge-base assistant."

# VULNERABLE: retrieved context AND prior conversation turns are glued into
# the prompt as plain text, with no marker distinguishing "document
# content" / "past assistant output" from "instructions."
PROMPT_TEMPLATE = """{system_prompt}

Context from company documents:
{context}

Conversation so far:
{history}

Question: {question}

Answer:"""


def get_vectorstore() -> Chroma:
    embeddings = OllamaEmbeddings(model=config.EMBED_MODEL)
    return Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=config.VECTORSTORE_DIR,
    )


def retrieve(query: str, k: int = config.TOP_K):
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(query, k=k)
    chunks = [r.page_content for r in results]
    sources = [r.metadata.get("source", "?") for r in results]
    return chunks, sources


def format_history(history: list[dict]) -> str:
    if not history:
        return "(no prior messages)"
    lines = []
    for turn in history:
        lines.append(f"User: {turn['question']}")
        lines.append(f"Assistant: {turn['answer']}")
    return "\n".join(lines)


def build_prompt(question: str, chunks: list[str], history: list[dict]) -> str:
    context = "\n\n---\n\n".join(chunks)
    return PROMPT_TEMPLATE.format(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        history=format_history(history),
        question=question,
    )


def answer(question: str, history: list[dict] | None = None) -> dict:
    history = history or []
    chunks, sources = retrieve(question)
    prompt = build_prompt(question, chunks, history)

    llm = OllamaLLM(model=config.LLM_MODEL)
    response = llm.invoke(prompt)

    return {
        "question": question,
        "answer": response,
        "retrieved_chunks": chunks,
        "sources": sources,
        "prompt_sent": prompt,
    }


if __name__ == "__main__":
    result = answer("What's the remote work policy?")
    print("Sources:", result["sources"])
    print("\nAnswer:", result["answer"])