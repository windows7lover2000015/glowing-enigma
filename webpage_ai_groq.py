import streamlit as st
from groq import Groq
from pypdf import PdfReader
from datetime import datetime

# --- 1. Page Config & Styling ---
st.set_page_config(page_title="Adrito's AI 2026", page_icon="🚀", layout="wide")

# This CSS ensures the Sidebar buttons and File Uploader look clean
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #ddd; }
    [data-testid="stSidebar"] { min-width: 300px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Initialize Permanent Session Memory ---
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"New Chat Session": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "New Chat Session"

# --- 3. Sidebar: Document Center & Smart History ---
with st.sidebar:
    st.header("📁 Document Center")
    # This is the file upload box you need
    uploaded_file = st.file_uploader("Upload PDF, TXT, or PY", type=["pdf", "txt", "py", "md"], key="file_viewer")
    
    context_text = ""
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    context_text += page.extract_text() + "\n"
            else:
                context_text = uploaded_file.read().decode("utf-8")
            st.success("Context loaded successfully!")
        except Exception as e:
            st.error(f"File Error: {e}")

    st.divider()
    st.header("📂 Chat History")
    
    if st.button("➕ Start New Chat", use_container_width=True):
        temp_name = f"Session {datetime.now().strftime('%H:%M:%S')}"
        st.session_state.all_sessions[temp_name] = []
        st.session_state.current_chat = temp_name
        st.rerun()

    st.write("") # Spacer

    # --- THE DELETE & SELECT LOGIC ---
    for chat_title in list(st.session_state.all_sessions.keys()):
        # We use columns to put the Delete [X] right next to the Name
        col1, col2 = st.columns([0.8, 0.2])
        
        with col1:
            is_active = "primary" if chat_title == st.session_state.current_chat else "secondary"
            if st.button(chat_title, use_container_width=True, type=is_active, key=f"btn_{chat_title}"):
                st.session_state.current_chat = chat_title
                st.rerun()
        
        with col2:
            if st.button("X", key=f"del_{chat_title}", help="Delete this chat"):
                del st.session_state.all_sessions[chat_title]
                if st.session_state.current_chat == chat_title:
                    remaining = list(st.session_state.all_sessions.keys())
                    st.session_state.current_chat = remaining[0] if remaining else "New Chat Session"
                    if not remaining: st.session_state.all_sessions["New Chat Session"] = []
                st.rerun()

# --- 4. API Engine Setup ---
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
except Exception:
    st.error("🔑 Please add 'GROQ_API_KEY' to your Streamlit Secrets!")
    st.stop()

# --- 5. Main Chat Interface ---
st.title(f"🚀 {st.session_state.current_chat}")
messages = st.session_state.all_sessions.get(st.session_state.current_chat, [])

# Always display the history first
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. Chat Input & Smart Renaming Logic ---
if prompt := st.chat_input("How can I help you today?"):
    # 1. Save and display user message
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate AI Response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # System instructions to keep it in 2026
        sys_info = f"System: Current date is {datetime.now().strftime('%B %d, %Y')}. The year is 2026."
        
        # Prepare context if a file was uploaded
        final_prompt = prompt
        if context_text:
            final_prompt = f"FILE CONTEXT:\n{context_text[:7000]}\n\nUSER QUESTION: {prompt}"

        # Stream the response from Groq
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_info}] + 
                     [m for m in messages[:-1]] + 
                     [{"role": "user", "content": final_prompt}],
            stream=True,
        )

        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
        messages.append({"role": "assistant", "content": full_response})

    # --- SMART RENAMING (The "Magic" part) ---
    # If this is the first exchange, ask AI to summarize a title
    if len(messages) <= 2 and st.session_state.current_chat.startswith("Session "):
        try:
            naming_chat = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{
                    "role": "system", 
                    "content": "Summarize the user's topic into a 2-3 word title. Return ONLY the title words."
                }, {"role": "user", "content": prompt}]
            )
            ai_title = naming_chat.choices[0].message.content.strip().replace(".", "")
            
            # Swap the session name in the dictionary
            st.session_state.all_sessions[ai_title] = st.session_state.all_sessions.pop(st.session_state.current_chat)
            st.session_state.current_chat = ai_title
        except:
            pass # Fallback to original name if naming fails

    st.rerun()
