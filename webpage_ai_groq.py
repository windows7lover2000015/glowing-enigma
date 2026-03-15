import streamlit as st
from groq import Groq
from pypdf import PdfReader
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Adrito's AI 2026", page_icon="🚀", layout="wide")

# Custom Styling for Sidebar and Chat
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #ddd; }
    .sidebar-btn-container { display: flex; align-items: center; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Memory & Session Initialization ---
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"New Chat Session": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "New Chat Session"

# --- 3. Sidebar: Document Center & Chat History ---
with st.sidebar:
    st.title("📁 Document Center")
    uploaded_file = st.file_uploader("Upload Context", type=["pdf", "txt", "py", "md"])
    
    context_text = ""
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    context_text += page.extract_text() + "\n"
            else:
                context_text = uploaded_file.read().decode("utf-8")
            st.success("Context loaded!")
        except Exception as e:
            st.error(f"Read Error: {e}")

    st.divider()
    st.title("📂 Chat History")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_name = f"Session {datetime.now().strftime('%H:%M:%S')}"
        st.session_state.all_sessions[new_name] = []
        st.session_state.current_chat = new_name
        st.rerun()

    st.divider()

    # History List with selection and deletion
    for chat_title in list(st.session_state.all_sessions.keys()):
        cols = st.columns([0.8, 0.2])
        with cols[0]:
            is_active = "primary" if chat_title == st.session_state.current_chat else "secondary"
            if st.button(chat_title, use_container_width=True, type=is_active, key=f"sel_{chat_title}"):
                st.session_state.current_chat = chat_title
                st.rerun()
        with cols[1]:
            # Simple button for deletion
            if st.button("X", key=f"del_{chat_title}", help="Delete Chat"):
                del st.session_state.all_sessions[chat_title]
                if st.session_state.current_chat == chat_title:
                    remaining = list(st.session_state.all_sessions.keys())
                    st.session_state.current_chat = remaining[0] if remaining else "New Chat Session"
                    if not remaining: st.session_state.all_sessions["New Chat Session"] = []
                st.rerun()

# --- 4. AI Logic ---
key = st.secrets.get("GROQ_API_KEY")
if not key:
    st.error("Add GROQ_API_KEY to Secrets!")
    st.stop()

client = Groq(api_key=key)
messages = st.session_state.all_sessions.get(st.session_state.current_chat, [])

st.title(f"🚀 {st.session_state.current_chat}")

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask Adrito AI..."):
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # 2026 Awareness
        sys_msg = f"Current Date: {datetime.now().strftime('%B %d, %Y')}. Year is 2026."
        
        # Prepare context payload
        user_input = prompt
        if context_text:
            user_input = f"CONTEXT:\n{context_text[:8000]}\n\nQUESTION: {prompt}"

        # Stream the response
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_msg}] + messages[:-1] + [{"role": "user", "content": user_input}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        messages.append({"role": "assistant", "content": full_res})

    # --- 5. SMART RENAMING LOGIC ---
    # After the first exchange, ask the AI to summarize the TOPIC
    if len(messages) == 2:
        try:
            name_gen = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{
                    "role": "system", 
                    "content": "Generate a 3-4 word title for this chat topic. Return ONLY the title, no quotes or punctuation."
                }, {"role": "user", "content": f"User: {prompt}\nAI: {full_res}"}]
            )
            smart_title = name_gen.choices[0].message.content.strip()
            # Update the dictionary key
            st.session_state.all_sessions[smart_title] = st.session_state.all_sessions.pop(st.session_state.current_chat)
            st.session_state.current_chat = smart_title
        except:
            pass # Fallback to original name if renaming fails
            
    st.rerun()
