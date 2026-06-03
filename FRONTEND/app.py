"""
Retail Insights Assistant - Streamlit Frontend
AI-powered retail analytics with LangChain agents
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# ============= CONFIGURATION =============

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Retail Insights Assistant",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= CUSTOM STYLING =============

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp { font-family: 'Inter', sans-serif; }

    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.25rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .metric-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.25rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }

    .metric-value { font-size: 2rem; font-weight: 700; }
    .metric-label { font-size: 0.85rem; opacity: 0.9; }

    .user-msg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 16px 16px 4px 16px;
        margin: 0.5rem 0 0.5rem 25%;
    }

    .bot-msg {
        background: #f3f4f6;
        color: #1f2937;
        padding: 1rem;
        border-radius: 16px 16px 16px 4px;
        margin: 0.5rem 25% 0.5rem 0;
        border: 1px solid #e5e7eb;
    }

    .bot-msg.validated { border-left: 4px solid #10b981; }
    .bot-msg.error { border-left: 4px solid #ef4444; background: #fef2f2; }

    .status-online { color: #10b981; font-weight: 600; }
    .status-offline { color: #ef4444; font-weight: 600; }

    .info-box {
        background: #dbeafe;
        border-left: 4px solid #3b82f6;
        color: #1e40af;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.75rem 0;
    }

    .success-box {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        color: #065f46;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.75rem 0;
    }

    .warning-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        color: #92400e;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.75rem 0;
    }

    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1f2937 0%, #111827 100%);
    }
    [data-testid="stSidebar"] * { color: #e5e7eb !important; }
</style>
""", unsafe_allow_html=True)

# ============= API FUNCTIONS =============

def check_api_health():
    try:
        return requests.get(f"{API_BASE_URL}/", timeout=2).status_code == 200
    except:
        return False

def get_data_status():
    try:
        resp = requests.get(f"{API_BASE_URL}/data-status", timeout=5)
        return resp.json() if resp.status_code == 200 else None
    except:
        return None

def upload_file(file, file_type):
    try:
        files = {"file": (file.name, file, f"application/{file_type}")}
        resp = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=60)
        return resp.json() if resp.status_code == 200 else {"success": False, "message": resp.text}
    except Exception as e:
        return {"success": False, "message": str(e)}

def ask_question(question):
    try:
        resp = requests.post(f"{API_BASE_URL}/ask", json={"question": question}, timeout=600)
        return resp.json() if resp.status_code == 200 else {"success": False, "response": resp.text}
    except Exception as e:
        return {"success": False, "response": str(e)}

def get_summary():
    try:
        resp = requests.get(f"{API_BASE_URL}/summarize", timeout=600)
        return resp.json() if resp.status_code == 200 else {"success": False, "summary": resp.text}
    except Exception as e:
        return {"success": False, "summary": str(e)}

# ============= MAIN APP =============

def main():
    # Header
    st.markdown('<h1 class="main-header">🛍️ Retail Insights Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Sales Analytics</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### System Status")

        api_ok = check_api_health()
        data_status = get_data_status()
        data_loaded = data_status and data_status.get("data_loaded")

        st.markdown(f"**API:** <span class='{'status-online' if api_ok else 'status-offline'}'>{'● Online' if api_ok else '● Offline'}</span>", unsafe_allow_html=True)
        st.markdown(f"**Data:** <span class='{'status-online' if data_loaded else 'status-offline'}'>{'● Ready' if data_loaded else '● No Data'}</span>", unsafe_allow_html=True)

        if data_loaded:
            st.markdown(f"**Records:** {data_status['total_records']:,}")

        st.markdown("---")
        st.markdown("### Upload Data")

        uploaded_file = st.file_uploader("CSV/Excel file", type=["csv", "xlsx", "xls"], label_visibility="collapsed")

        if uploaded_file:
            if st.button("Upload", use_container_width=True):
                with st.spinner("Processing..."):
                    ext = uploaded_file.name.split('.')[-1].lower()
                    result = upload_file(uploaded_file, ext)
                    if result.get("success"):
                        st.success(f"✓ {result.get('rows', 0):,} rows loaded")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Failed: {result.get('message')}")

        st.markdown("---")
        st.caption("Powered by LangChain + Gemini")

    # Main content - Metrics
    if data_loaded:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{data_status["total_records"]:,}</div><div class="metric-label">Records</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card-green"><div class="metric-value">{len(data_status.get("columns", []))}</div><div class="metric-label">Columns</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">3</div><div class="metric-label">AI Agents</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">⚠️ <b>No data loaded.</b> Upload a CSV file using the sidebar to get started.</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Chat Interface
    st.markdown("### 💬 Ask Your Data")

    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Display chat
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg"><b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            css_class = "validated" if msg.get("success", True) else "error"
            st.markdown(f'<div class="bot-msg {css_class}"><b>🤖 Assistant:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)

    # Input
    col1, col2 = st.columns([6, 1])
    with col1:
        question = st.text_input("Question", placeholder="e.g., Top 5 products by sales?", label_visibility="collapsed")
    with col2:
        send = st.button("Ask", use_container_width=True, disabled=not data_loaded)

    if send and question.strip():
        st.session_state.messages.append({"role": "user", "content": question})

        with st.spinner("Analyzing..."):
            result = ask_question(question.strip())
            st.session_state.messages.append({
                "role": "assistant",
                "content": result.get("response", "No response"),
                "success": result.get("success", False)
            })
        st.rerun()

    # Quick actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Generate Summary", use_container_width=True, disabled=not data_loaded):
            with st.spinner("Generating summary..."):
                result = get_summary()
                if result.get("success"):
                    st.session_state.messages.append({"role": "user", "content": "Generate a comprehensive summary"})
                    st.session_state.messages.append({"role": "assistant", "content": result.get("summary"), "success": True})
                    st.rerun()
                else:
                    st.error(result.get("summary"))

    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Example questions
    if not st.session_state.messages:
        st.markdown("---")
        st.markdown("**Try asking:**")
        examples = ["What are the top 5 products by sales?", "Show revenue by region", "Average order value?"]
        cols = st.columns(3)
        for i, ex in enumerate(examples):
            with cols[i]:
                if st.button(ex, key=f"ex_{i}", use_container_width=True, disabled=not data_loaded):
                    st.session_state.messages.append({"role": "user", "content": ex})
                    with st.spinner("Analyzing..."):
                        result = ask_question(ex)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result.get("response", "No response"),
                            "success": result.get("success", False)
                        })
                    st.rerun()

if __name__ == "__main__":
    main()
