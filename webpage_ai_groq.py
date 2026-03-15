import streamlit as st
from groq import Groq
from pypdf import PdfReader
from datetime import datetime

# --- 1. CRITICAL SETUP ---
# This must be the very first Streamlit command
st.set_page_config(page_title="Adrito's AI 2026", layout="wide")

# --- 2. SESSION STATE (The Memory) ---
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"New Chat Session": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "New Chat Session"

# --- 3. SIDEBAR (File Upload & History) ---
with st.sidebar:
    st.header("📁 Document Center")
    # THE FILE UPLOADER
    uploaded_file = st.file_uploader("Upload PDF or Text", type=["pdf", "txt", "py", "md"])
    
    context_text = ""
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    context_text += page.extract_text() + "\n"
            else:
                context_text = uploaded_file.read().decode("utf-8")
            st.success("File loaded!")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.header("📂 Chat History")
    
    # NEW CHAT BUTTON
    if st.button("➕ Start New Chat", use_container_width=True):
        new_name = f"Session {datetime.now().strftime('%H:%M:%S')}"
        st.session_state.all_sessions[new_name] = []
        st.session_state.current_chat = new_name
        st.rerun()

    # THE HISTORY LIST WITH DELETE BUTTONS
    for chat_title in list(st.session_state.all_sessions.keys()):
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            is_active = "primary" if chat_title == st.session_state.current_chat else "secondary"
            if st.button(chat_title, use_container_width=True, type=is_active, key=f"btn_{chat_title}"):
                st.session_state.current_chat = chat_title
                st.rerun()
        with col2:
            # THE DELETE BUTTON
            if st.button("X", key=f"del_{chat_title}"):
                del st.session_state.all_sessions[chat_title]
                if not st.session_state.all_sessions:
                    st.session_state.all_sessions["New Chat Session"] = []
                st.session_state.current_chat = list(st.session_state.all_sessions.keys())[0]
                st.rerun()

# --- 4. MAIN CHAT AREA ---
st.title(f"🚀 {st.session_state.current_chat}")

# Load API Key
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Missing GROQ_API_KEY in Streamlit Secrets!")
    st.stop()

# Show Messages
messages = st.session_state.all_sessions[st.session_state.current_chat]
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 5. INPUT & SMART NAMING ---
if prompt := st.chat_input("Ask me something..."):
    # Show User Message
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate AI Answer
    with st.chat_message("assistant"):
        full_res = ""
        placeholder = st.empty()
        
        # 2026 Context
        sys_msg = f"Today is {datetime.now().strftime('%B %d, %Y')}. Year is 2026."
        
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_msg}] + messages,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        messages.append({"role": "assistant", "content": full_res})

    # SMART RENAMING LOGIC
    if len(messages) == 2 and st.session_state.current_chat.startswith("Session "):
        try:
            name_gen = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "Summarize the user question into a 2-word title. No quotes."},
                          {"role": "user", "content": prompt}]
            )
            new_title = name_gen.choices[0].message.content.strip()
            st.session_state.all_sessions[new_title] = st.session_state.all_sessions.pop(st.session_state.current_chat)
            st.session_state.current_chat = new_title
        except:
            pass

    st.rerun()
