import streamlit as st
from groq import Groq
from PIL import Image
from datetime import datetime
import PyPDF2
from docx import Document
import io
import requests
import time

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Adrito's AI Chatbot", page_icon="🌐", layout="wide")

# --- 2. SESSION STATE ---
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"New Chat Session": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "New Chat Session"
# Track if the welcome popup has already been shown to this visitor
if "popup_shown" not in st.session_state:
    st.session_state.popup_shown = False

# --- 3. FILE PARSERS ---
def extract_text(file):
    try:
        fname = file.name.lower()
        if fname.endswith(('.txt', '.py', '.md')):
            return file.read().decode("utf-8")
        elif fname.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
        elif fname.endswith('.docx'):
            doc = Document(io.BytesIO(file.read()))
            return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        st.sidebar.error(f"File Error: {e}")
    return ""

# --- 4. SIDEBAR ---
MODEL_MAP = {
    "🔥 Pro (GPT-OSS 120B)": "openai/gpt-oss-120b",
    "⚖️ Balanced (Llama 3.3 70B)": "llama-3.3-70b-versatile",
    "⚡ Lightning (GPT-OSS 20B)": "openai/gpt-oss-20b",
    "🎨 Nano Banana (Image Gen)": "NANO_MODE"
}

with st.sidebar:
    st.title("⚙️ AI Control")
    selected_label = st.selectbox("🧠 Choose Brain Power", options=list(MODEL_MAP.keys()), index=0, key="model_v8")
    model_choice = MODEL_MAP[selected_label]
    is_image_mode = (model_choice == "NANO_MODE")
    
    if not is_image_mode:
        web_search = st.toggle("Enable Live Web Search", value=True)
        uploaded_file = st.file_uploader("📎 Upload Context", type=['txt', 'py', 'md', 'pdf', 'docx'])
    
    st.divider()
    
    st.header("📂 Chats")
    
    if st.button("➕ Start New Chat", use_container_width=True):
        new_id = f"Session {datetime.now().strftime('%H:%M:%S')}"
        st.session_state.all_sessions[new_id] = []
        st.session_state.current_chat = new_id
        st.rerun()

    if len(st.session_state.all_sessions) > 1:
        if st.button("🗑️ Delete All History", use_container_width=True, type="secondary", key="del_all_btn"):
            st.session_state.all_sessions = {"New Chat Session": []}
            st.session_state.current_chat = "New Chat Session"
            st.rerun()

    st.divider()
    
    for chat_title in list(st.session_state.all_sessions.keys()):
        cols = st.columns([0.8, 0.2])
        
        if cols[0].button(chat_title, key=f"btn_{chat_title}", use_container_width=True, 
                          type="primary" if chat_title == st.session_state.current_chat else "secondary"):
            st.session_state.current_chat = chat_title
            st.rerun()
        
        if len(st.session_state.all_sessions) > 1:
            if cols[1].button("❌", key=f"del_single_{chat_title}"):
                del st.session_state.all_sessions[chat_title]
                if st.session_state.current_chat == chat_title:
                    st.session_state.current_chat = list(st.session_state.all_sessions.keys())[0]
                st.rerun()

# --- 5. WELCOME POPUP LOGIC ---
# Using Streamlit's native dialog engine to create a dismissible box overlay
@st.dialog("👋 Welcome!")
def show_welcome_box():
    st.markdown("""
    ### Hello! This is Adrito's AI Chatbot.
    This chatbot is made by **Adrito Roy** and is open source. 
    
    🌐 **GitHub Repository:**
    [glowing-enigma](https://github.com/windows7lover2000015/glowing-enigma/tree/main)
    """)
    st.divider()
    if st.button("Ok!", use_container_width=True, type="primary"):
        st.session_state.popup_shown = True
        st.rerun()

# Trigger popup immediately on page load if it hasn't been acknowledged yet
if not st.session_state.popup_shown:
    show_welcome_box()

# --- 6. MAIN INTERFACE ---
st.title(f"🚀 {st.session_state.current_chat}")

try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Missing Groq API Key!")
    st.stop()

# Display chat history
messages = st.session_state.all_sessions[st.session_state.current_chat]
for msg in messages:
    with st.chat_message(msg["role"]):
        if "image" in msg:
            st.image(msg["image"], caption="Nano Banana Output")
        else:
            st.markdown(msg["content"])

# --- 7. UNIFIED CHAT LOGIC ---
if prompt := st.chat_input("Message or Image Prompt..."):
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if is_image_mode:
            status_box = st.status("🍌 Nano Banana is peeling...")
            success = False
            for attempt in range(2):
                try:
                    seed = datetime.now().microsecond
                    image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1280&height=720&seed={seed}&model=flux&nologo=true"
                    
                    img_response = requests.get(image_url, timeout=60)
                    if img_response.status_code == 200:
                        image_bytes = io.BytesIO(img_response.content)
                        img_obj = Image.open(image_bytes)
                        status_box.update(label="✅ Image Peeled!", state="complete")
                        st.image(img_obj)
                        messages.append({"role": "assistant", "image": img_obj})
                        success = True
                        break
                except:
                    if attempt == 0:
                        status_box.write("⏱️ Retrying...")
                        time.sleep(2)
            if not success:
                st.error("Server busy. Try again shortly.")
        else:
            placeholder = st.empty()
            full_res = ""
            context = ""
            if uploaded_file:
                file_text = extract_text(uploaded_file)
                context = f"\n\n[FILE DATA]\n{file_text}"
            
            try:
                stream = groq_client.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "system", "content": "You are a helpful AI assistant."}] + messages[:-1] + [{"role": "user", "content": prompt + context}],
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        placeholder.markdown(full_res + "▌")
                placeholder.markdown(full_res)
                messages.append({"role": "assistant", "content": full_res})
            except Exception as e:
                st.error(f"API Error: {e}")

    # SMART NAMING (Using Fast 20B)
    is_default = any(x in st.session_state.current_chat for x in ["Session", "New Chat"])
    if len(messages) >= 2 and is_default:
        try:
            name_gen = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "system", "content": "Return 2 words summarize topic. No quotes."}, {"role": "user", "content": prompt}]
            )
            smart_title = name_gen.choices[0].message.content.strip().replace('"', '')
            st.session_state.all_sessions[smart_title] = st.session_state.all_sessions.pop(st.session_state.current_chat)
            st.session_state.current_chat = smart_title
            st.rerun()
        except: pass
