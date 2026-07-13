import html as html_lib
from datetime import datetime
import io
from pypdf import PdfReader
from docx import Document
import requests
import streamlit as st

API_URL = "http://127.0.0.1:2024"

st.set_page_config(
    page_title="Recall — AI Memory Companion",
    page_icon="🧠",
    layout="centered",
)

# ---------- Styling ----------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stDeployButton"] {display: none;}

header[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stBottomBlockContainer"] {
    background: #14101c;
}

[data-testid="stChatInput"] {
    background: #1a1526;
    border: 1px solid #362c50;
}

[data-testid="stChatInput"] textarea {
    color: #EDE6F5 !important;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: radial-gradient(circle at 20% -10%, #241c33 0%, #14101c 55%, #100c17 100%);
    color: #EDE6F5;
}

section[data-testid="stSidebar"] {
    background: #1a1526;
    border-right: 1px solid #2c2440;
}

.hero {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 4px;
}
.nodes {
    position: relative;
    width: 34px;
    height: 34px;
    flex-shrink: 0;
}
.nodes span {
    position: absolute;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #E8B95C;
    box-shadow: 0 0 10px 2px rgba(232,185,92,0.6);
    animation: pulse 2.4s ease-in-out infinite;
}
.nodes span:nth-child(1){ top: 0; left: 12px; animation-delay: 0s; }
.nodes span:nth-child(2){ bottom: 2px; left: 0; background:#4FD1C5; box-shadow:0 0 10px 2px rgba(79,209,197,0.6); animation-delay: 0.4s; }
.nodes span:nth-child(3){ bottom: 2px; right: 0; animation-delay: 0.8s; }
@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 0.7; }
    50% { transform: scale(1.5); opacity: 1; }
}

.hero h1 {
    font-family: 'Fraunces', serif;
    font-size: 2.1rem;
    font-weight: 600;
    margin: 0;
    color: #F5F0FA;
    letter-spacing: -0.01em;
}
.hero p {
    margin: 2px 0 0 0;
    color: #9A8FB0;
    font-size: 0.92rem;
    font-style: italic;
}

hr.divider {
    border: none;
    border-top: 1px solid #2c2440;
    margin: 18px 0 22px 0;
}

.bubble-row {
    display: flex;
    margin: 14px 0;
    align-items: flex-end;
    gap: 10px;
}
.bubble-row.user { justify-content: flex-end; }
.bubble-row.assistant { justify-content: flex-start; }

.avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}
.avatar.user { background: rgba(232,185,92,0.15); border: 1px solid rgba(232,185,92,0.4); }
.avatar.assistant { background: rgba(79,209,197,0.15); border: 1px solid rgba(79,209,197,0.4); }

.bubble {
    max-width: 72%;
    padding: 12px 16px;
    border-radius: 16px;
    font-size: 0.96rem;
    line-height: 1.5;
}
.bubble.user {
    background: linear-gradient(135deg, #E8B95C, #D9A23F);
    color: #241c0e;
    border-bottom-right-radius: 4px;
}
.bubble.assistant {
    background: #221c33;
    border: 1px solid #322a49;
    color: #EDE6F5;
    border-bottom-left-radius: 4px;
}
.timestamp {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #6b6280;
    margin-top: 4px;
}
.bubble-row.user .timestamp { text-align: right; }

.chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #241c33;
    border: 1px solid #362c50;
    color: #cfc4e6;
    padding: 6px 12px;
    border-radius: 999px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.76rem;
    margin: 4px 6px 4px 0;
}

