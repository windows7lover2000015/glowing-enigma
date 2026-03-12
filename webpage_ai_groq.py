import streamlit as st
from groq import Groq
from pypdf import PdfReader
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Adrito's AI 2026", page_icon="🚀", layout="wide")

# --- 2. Custom Styling ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .st-emotion-cache-16idsys p { font-size: 1.1rem; }
    </style>
    """, unsafe_base64=True)

st.title("🚀 Adrito's Cloud AI Assistant")
st.caption(f"Status: Online | Year: {datetime.now().year} | Engine: Groq Llama 3.1")

# --- 3. API & Secret Setup ---
# This looks for "GROQ_API_KEY" in your Streamlit Cloud "Secrets" settings
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

if not GROQ_API_KEY:
    st.error("Please add your GROQ_API_KEY to Streamlit Secrets!")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# --- 4. Sidebar: Document Handling ---
with st.sidebar:
    st.header("📁 Document Center")
    uploaded_file = st.file_uploader("Upload PDF, Python, or Text", type=["pdf", "txt", "py", "md"])
    
    context_text = ""
    if uploaded_file:
        with st.spinner("Reading document..."):
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    context_text += page.extract_text() + "\n"
            else:
                context_text = uploaded_file.read().decode("utf-8")
        st.success(f"Context loaded: {uploaded_file.name}")
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- 5. Chat History & Logic ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. The 2026 Engine ---
if prompt := st.chat_input("Ask me anything..."):
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare Context (Current Date + File Content)
    current_date = datetime.now().strftime("%B %d, %Y")
    system_instruction = f"Today's date is {current_date}. You are a helpful AI assistant in the year 2026."
    
    if context_text:
        # We give the AI the first 15,000 characters of the file to stay within limits
        final_prompt = f"ATTACHED FILE CONTENT:\n{context_text[:15000]}\n\nUSER QUESTION: {prompt}"
    else:
        final_prompt = prompt

    # AI Response Generation
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Build the conversation payload
        messages_payload = [{"role": "system", "content": system_instruction}]
        for m in st.session_state.messages[:-1]:
            messages_payload.append({"role": m["role"], "content": m["content"]})
        messages_payload.append({"role": "user", "content": final_prompt})

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
            st.error(f"Error: {str(e)}")
