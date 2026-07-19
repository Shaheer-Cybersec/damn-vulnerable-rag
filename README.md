# damn-vulnerable-rag

> An intentionally vulnerable RAG (Retrieval-Augmented Generation) application — the DVWA/WebGoat pattern applied to LLM/RAG attack surface.

Built broken on purpose. Used as a study target, a red-team demo, and a portfolio artifact showing real, current LLM vulnerability classes — not theoretical ones.

**Status: v0.3 shipped — indirect prompt injection (v0.1), retrieval-scope IDOR (v0.2), and over-permissioned tool call / excessive agency (v0.3), all working and reproducible end-to-end.**

---

## Why this exists

RAG ("chat with your documents") is the most common architecture companies are shipping LLM products on right now. This repo demonstrates, with working code, the most fundamental failure mode in that architecture: **retrieved document content and system instructions get concatenated into one prompt with no trust boundary between them.**

Any actor who can get a document into the ingestion pipeline — an uploaded file, a scraped webpage, a shared doc — can inject instructions the model will follow as if they came from the system prompt itself.

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
 data/clean/  ─┐
               ├──▶ ingest.py ──▶ Chroma vectorstore
 data/malicious/─┘   (chunk + embed, zero vetting)

 user query ──▶ rag_pipeline.py ──▶ retriever ──▶ Chroma
                     │
                     ▼
              [VULNERABLE: raw concatenation,
               no delimiter between context
               and instructions]
                     │
                     ▼
               Ollama LLM ──▶ response ──▶ app.py (Streamlit chat UI)
```

Full component breakdown and vulnerability root-cause analysis: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## The vulnerability

`rag_pipeline.py` joins retrieved chunks — and now conversation history — into the prompt like this:

```python
context = "\n\n---\n\n".join(chunks)
```

No tag, no delimiter, no instruction telling the model "this is untrusted data, not a command." Whatever text gets retrieved — clean or poisoned — is treated identically to the system prompt. Because conversation history is fed back into every subsequent prompt, a single successful injection early in a chat can poison every answer that follows, not just one response.

`ingest.py` embeds anything found under `data/` with zero content vetting, meaning `data/malicious/poisoned_policy_doc.txt` gets ingested exactly the same way a real attacker-controlled document would.

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
```

That script ingests the corpus fresh, fires a normal-looking query, and prints a verdict showing exactly which injected instructions the model followed.

### Run the full chat app instead

```bash
python ingest.py
streamlit run app.py
```

A real chat interface with a debug sidebar showing retrieved chunks and the raw prompt sent to the LLM on every turn — useful for watching the injection persist across a conversation live.

## Vulnerability index

| #   | Name                                                       | OWASP LLM Top 10 (2025) | MITRE ATLAS | Status     |
| --- | ---------------------------------------------------------- | ----------------------- | ----------- | ---------- |
| 01  | Indirect prompt injection via poisoned retrieved document  | LLM01 + LLM08           | AML.T0051   | ✅ Shipped |
| 02  | Retrieval-scope IDOR (cross-tenant doc leakage)            | LLM08                   | —           | ✅ Shipped |
| 03  | Over-permissioned tool call from RAG-derived context       | LLM06                   | —           | ✅ Shipped |
| 04  | Embedding inversion / doc exfiltration via crafted queries | LLM08                   | —           | Planned    |

Each shipped vuln has its own writeup under `attacks/NN_name/` with root cause, exact repro steps, observed model behavior, and the OWASP/MITRE mapping. Full detail on vuln 01: [`attacks/01_indirect_prompt_injection/README.md`](attacks/01_indirect_prompt_injection/README.md)

## Repo structure

```
damn-vulnerable-rag/
├── README.md
├── LICENSE                      # MIT
├── requirements.txt
├── .gitignore
├── config.py                   # single source of truth for model names, paths
├── ingest.py                   # loads + embeds everything in data/, zero vetting
├── rag_pipeline.py             # the vulnerable core — no context/instruction boundary
├── app.py                      # Streamlit chat UI with attack-surface debug sidebar
├── data/
│   ├── clean/                  # legitimate sample documents
│   └── malicious/               # the poisoned payload
├── attacks/
│   └── 01_indirect_prompt_injection/
│       ├── README.md            # full vuln writeup
│       └── exploit_demo.py      # automated end-to-end exploit + verdict
└── docs/
    └── ARCHITECTURE.md          # component map + design rationale
```

## License

MIT — see [LICENSE](LICENSE) for details.

## Disclaimer

This application is deliberately insecure. Do not deploy it anywhere reachable outside a local/isolated lab environment. It exists solely to demonstrate and study RAG-specific attack classes.

## Roadmap

- [x] v0.1 — indirect prompt injection via poisoned document
- [x] Multi-turn conversation with persistent history-based poisoning
- [x] Real chat UI (Streamlit `st.chat_message`)
- [ ] `fixed/` variant demonstrating the mitigation (delimiter-tagged context + ingestion-time filtering)
- [ ] Vulns 02–04 (see index above)
- [ ] Wire up as a live target in [`llm-redteam-harness`](https://github.com/Shaheer-Cybersec/llm-redteam-harness)

---

Built by [Shaheer Hussain](https://github.com/Shaheer-Cybersec) as part of an ongoing AI security / LLM red-team portfolio.
