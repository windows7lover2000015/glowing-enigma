import streamlit as st
from groq import Groq
from pypdf import PdfReader
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Adrito's AI 2026", page_icon="🚀", layout="wide")

# --- 2. Custom Styling (FIXED VERSION) ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    /* Styling for a cleaner chat look */
    .st-emotion-cache-16idsys p { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True) # Changed from unsafe_base64 to fix the error

st.title("🚀 Adrito's Cloud AI Assistant")
st.caption(f"Status: Online | Current Date: {datetime.now().strftime('%B %d, %Y')} | Engine: Groq Llama 3.1")

# --- 3. API & Secret Setup ---
# Make sure you have GROQ_API_KEY in your Streamlit Cloud Secrets!
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

if not GROQ_API_KEY:
    st.error("Missing API Key! Go to Settings > Secrets and add: GROQ_API_KEY = 'your_key'")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# --- 4. Sidebar: Document Handling ---
with st.sidebar:
    st.header("📁 Document Center")
    uploaded_file = st.file_uploader("Upload PDF, Python, or Text", type=["pdf", "txt", "py", "md"])
    
    context_text = ""
    if uploaded_file:
        with st.spinner("Reading document..."):
            try:
                if uploaded_file.type == "application/pdf":
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            context_text += text + "\n"
                else:
                    context_text = uploaded_file.read().decode("utf-8")
                st.success(f"Context loaded: {uploaded_file.name}")
            except Exception as e:
                st.error(f"Could not read file: {e}")
    
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- 5. Chat History Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. The 2026 AI Logic ---
if prompt := st.chat_input("Ask me anything..."):
    # Show user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare Context (Current Date + File Content)
    current_date = datetime.now().strftime("%B %d, %Y")
    system_instruction = (
        f"You are a helpful AI assistant. Today's date is {current_date}. "
        "The current year is 2026. If the user provides document context, "
        "use it to answer their questions accurately."
    )
    
    # If a file is uploaded, add it to the user's prompt as context
    if context_text:
        # Limit context to ~12,000 characters to prevent crashing the AI's "brain"
        user_payload = f"DOCUMENT CONTEXT:\n{context_text[:12000]}\n\nUSER QUESTION: {prompt}"
    else:
        user_payload = prompt

    # AI Response Generation
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Build message history with the system instruction at the top
        messages_payload = [{"role": "system", "content": system_instruction}]
        
        # Add past history (excluding the very last prompt we just handled)
        for m in st.session_state.messages[:-1]:
            messages_payload.append({"role": m["role"], "content": m["content"]})
            
        # Add the current prompt (with file context if it exists)
        messages_payload.append({"role": "user", "content": user_payload})

        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages_payload,
                stream=True,
            )

            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Groq API Error: {str(e)}")
