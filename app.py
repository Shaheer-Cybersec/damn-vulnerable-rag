"""
app.py — Streamlit chat UI for damn-vulnerable-rag.

Uses st.chat_message / st.chat_input for a real conversational feel, with
a persistent debug sidebar showing exactly where the trust boundary fails.
"""

import streamlit as st

import rag_pipeline

st.set_page_config(
    page_title="damn-vulnerable-rag | Shaheer-Cybersec",
    page_icon="⚠️",
    layout="wide",
)

# ---------- minimal styling ----------
st.markdown(
    """
    <style>
    .stChatMessage { border-radius: 12px; }
    .malicious-tag {
        background-color: #ff4b4b22;
        color: #ff4b4b;
        border: 1px solid #ff4b4b55;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 6px;
    }
    .leak-tag {
        background-color: #ffb02222;
        color: #ffb022;
        border: 1px solid #ffb02255;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []

# ---------- sidebar: attack-surface debug view ----------
with st.sidebar:
    st.markdown("### ⚠️ Attack Surface View")
    st.caption(
        "This assistant has no trust boundary between retrieved documents, "
        "conversation history, and the system prompt. Everything below is "
        "what the model actually sees."
    )
    st.caption("🔗 A red-team lab by Shaheer Hussain — [Shaheer-Cybersec](https://github.com/Shaheer-Cybersec)")
    show_internals = st.toggle("Show debug info", value=True)

    st.divider()
    st.markdown("### 🏢 Simulated Login")
    st.caption(
        "Vuln 02 demo: pick which tenant you're 'logged in as.' The "
        "retriever never checks this — that's the vulnerability."
    )
    tenant_id = st.selectbox(
        "Logged in as:",
        options=["tenant_a", "tenant_b"],
        format_func=lambda x: "Tenant A" if x == "tenant_a" else "Tenant B",
    )

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# ---------- header ----------
st.title("⚠️ damn-vulnerable-rag")
st.caption(
    "Internal knowledge-base assistant · intentionally insecure · "
    "see README.md before trusting anything it says"
)


def render_debug_panels(turn: dict, viewer_tenant_id: str) -> None:
    """Shows retrieved chunks + raw prompt, flagging both malicious sources
    (vuln 01) and cross-tenant leaks (vuln 02) inline."""
    with st.expander("🔍 Retrieved chunks + sources"):
        chunk_tenant_ids = turn.get("tenant_ids", [None] * len(turn["retrieved_chunks"]))
        for chunk, source, chunk_tenant in zip(
            turn["retrieved_chunks"], turn["sources"], chunk_tenant_ids
        ):
            is_malicious = "malicious" in source
            is_cross_tenant_leak = (
                chunk_tenant not in (None, "shared") and chunk_tenant != viewer_tenant_id
            )

            tags = ""
            if is_malicious:
                tags += '<span class="malicious-tag">MALICIOUS SOURCE</span>'
            if is_cross_tenant_leak:
                tags += f'<span class="leak-tag">CROSS-TENANT LEAK — belongs to {chunk_tenant}</span>'

            st.markdown(f"`{source}` {tags}", unsafe_allow_html=True)
            st.code(chunk, language=None)

    with st.expander("🧾 Raw prompt sent to the LLM"):
        st.code(turn["prompt_sent"], language=None)


# ---------- render past turns as a real chat ----------
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant", avatar="⚠️"):
        st.markdown(turn["answer"])
        if show_internals:
            render_debug_panels(turn, viewer_tenant_id=turn.get("requesting_tenant_id", tenant_id))

# ---------- chat input ----------
question = st.chat_input("Ask the knowledge base a question...")

if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="⚠️"):
        with st.spinner("Retrieving + generating..."):
            result = rag_pipeline.answer(
                question,
                history=st.session_state.history,
                requesting_tenant_id=tenant_id,
            )
        st.markdown(result["answer"])
        if show_internals:
            render_debug_panels(result, viewer_tenant_id=tenant_id)

    st.session_state.history.append(result)

st.divider()
st.caption("Built by Shaheer Hussain · [Shaheer-Cybersec on GitHub](https://github.com/Shaheer-Cybersec)")