import streamlit as st
from groq import Groq
from PIL import Image
from datetime import datetime
import PyPDF2
from docx import Document
import io
import requests
import time
import base64
import uuid
from google.cloud import firestore
from google.oauth2 import service_account

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Adrito's AI Chatbot", page_icon="logo.png", layout="wide")

# --- 1b. BACKGROUND IMAGE ---
def set_background(image_path):
    try:
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{img_data}");
                background-size: 300px;
                background-position: center center;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-color: #000000;
            }}

            /* Keep chat bubbles readable over the background */
            [data-testid="stChatMessage"] {{
                background-color: rgba(20, 20, 20, 0.85);
                border-radius: 12px;
                padding: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}

            /* Sidebar stays solid dark so controls are legible */
            [data-testid="stSidebar"] {{
                background-color: rgba(10, 10, 10, 0.97);
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        pass

set_background("background.png")

# --- 2. CLOUD DATABASE CONNECTION ---
@st.cache_resource
def get_db():
    cred_dict = dict(st.secrets["firebase"])
    if "\\n" in cred_dict["private_key"]:
        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
    creds = service_account.Credentials.from_service_account_info(cred_dict)
    return firestore.Client(credentials=creds, project=cred_dict["project_id"])

try:
    db = get_db()
except Exception as e:
    st.error(f"Cloud Database Connection Failed: {e}")
    st.stop()

# --- 3. SESSION STATE & ISOLATED CLOUD SYNC ---
# Generate a unique browser session ID if not set
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_{uuid.uuid4().hex[:8]}"

# Sidebar profile switcher lets returning users access their history across devices
with st.sidebar:
    custom_user_id = st.text_input("👤 Your Profile ID", value=st.session_state.user_id, help="Enter a custom handle to access your chats on another device.")
    if custom_user_id != st.session_state.user_id:
        st.session_state.user_id = custom_user_id
        if "all_sessions" in st.session_state:
            del st.session_state["all_sessions"]
        st.rerun()

USER_ID = st.session_state.user_id

if "all_sessions" not in st.session_state:
    with st.spinner("☁️ Syncing history with Cloud Database..."):
        try:
            doc_ref = db.collection("users").document(USER_ID)
            doc = doc_ref.get()
            if doc.exists:
                st.session_state.all_sessions = doc.to_dict().get("chats", {"New Chat Session": []})
            else:
                st.session_state.all_sessions = {"New Chat Session": []}
                doc_ref.set({"chats": st.session_state.all_sessions})
        except Exception as e:
            st.session_state.all_sessions = {"New Chat Session": []}

if "current_chat" not in st.session_state or st.session_state.current_chat not in st.session_state.all_sessions:
    st.session_state.current_chat = list(st.session_state.all_sessions.keys())[0]

if "popup_shown" not in st.session_state:
    st.session_state.popup_shown = False

def save_to_cloud():
    try:
        db.collection("users").document(USER_ID).set({"chats": st.session_state.all_sessions})
    except Exception as e:
        st.sidebar.error(f"Cloud Save Failed: {e}")

# --- 4. FILE PARSERS ---
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

# --- 5. SIDEBAR CONTROLS ---
MODEL_MAP = {
    "🔥 Pro (GPT-OSS 120B)": "openai/gpt-oss-120b",
    "⚖️ Balanced (Llama 3.1 70B)": "llama-3.1-70b-versatile",
    "⚡ Lightning (GPT-OSS 20B)": "openai/gpt-oss-20b",
    "🎨 Nano Banana (Image Gen)": "NANO_MODE"
}

LANGUAGES = {
    "English 🇬🇧": "English",
    "Bengali 🇧🇩": "Bengali",
    "Hindi 🇮🇳": "Hindi",
    "Spanish 🇪🇸": "Spanish",
    "French 🇫🇷": "French",
    "German 🇩🇪": "German",
    "Mandarin Chinese 🇨🇳": "Mandarin Chinese",
    "Japanese 🇯🇵": "Japanese",
    "Korean 🇰🇷": "Korean",
    "Arabic 🇸🇦": "Arabic",
    "Russian 🇷🇺": "Russian",
    "Portuguese 🇵🇹": "Portuguese",
    "Italian 🇮🇹": "Italian",
    "Urdu 🇵🇰": "Urdu",
    "Tamil 🇮🇳": "Tamil"
}

with st.sidebar:
    try:
        st.image("logo.png", width=120)
    except Exception:
        pass
    st.title("⚙️ AI Control")
    
    selected_label = st.selectbox("🧠 Choose Brain Power", options=list(MODEL_MAP.keys()), index=0, key="model_v10")
    model_choice = MODEL_MAP[selected_label]
    is_image_mode = (model_choice == "NANO_MODE")
    
    selected_lang = st.selectbox("🌐 Select AI Output Language", options=list(LANGUAGES.keys()), index=0, key="lang_selector")
    target_language = LANGUAGES[selected_lang]
    
    uploaded_file = None
    if not is_image_mode:
        web_search = st.toggle("Enable Live Web Search", value=True)
        uploaded_file = st.file_uploader("📎 Upload Context", type=['txt', 'py', 'md', 'pdf', 'docx'])
    else:
        st.info("🎨 Nano Banana is active. Prompt for an image below.")
    
    st.divider()
    st.header("📂 Chats")
    
    if st.button("➕ Start New Chat", use_container_width=True):
        new_id = f"Session {datetime.now().strftime('%H:%M:%S')}"
        st.session_state.all_sessions[new_id] = []
        st.session_state.current_chat = new_id
        save_to_cloud()
        st.rerun()

    if len(st.session_state.all_sessions) > 1:
        if st.button("🗑️ Delete All History", use_container_width=True, type="secondary", key="del_all_btn"):
            st.session_state.all_sessions = {"New Chat Session": []}
            st.session_state.current_chat = "New Chat Session"
            save_to_cloud()
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
                save_to_cloud()
                st.rerun()

    st.divider()
    # --- ADMIN DATABASE RESET ---
    with st.expander("⚠️ Admin Database Reset"):
        reset_pass = st.text_input("Enter Admin Password", type="password", key="admin_pass_key")
        
        # Pulls password securely from Streamlit Secrets
        if reset_pass and reset_pass == st.secrets.get("ADMIN_PASSWORD"):
            if st.button("🔥 PURGE ALL CLOUD CHATS", type="primary", use_container_width=True):
                try:
                    docs = db.collection("users").stream()
                    for doc in docs:
                        doc.reference.delete()
                    
                    st.session_state.all_sessions = {"New Chat Session": []}
                    st.session_state.current_chat = "New Chat Session"
                    st.success("Database completely cleared!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Reset failed: {e}")

# --- 6. WELCOME POPUP LOGIC ---
@st.dialog("👋 Welcome!")
def show_welcome_box():
    st.markdown("""
    ### Hello! This is Adrito's AI Chatbot.
    This chatbot is made by **Adrito Roy** and is open source. 
    
    This chatbot has cloud storage and the chats sync with the cloud to your device.
    
    🌐 **GitHub Repository:**
    [glowing-enigma](https://github.com/windows7lover2000015/glowing-enigma/tree/main)
    """)
    st.divider()
    if st.button("Ok!", use_container_width=True, type="primary"):
        st.session_state.popup_shown = True
        st.rerun()

if not st.session_state.popup_shown:
    show_welcome_box()

# --- 7. MAIN INTERFACE ---
st.title(f"🚀 {st.session_state.current_chat}")

try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
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

# --- 8. UNIFIED CHAT LOGIC ---
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
                        status_box.update(label="✅ Image Peeled!", state="complete")
                        st.image(image_url)
                        messages.append({"role": "assistant", "image": image_url})
                        success = True
                        save_to_cloud()
                        break
                except Exception:
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
                if file_text:
                    context = f"\n\n[FILE DATA]\n{file_text}"
            
            system_instruction = f"You are a helpful AI assistant. IMPORTANT: You must respond entirely in the {target_language} language, regardless of the language the user writes in."
            
            # Filter history to only text payloads for Groq API
            api_history = [{"role": m["role"], "content": m["content"]} for m in messages[:-1] if "content" in m]
            
            try:
                stream = groq_client.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "system", "content": system_instruction}] + api_history + [{"role": "user", "content": prompt + context}],
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        placeholder.markdown(full_res + "▌")
                placeholder.markdown(full_res)
                messages.append({"role": "assistant", "content": full_res})
                save_to_cloud()
            except Exception as e:
                st.error(f"API Error ({model_choice}): {e}")
                st.info("💡 Tip: Try switching to '🔥 Pro' or '⚡ Lightning' in the sidebar if this model is rate-limited or offline.")

    # SMART NAMING (Using Fast 20B)
    is_default = any(x in st.session_state.current_chat for x in ["Session", "New Chat"])
    if len(messages) >= 2 and is_default:
        try:
            name_gen = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "system", "content": f"Return 2 words summarizing topic in the {target_language} language. No quotes."}, {"role": "user", "content": prompt}]
            )
            smart_title = name_gen.choices[0].message.content.strip().replace('"', '')
            st.session_state.all_sessions[smart_title] = st.session_state.all_sessions.pop(st.session_state.current_chat)
            st.session_state.current_chat = smart_title
            save_to_cloud()
            st.rerun()
        except Exception:
            pass
