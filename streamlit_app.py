# streamlit_app.py
import warnings
# Silence the mic-recorder ScriptRunContext warning early (if it appears)
warnings.filterwarnings("ignore", message="missing ScriptRunContext")

from pathlib import Path
import streamlit as st
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

import os
import base64
import datetime
import streamlit as st

# Try to import the mic recorder component; allow a graceful fallback if it's missing.
try:
    from streamlit_mic_recorder import mic_recorder
    MIC_AVAILABLE = True
except Exception:
    MIC_AVAILABLE = False

# Local project imports
from agents.companion import get_companion_prompt
from tools import stt_tts_tools, memory_tools

# GenAI client (explicit api_key is more reliable inside Streamlit)
try:
    from google import genai
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception:
    client = None

# Ensure required dirs & DB
Path("data/temp_audio").mkdir(parents=True, exist_ok=True)
try:
    memory_tools.setup_database()
except Exception:
    pass

# Streamlit page config
st.set_page_config(page_title="SerenAI", layout="wide")

# --- Session state defaults ---
if "messages" not in st.session_state:
    # messages: list[{"role":"user"|"assistant", "text": str, "ts": iso-str}]
    st.session_state["messages"] = []
if "processing" not in st.session_state:
    st.session_state["processing"] = False

# --- Helpers ---

def _now_ts():
    return datetime.datetime.now().isoformat(timespec="seconds")

