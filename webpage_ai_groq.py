import streamlit as st
from groq import Groq
from pypdf import PdfReader
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Adrito's AI 2026", page_icon="🚀", layout="wide")

# Custom Styling for the "Delete" buttons
st.markdown("""
    <style>
    .stButton>button { border-radius: 5px; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Memory Initialization ---
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"Default Chat": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Default Chat"

# --- 3. Sidebar: Document Center & History ---
with st.sidebar:
    st.title("📁 Document Center")
    uploaded_file = st.file_uploader("Upload PDF, Python, or Text", type=["pdf", "txt", "py", "md"])
    
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
            st.error(f"Error: {e}")

    st.divider()
    st.title("📂 Chat History")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_id = f"Chat {datetime.now().strftime('%H:%M:%S')}"
        st.session_state.all_sessions[new_id] = []
        st.session_state.current_chat = new_id
        st.rerun()

    st.divider()

    # --- History List with Delete Buttons ---
    for chat_title in list(st.session_state.all_sessions.keys()):
        cols = st.columns([0.8, 0.2]) # Create two columns: one for Title, one for Delete
        
        # Column 1: The Chat Title Button
        with cols[0]:
            btn_type = "primary" if chat_title == st.session_state.current_chat else "secondary"
            if st.button(chat_title, use_container_width=True, type=btn_type, key=f"select_{chat_title}"):
                st.session_state.current_chat = chat_title
                st.rerun()
        
        # Column 2: The Delete Button (Trash Icon)
        with cols[1]:
            if st.button("🗑️", key=f"del_{chat_title}", help="Delete this chat"):
                del st.session_state.all_sessions[chat_title]
                # If we delete the current chat, go back to Default or the first one left
                if st.session_state.current_chat == chat_title:
                    remaining = list(st.session_state.all_sessions.keys())
                    st.session_state.current_chat = remaining[0] if remaining else "Default Chat"
                    if not remaining: st.session_state.all_sessions["Default Chat"] = []
                st.rerun()

# --- 4. Main Chat Logic ---
st.title(f"🚀 {st.session_state.current_chat}")
messages = st.session_state.all_sessions.get(st.session_state.current_chat, [])

# Display current chat history
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 5. AI Engine ---
key = st.secrets.get("GROQ_API_KEY")
if not key:
    st.warning("Please add your API key to Secrets!")
    st.stop()

client = Groq(api_key=key)

if prompt := st.chat_input("Start a conversation..."):
    # Add user message
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Date Fix for 2026
    sys_msg = f"Today is {datetime.now().strftime('%B %d, %Y')}. Year is 2026. Use context if provided."
    
    user_payload = prompt
    if context_text:
        user_payload = f"DOCUMENT CONTEXT:\n{context_text[:8000]}\n\nUSER QUESTION: {prompt}"

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Build API payload
        api_history = [{"role": "system", "content": sys_msg}]
        for m in messages[:-1]: api_history.append(m)
        api_history.append({"role": "user", "content": user_payload})

        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=api_history,
                stream=True,
            )
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
            messages.append({"role": "assistant", "content": full_res})
            
            # Auto-Rename Chat based on first prompt
            if len(messages) == 2 and st.session_state.current_chat.startswith("Chat "):
                new_title = prompt[:20] + "..." if len(prompt) > 20 else prompt
                st.session_state.all_sessions[new_title] = st.session_state.all_sessions.pop(st.session_state.current_chat)
                st.session_state.current_chat = new_title
                
            st.rerun()
        except Exception as e:
            st.error(f"API Error: {e}")