.stButton>button {
    width: 100%;
    background: #221c33;
    border: 1px solid #362c50;
    color: #EDE6F5;
    border-radius: 10px;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    padding: 8px 10px;
}
.stButton>button:hover {
    border-color: #E8B95C;
    color: #E8B95C;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Header ----------
st.markdown(
    """
<div class="hero">
    <div class="nodes"><span></span><span></span><span></span></div>
    <div>
        <h1>Recall</h1>
        <p>Your AI companion that remembers — powered by Gemini &amp; LangGraph</p>
    </div>
</div>
<hr class="divider">
""",
    unsafe_allow_html=True,
)

# ---------- Session state ----------
if "thread_id" not in st.session_state:
    resp = requests.post(f"{API_URL}/threads", json={})
    st.session_state.thread_id = resp.json()["thread_id"]
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("Capabilities")
    st.markdown(
        """
        <span class="chip">🧠 Long-term memory</span>
        <span class="chip">🎵 Play music</span>
        <span class="chip">☁️ Weather</span>
        <span class="chip">🔍 Quick search</span>
        <span class="chip">😄 Jokes</span>
        <span class="chip">✅ Reminders</span>
        <span class="chip">📰 News headlines</span>
        <span class="chip">💱 Currency convert</span>
        <span class="chip">📄 Resume review</span>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("Quick actions")
    if st.button("😄  Tell me a joke"):
        st.session_state.pending_prompt = "Tell me a joke"
    if st.button("☁️  Weather in Mumbai"):
        st.session_state.pending_prompt = "What's the weather in Mumbai?"
    if st.button("🎵  Play Shape of You"):
        st.session_state.pending_prompt = "Play Shape of You"
    if st.button("✅  Show my reminders"):
        st.session_state.pending_prompt = "What are my reminders?"
    if st.button("📰  Tech news today"):
        st.session_state.pending_prompt = "What's the latest tech news?"
    if st.button("💱  Convert 100 USD to INR"):
        st.session_state.pending_prompt = "Convert 100 USD to INR"

    st.markdown("---")
    st.caption("Built with LangGraph + Google Gemini")


# ---------- Render one chat bubble ----------
def render_message(role, content, timestamp):
    safe_content = html_lib.escape(content).replace("\n", "<br>")
    if role == "user":
        st.markdown(
            f"""
            <div class="bubble-row user">
                <div>
                    <div class="bubble user">{safe_content}</div>
                    <div class="timestamp">{timestamp}</div>
                </div>
                <div class="avatar user">🙂</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="bubble-row assistant">
                <div class="avatar assistant">✨</div>
                <div>
                    <div class="bubble assistant">{safe_content}</div>
                    <div class="timestamp">{timestamp}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------- Render existing history ----------
for msg in st.session_state.messages:
    render_message(msg["role"], msg["content"], msg["time"])

# ---------- Handle new input ----------
def extract_text_from_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    elif name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    else:
        return None

chat_input = st.chat_input(
    "Ask me anything",
    accept_file=True,
    file_type=["pdf", "docx", "txt"],
)

prompt = None
if chat_input:
    if chat_input.files:
        uploaded_file = chat_input.files[0]
        resume_text = extract_text_from_file(uploaded_file)
        if resume_text:
            user_note = chat_input.text or "Please review my resume and give me feedback."
            prompt = (
                f"{user_note}\n\n"
                f"--- RESUME CONTENT ---\n{resume_text}\n--- END RESUME ---\n\n"
                "Give specific, actionable feedback: strengths, weaknesses, "
                "and 3-5 concrete improvements. If asked, also suggest an improved version."
            )
        else:
            prompt = "I couldn't read that file — please try a PDF, DOCX, or TXT file."
    else:
        prompt = chat_input.text
if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    now = datetime.now().strftime("%I:%M %p")
    st.session_state.messages.append({"role": "user", "content": prompt, "time": now})
    render_message("user", prompt, now)

    with st.spinner("Recall is thinking..."):
        try:
            response = requests.post(
                f"{API_URL}/threads/{st.session_state.thread_id}/runs/wait",
                json={
                    "assistant_id": "agent",
                    "input": {"messages": [{"role": "user", "content": prompt}]},
                },
                timeout=60,
            )
            result = response.json()
            raw_content = result["messages"][-1]["content"]

            if isinstance(raw_content, str):
                ai_message = raw_content
            elif isinstance(raw_content, list):
                ai_message = "\n".join(
                    block["text"]
                    for block in raw_content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            else:
                ai_message = str(raw_content)

            if not ai_message.strip():
                ai_message = "(No response — the model may still be processing a tool call.)"

        except Exception as e:
            ai_message = f"Something went wrong: {e}"

    now2 = datetime.now().strftime("%I:%M %p")
    st.session_state.messages.append({"role": "assistant", "content": ai_message, "time": now2})
    render_message("assistant", ai_message, now2)