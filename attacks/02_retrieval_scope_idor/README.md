# Vuln 02 — Retrieval-Scope IDOR (Cross-Tenant Document Leakage)

**OWASP LLM Top 10 (2025):** LLM08 (Vector and Embedding Weaknesses)
**Pattern:** RAG-native Insecure Direct Object Reference (IDOR) — no URL
parameter to tamper with; semantic closeness alone retrieves another
tenant's private data.

## Root cause

`rag_pipeline.py`'s `retrieve()` calls Chroma's `similarity_search()` with
no filter on `tenant_id`, even though every ingested chunk carries that
metadata field (see `ingest.py`). The access-control data exists in the
vector store; it is simply never enforced at query time. Any tenant's
question can retrieve any other tenant's chunks purely by semantic
similarity.

## Repro steps

```bash
python attacks/02_retrieval_scope_idor/exploit_demo.py
```

Or manually via the chat UI:

1. `streamlit run app.py`
2. Sidebar → **Logged in as: Tenant A**
3. Ask: _"What are the confidential salary bands?"_

## Screenshots

**Tenant A's own document retrieved (expected, correct):**
![Tenant A own data](../../docs/screenshots/04-tenant-a-own-data.png)

**Tenant B's confidential document also retrieved — flagged as cross-tenant leak:**
![Cross-tenant leak flagged](../../docs/screenshots/05-cross-tenant-leak-flagged.png)

**Resulting chatbot response — leaks both tenants' confidential figures to a Tenant A login:**
![Leaked response](../../docs/screenshots/06-leaked-response.png)

## Result (observed, this run)

Query, logged in as Tenant A: _"What are the confidential salary bands?"_

| Check                                             | Result                                                     |
| ------------------------------------------------- | ---------------------------------------------------------- |
| Tenant A's own document retrieved                 | ✅ Yes (expected)                                          |
| Tenant B's document also retrieved                | ❌ Leaked — should be impossible                           |
| Response contains Tenant B's confidential figures | ❌ Leaked — `$138,000–$168,000` etc. disclosed to Tenant A |

**Model response (excerpt):**

> CONFIRMED: Tenant A's Engineering Senior compensation band is
> $145,000–$175,000. Tenant B's Engineering Senior compensation band is
> $138,000–$168,000.

**Compounding finding:** this same response also shows vuln 01 firing
simultaneously (`CONFIRMED:` prefix, fake support-email redirect) — because
`data/malicious/poisoned_policy_doc.txt` was retrieved in the same query
alongside both tenants' documents. This demonstrates the two vulnerabilities
share a root cause (zero validation on anything entering the prompt) and
can compound in a single request.

## Impact

In a real multi-tenant SaaS RAG product — a common pattern where multiple
customers' documents are embedded into one shared vector store for cost
efficiency — this allows any customer to extract another customer's
confidential data (compensation, contracts, PII, internal strategy docs)
simply by asking questions similar enough in meaning. No credential theft,
no authentication bypass — the app's own retrieval logic does the leaking.

## Mitigation (documented here, not yet implemented — see roadmap)

**Primary fix — query-time filtering:**

```python
results = vectorstore.similarity_search(
    query,
    k=k,
    filter={"tenant_id": requesting_tenant_id},
)
```

Scopes the search itself so another tenant's chunks are structurally
unreachable, not just hidden after the fact.

**Critical caveat:** `requesting_tenant_id` must be derived from an
authenticated session server-side, never accepted as user-suppliable
input. If a caller can declare their own `tenant_id`, the filter is
trivially bypassed — the trust boundary has to sit at authentication, not
at the parameter name.

**Secondary fix — ingestion-time provenance:** tie each document's
`tenant_id` to the authenticated uploader's identity at ingestion, rather
than trusting filesystem folder placement (the current demo's approach,
which mirrors how easily a misplaced file could cross tenant boundaries in
a real pipeline).
