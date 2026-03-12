import streamlit as st
from groq import Groq
from pypdf import PdfReader
from datetime import datetime

# --- 1. Setup ---
st.set_page_config(page_title="Adrito's AI 2026", page_icon="🚀", layout="wide")

# Corrected Styling
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# Initialize Session State (This is the AI's "Memory Bank")
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🚀 Adrito's Cloud AI Assistant")
st.caption(f"Status: Online | Date: {datetime.now().strftime('%B %d, %Y')}")

# --- 2. API Setup ---
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    st.error("Missing GROQ_API_KEY in Secrets!")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)

# --- 3. Sidebar (Document Center) ---
with st.sidebar:
    st.header("📁 Document Center")
    uploaded_file = st.file_uploader("Upload PDF, Python, or Text", type=["pdf", "txt", "py", "md"])
    
    context_text = ""
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    t = page.extract_text()
                    if t: context_text += t + "\n"
            else:
                context_text = uploaded_file.read().decode("utf-8")
            st.success("File context loaded!")
        except Exception as e:
            st.error(f"Error reading file: {e}")
    
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- 4. DISPLAY LOOP (This keeps the history visible) ---
# We loop through the memory bank and draw every message on the screen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. CHAT INPUT & PROCESSING ---
if prompt := st.chat_input("Ask me anything..."):
    # 1. Add User message to memory and show it immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Prepare context
    current_date = datetime.now().strftime("%B %d, %Y")
    system_msg = f"Today is {current_date}. Year is 2026. Use provided context if relevant."
    
    user_payload = prompt
    if context_text:
        user_payload = f"CONTEXT:\n{context_text[:10000]}\n\nUSER QUESTION: {prompt}"

    # 3. Get AI Response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Build the full conversation history for the AI
        api_messages = [{"role": "system", "content": system_msg}]
        for m in st.session_state.messages:
            api_messages.append({"role": m["role"], "content": m["content"]})
        
        # Swap the last message with the context-heavy version if needed
        api_messages[-1] = {"role": "user", "content": user_payload}

        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=api_messages,
                stream=True,
            )

            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
            # 4. Save AI response to memory and refresh to "lock" it in
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.rerun() # Forces the page to redraw everything from the display loop
            
        except Exception as e:
            st.error(f"Groq API Error: {e}")
