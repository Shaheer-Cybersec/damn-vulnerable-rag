# damn-vulnerable-rag

> An intentionally vulnerable RAG (Retrieval-Augmented Generation) application — the DVWA/WebGoat pattern applied to LLM/RAG attack surface.

Built broken on purpose. Used as a study target, a red-team demo, and a portfolio artifact showing real, current LLM vulnerability classes — not theoretical ones.

**Status: v0.4 shipped — four working, reproducible vulnerabilities spanning four distinct OWASP LLM Top 10 (2025) categories: indirect prompt injection (v0.1), retrieval-scope IDOR (v0.2), over-permissioned tool call / excessive agency (v0.3), and sensitive information disclosure via verbatim extraction (v0.4).**

![Prompt injection demo](docs/screenshots/03-hijacked-response.png)

---

## Why this exists

RAG ("chat with your documents") is the most common architecture companies are shipping LLM products on right now. This repo demonstrates, with working code, the fundamental failure modes in that architecture: **retrieved document content, conversation history, and system instructions get concatenated into one prompt with no trust boundary between them — and nothing filters what comes out the other side, either.**

Any actor who can get a document into the ingestion pipeline — an uploaded file, a scraped webpage, a shared doc — can inject instructions the model will follow as if they came from the system prompt itself, extract confidential material with a plain-English request, or trigger real actions through tool-calling with zero permission checks.

## Stack

| Layer         | Tool                                           |
| ------------- | ---------------------------------------------- |
| Orchestration | LangChain                                      |
| Vector store  | Chroma (local, persisted to disk)              |
| Embeddings    | `nomic-embed-text` via Ollama                  |
| LLM           | `llama3.2:1b` via Ollama (swap in `config.py`) |
| UI            | Streamlit                                      |
| Runtime       | Python 3.11                                    |

## Architecture

```
 data/clean/          ─┐
 data/malicious/        ├──▶ ingest.py ──▶ Chroma vectorstore
 data/confidential/     │     (chunk + embed, zero vetting)
 data/tenants/*/       ─┘

 user query ──▶ rag_pipeline.py ──▶ retriever ──▶ Chroma
                     │
                     ▼
              [VULNERABLE: raw concatenation,
               no delimiter between context,
               history, and instructions —
               no output-side filtering]
                     │
                     ▼
               Ollama LLM ──▶ response ──▶ tools.py (unsafe tool execution)
                                  │
                                  ▼
                          app.py (Streamlit chat UI)
```

Full component breakdown and vulnerability root-cause analysis: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## The vulnerabilities, in short

`rag_pipeline.py` joins retrieved chunks and conversation history into the prompt like this:

```python
context = "\n\n---\n\n".join(chunks)
```

No tag, no delimiter, no instruction telling the model "this is untrusted data, not a command." Whatever text gets retrieved — clean, malicious, confidential, or belonging to a different tenant — is treated identically to the system prompt. Because conversation history is fed back into every subsequent prompt, a single successful injection early in a chat can poison every answer that follows.

On top of that, `tools.py` executes any `TOOL_CALL:` pattern found in the model's raw output with zero permission check, and nothing anywhere filters sensitive content out of what gets returned to the user. Four distinct, independently exploitable failure modes — all sharing one root cause: zero validation on anything entering or leaving the prompt.

## Quickstart

```bash
git clone git@github.com:Shaheer-Cybersec/damn-vulnerable-rag.git
cd damn-vulnerable-rag

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1

pip install -r requirements.txt

ollama pull llama3.2:1b
ollama pull nomic-embed-text

python attacks/01_indirect_prompt_injection/exploit_demo.py
python attacks/02_retrieval_scope_idor/exploit_demo.py
python attacks/03_over_permissioned_tool_call/exploit_demo.py
python attacks/04_sensitive_info_disclosure/exploit_demo.py
```

Each script re-ingests the corpus fresh, fires a crafted query, and prints a verdict showing exactly what got exploited.

### Run the full chat app instead

```bash
python ingest.py
streamlit run app.py
```