def extract_response_text(response) -> str:
    """Robust extraction of plain text from a Gemini response object."""
    try:
        # preferred property
        text = getattr(response, "text", None)
        if text:
            return text
    except Exception:
        pass
    # fallback to nested structure
    try:
        return response.candidates[0].content.parts[0].text
    except Exception:
        try:
            # some versions expose a dict-like interface
            return response["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return str(response)

def generate_reply_from_model(user_text: str) -> str:
    """Build prompt and call model; returns the assistant text."""
    try:
        recent_history = memory_tools.get_recent_history(days=7)
    except Exception:
        recent_history = None
    try:
        user_profile = memory_tools.get_user_profile()
    except Exception:
        user_profile = None

    try:
        prompt = get_companion_prompt(user_text, recent_history, user_profile)
    except Exception:
        prompt = f"User said: {user_text}"

    if client is None:
        return "GenAI client not initialized. Check environment/config."

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return extract_response_text(response)
    except Exception as e:
        return f"Model generation error: {e}"

def safe_write_bytes_to_file(path: str, b: bytes) -> None:
    """Write raw bytes to disk (ensures parent exists)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        f.write(b)

def resolve_tts_path_from_speak(reply_text: str) -> str | None:
    """
    Call the project's speak_text helper and return the resulting file path.
    If speak_text returns None or raises, fall back to the default mp3 path.
    """
    # Call the project's speak function if available
    try:
        out = stt_tts_tools.speak_text(reply_text)
        # If the function returns a Path-like or str, use it if file exists later
        if out:
            return str(out)
    except Exception:
        # ignore and fallback
        pass
    # fallback default location many versions of the repo use
    fallback = "data/temp_audio/ai_response.mp3"
    return fallback

def play_tts_file(tts_path: str):
    """Read audio bytes and play in Streamlit using correct mime type."""
    p = Path(tts_path)
    if not p.exists() or p.stat().st_size == 0:
        st.warning("TTS audio file missing or empty; could not play audio.")
        return
    ext = p.suffix.lower()
    with open(p, "rb") as f:
        audio_bytes = f.read()
    if ext == ".wav":
        st.audio(audio_bytes, format="audio/wav")
    elif ext == ".mp3":
        st.audio(audio_bytes, format="audio/mp3")
    else:
        # try generic playback; browsers usually accept wav/mp3
        st.audio(audio_bytes)

def process_user_message_and_respond(user_text: str):
    """Append user -> call model -> append assistant -> call TTS/playback (best-effort)."""
    st.session_state["processing"] = True
    ts = _now_ts()
    st.session_state["messages"].append({"role": "user", "text": user_text, "ts": ts})

    # Model reply
    reply = generate_reply_from_model(user_text)
    st.session_state["messages"].append({"role": "assistant", "text": reply, "ts": _now_ts()})

    # TTS: call speak_text and play bytes (minimal-fix-A: read bytes)
    tts_path = resolve_tts_path_from_speak(reply)
    try:
        # If speak_text wrote to a bytes buffer rather than returning path, handle that in tool
        # But most implementations write a file; fallback handled in play_tts_file
        play_tts_file(tts_path)
    except Exception as e:
        st.warning(f"TTS playback failed: {e}")

    st.session_state["processing"] = False

# --- UI layout ---

col_left, col_right = st.columns([3, 1])

with col_left:
    st.header("SerenAI — Chat")

    # Conversation display
    st.subheader("Conversation")
    if not st.session_state["messages"]:
        st.info("No messages yet — speak or type to begin.")
    for msg in st.session_state["messages"]:
        role = msg.get("role", "assistant")
        text = msg.get("text", "")
        ts = msg.get("ts", "")
        if role == "user":
            st.markdown(f"**You ({ts}):**  \n{text}")
        else:
            st.markdown(f"**SerenAI ({ts}):**  \n{text}")

    st.markdown("---")

    # Microphone recorder - fixed key so widget persists across reruns
    st.subheader("Speak (record using the button)")

    if MIC_AVAILABLE:
        audio = mic_recorder(
            start_prompt="🎤 Record",
            stop_prompt="⏹ Stop",
            just_once=True,
            format="wav",
            key="mic_recorder",  # fixed key — do not vary this between runs
        )
    else:
        audio = None
        st.warning("Microphone recorder component not available. Install `streamlit-mic-recorder` to enable in-browser recording.")

    # Process recorded audio (if any)
    if audio:
        tmp_path = "data/temp_audio/mic_input.wav"
        try:
            # audio["bytes"] might be raw bytes or base64-encoded string depending on component version
            b = audio.get("bytes")
            if isinstance(b, str):
                # base64 string
                b = base64.b64decode(b)
            safe_write_bytes_to_file(tmp_path, b)
        except Exception as e:
            st.error(f"Failed saving recorded audio: {e}")
            tmp_path = None

        if tmp_path and Path(tmp_path).exists():
            st.audio(tmp_path, format="audio/wav")
            # Transcribe
            try:
                # initialize only if function exists; some implementations don't require init
                if hasattr(stt_tts_tools, "initialize_stt_model"):
                    try:
                        stt_tts_tools.initialize_stt_model()
                    except Exception:
                        # ignore initialization errors; transcription may still work
                        pass
                transcript = stt_tts_tools.transcribe_audio(tmp_path)
            except Exception as e:
                st.error(f"Transcription error: {e}")
                transcript = ""

            if transcript:
                st.success("Transcribed: " + transcript)
                process_user_message_and_respond(transcript)
            else:
                st.warning("No transcript returned. Try again or type a message below.")

    # Text input form (clear_on_submit avoids manual session_state edits)
    st.subheader("Or type your message")
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area("Message", key="input_text", height=100)
        submitted = st.form_submit_button("Send")

        if submitted:
            text_to_send = (user_input or "").strip()
            if not text_to_send:
                st.error("Type a message first.")
            else:
                process_user_message_and_respond(text_to_send)
                # form will clear automatically due to clear_on_submit=True

    # show processing status
    if st.session_state["processing"]:
        st.info("Processing...")

with col_right:
    st.header("Session")
    if client:
        st.success("Model client: OK")
    else:
        st.error("Model client: NOT INITIALIZED")

    if st.button("Clear chat"):
        st.session_state["messages"] = []
        st.experimental_rerun()

    if st.button("Show recent history (7 days)"):
        try:
            history = memory_tools.get_recent_history(days=7) or []
        except Exception:
            history = []
        if not history:
            st.write("No recent history found.")
        else:
            for row in history[:10]:
                ts = row[1] if len(row) > 1 else ""
                sid = row[2] if len(row) > 2 else ""
                summary = row[3] if len(row) > 3 else ""
                st.write(f"- {ts} — `{sid}`")
                if summary:
                    st.write(f"  • {summary}")

