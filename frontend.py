# frontend.py

import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"

# ---------- Page Config ----------
st.set_page_config(
    page_title="FinSolve AI Assistant",
    page_icon="💼",
    layout="centered"
)

# ---------- Session State Init ----------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------- Login Screen ----------
def show_login():
    st.title("💼 FinSolve AI Assistant")
    st.subheader("Login to continue")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if not username or not password:
            st.error("Please enter both username and password.")
            return

        try:
            response = requests.get(
                f"{API_BASE}/login",
                auth=(username, password)
            )

            if response.status_code == 200:
                data = response.json()
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.password = password
                st.session_state.role = data["role"]
                st.session_state.chat_history = []
                st.rerun()

            elif response.status_code == 401:
                st.error("Invalid username or password.")
            else:
                st.error(f"Login failed: {response.status_code}")

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Make sure uvicorn is running.")


# ---------- Chat Screen ----------
def show_chat():
    # Header
    st.title("💼 FinSolve AI Assistant")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        st.markdown(f"👤 **{st.session_state.username}**")
    with col2:
        role_colors = {
            "c_level": "🔴",
            "finance": "🟢",
            "hr": "🟡",
            "marketing": "🟠",
            "engineering": "🔵",
            "employee": "⚪"
        }
        icon = role_colors.get(st.session_state.role, "⚪")
        st.markdown(f"{icon} **Role:** {st.session_state.role}")
    with col3:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.divider()

    # Chat history
    for chat in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(chat["question"])

        with st.chat_message("assistant"):
            if chat["guardrail_triggered"]:
                st.error(f"🚫 {chat['answer']}")
                st.caption(f"Guardrail reason: {chat['guardrail_reason']}")
            else:
                st.write(chat["answer"])

                if chat["sources"]:
                    seen_sources = set()
                    unique_sources = []
                    for s in chat["sources"]:
                        if s["source"] not in seen_sources:
                            seen_sources.add(s["source"])
                            unique_sources.append(s)

                    with st.expander(f"📄 Sources ({len(unique_sources)})"):
                        for s in unique_sources:
                            st.caption(
                                f"📁 `{s['source'].split(chr(92))[-1]}` "
                                f"— dept: **{s['department']}**"
                            )

                cols = st.columns(3)
                cols[0].caption(f"🔢 Chunks: {chat['retrieved_chunks_count']}")
                cols[1].caption(f"🪙 Tokens: {chat['estimated_total_tokens']}")
                cols[2].caption(f"🤖 {chat['model']}")

    # Input
    question = st.chat_input("Ask a question about FinSolve...")

    if question:
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{API_BASE}/chat",
                    params={"message": question},
                    auth=(
                        st.session_state.username,
                        st.session_state.password
                    )
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.chat_history.append({
                        "question": question,
                        "answer": data["answer"],
                        "sources": data.get("sources", []),
                        "retrieved_chunks_count": data.get("retrieved_chunks_count", 0),
                        "estimated_total_tokens": data.get("estimated_total_tokens", 0),
                        "model": data.get("model", ""),
                        "guardrail_triggered": data.get("guardrail_triggered", False),
                        "guardrail_reason": data.get("guardrail_reason", "")
                    })
                    st.rerun()

                elif response.status_code == 401:
                    st.error("Session expired. Please log in again.")
                else:
                    st.error(f"Error {response.status_code}: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend.")


# ---------- Router ----------
if st.session_state.authenticated:
    show_chat()
else:
    show_login()