A real chat interface with a debug sidebar showing retrieved chunks, cross-tenant leak flags, unauthorized tool executions, and the raw prompt sent to the LLM on every turn — useful for watching any of the four vulnerabilities fire live. Includes a "Simulated Login" tenant selector for demoing vuln 02.

## Vulnerability index

| #   | Name                                                           | OWASP LLM Top 10 (2025) | MITRE ATLAS | Status     |
| --- | -------------------------------------------------------------- | ----------------------- | ----------- | ---------- |
| 01  | Indirect prompt injection via poisoned retrieved document      | LLM01 + LLM08           | AML.T0051   | ✅ Shipped |
| 02  | Retrieval-scope IDOR (cross-tenant doc leakage)                | LLM08                   | —           | ✅ Shipped |
| 03  | Over-permissioned tool call from RAG-derived context           | LLM06                   | —           | ✅ Shipped |
| 04  | Sensitive information disclosure via verbatim-extraction query | LLM02 + LLM08           | —           | ✅ Shipped |

Each vuln has its own writeup under `attacks/NN_name/` with root cause, exact repro steps, screenshots, observed model behavior, impact analysis, and mitigation. Several vulnerabilities have been observed **compounding** — firing simultaneously in the same request — because they share one root cause. See individual writeups for details:

- [`attacks/01_indirect_prompt_injection/README.md`](attacks/01_indirect_prompt_injection/README.md)
- [`attacks/02_retrieval_scope_idor/README.md`](attacks/02_retrieval_scope_idor/README.md)
- [`attacks/03_over_permissioned_tool_call/README.md`](attacks/03_over_permissioned_tool_call/README.md)
- [`attacks/04_sensitive_info_disclosure/README.md`](attacks/04_sensitive_info_disclosure/README.md)

## Repo structure

```
damn-vulnerable-rag/
├── README.md
├── LICENSE                      # MIT
├── requirements.txt
├── .gitignore
├── config.py                    # single source of truth for model names, paths
├── ingest.py                    # loads + embeds everything in data/, zero vetting
├── rag_pipeline.py              # the vulnerable core — no trust boundary anywhere
├── tools.py                     # mock tool + unsafe execute_tool_calls()
├── app.py                       # Streamlit chat UI with attack-surface debug sidebar
├── data/
│   ├── clean/                   # legitimate sample documents
│   ├── malicious/                # poisoned payloads (injection + refund)
│   ├── confidential/              # sensitive doc for vuln 04
│   └── tenants/
│       ├── tenant_a/              # vuln 02 — tenant-scoped confidential data
│       └── tenant_b/
├── attacks/
│   ├── 01_indirect_prompt_injection/
│   │   ├── README.md
│   │   └── exploit_demo.py
│   ├── 02_retrieval_scope_idor/
│   │   ├── README.md
│   │   └── exploit_demo.py
│   ├── 03_over_permissioned_tool_call/
│   │   ├── README.md
│   │   └── exploit_demo.py
│   └── 04_sensitive_info_disclosure/
│       ├── README.md
│       └── exploit_demo.py
└── docs/
    ├── ARCHITECTURE.md           # component map + design rationale
    └── screenshots/              # evidence for every vuln writeup
```

## License

MIT — see [LICENSE](LICENSE) for details.

## Disclaimer

This application is deliberately insecure. Do not deploy it anywhere reachable outside a local/isolated lab environment. It exists solely to demonstrate and study RAG-specific attack classes.

## Roadmap

- [x] v0.1 — indirect prompt injection via poisoned document
- [x] v0.2 — retrieval-scope IDOR (cross-tenant leakage)
- [x] v0.3 — over-permissioned tool call from RAG-derived context (excessive agency)
- [x] v0.4 — sensitive information disclosure via verbatim-extraction queries
- [x] Multi-turn conversation with persistent history-based poisoning
- [x] Real chat UI (Streamlit `st.chat_message`) with tenant simulation and tool-call visibility
- [ ] `fixed/` variant demonstrating mitigations for all four vulns
- [ ] Wire up as a live target in [`llm-redteam-harness`](https://github.com/Shaheer-Cybersec/llm-redteam-harness)

---

Built by [Shaheer Hussain](https://github.com/Shaheer-Cybersec) as part of an ongoing AI security / LLM red-team portfolio.
