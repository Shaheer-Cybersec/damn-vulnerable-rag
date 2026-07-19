"""
rag_pipeline.py — the vulnerable core.

VULNERABILITY (LLM01 + LLM08 + LLM06): retrieved chunk text AND
conversation history are concatenated directly into the prompt with no
delimiter, no instruction/data separation, and no output-side check.
Anything in the vector store — including data/malicious/*.txt — is treated
as equally trustworthy as the system prompt itself. Because history is fed
back into every subsequent prompt, a single successful injection can
poison the entire rest of the conversation, not just one answer. On top of
that, any TOOL_CALL: pattern in the model's raw output gets executed
immediately with zero permission check (see tools.py).
"""

import tools

from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM

import config

SYSTEM_PROMPT = "You are a helpful internal knowledge-base assistant."

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


def retrieve(query: str, k: int = config.TOP_K, requesting_tenant_id: str | None = None):
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(query, k=k)
    chunks = [r.page_content for r in results]
    sources = [r.metadata.get("source", "?") for r in results]
    tenant_ids = [r.metadata.get("tenant_id", "?") for r in results]
    return chunks, sources, tenant_ids


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


def answer(
    question: str,
    history: list[dict] | None = None,
    requesting_tenant_id: str | None = None,
) -> dict:
    history = history or []
    chunks, sources, tenant_ids = retrieve(question, requesting_tenant_id=requesting_tenant_id)
    prompt = build_prompt(question, chunks, history)

    llm = OllamaLLM(model=config.LLM_MODEL)
    response = llm.invoke(prompt)

    tool_calls_executed = tools.execute_tool_calls(response)

    return {
        "question": question,
        "answer": response,
        "retrieved_chunks": chunks,
        "sources": sources,
        "tenant_ids": tenant_ids,
        "requesting_tenant_id": requesting_tenant_id,
        "prompt_sent": prompt,
        "tool_calls_executed": tool_calls_executed,
    }


if __name__ == "__main__":
    result = answer("What's the remote work policy?")
    print("Sources:", result["sources"])
    print("\nAnswer:", result["answer"])
    print("\nTool calls executed:", result["tool_calls_executed"])