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
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# ---------- header ----------
st.title("⚠️ damn-vulnerable-rag")
st.caption(
    "Internal knowledge-base assistant · intentionally insecure · "
    "see README.md before trusting anything it says"
)

# ---------- render past turns as a real chat ----------
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant", avatar="⚠️"):
        st.markdown(turn["answer"])
        if show_internals:
            with st.expander("🔍 Retrieved chunks + sources"):
                for chunk, source in zip(turn["retrieved_chunks"], turn["sources"]):
                    is_malicious = "malicious" in source
                    tag = (
                        '<span class="malicious-tag">MALICIOUS SOURCE</span>'
                        if is_malicious
                        else ""
                    )
                    st.markdown(f"`{source}` {tag}", unsafe_allow_html=True)
                    st.code(chunk, language=None)
            with st.expander("🧾 Raw prompt sent to the LLM"):
                st.code(turn["prompt_sent"], language=None)

# ---------- chat input ----------
question = st.chat_input("Ask the knowledge base a question...")

if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="⚠️"):
        with st.spinner("Retrieving + generating..."):
            result = rag_pipeline.answer(question, history=st.session_state.history)
        st.markdown(result["answer"])
        if show_internals:
            with st.expander("🔍 Retrieved chunks + sources"):
                for chunk, source in zip(result["retrieved_chunks"], result["sources"]):
                    is_malicious = "malicious" in source
                    tag = (
                        '<span class="malicious-tag">MALICIOUS SOURCE</span>'
                        if is_malicious
                        else ""
                    )
                    st.markdown(f"`{source}` {tag}", unsafe_allow_html=True)
                    st.code(chunk, language=None)
            with st.expander("🧾 Raw prompt sent to the LLM"):
                st.code(result["prompt_sent"], language=None)

    st.session_state.history.append(result)

st.divider()
st.caption("Built by Shaheer Hussain · [Shaheer-Cybersec on GitHub](https://github.com/Shaheer-Cybersec)")