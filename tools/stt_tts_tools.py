# tools/stt_tts_tools.py

import os
from pathlib import Path

# Directory for temporary audio output
TTS_OUTPUT_DIR = Path("data/temp_audio")
TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TTS_OUTPUT_PATH = TTS_OUTPUT_DIR / "ai_response.mp3"


# ----------------------------------------------------------------
# TEXT TO SPEECH
# ----------------------------------------------------------------
def speak_text(text: str) -> str:
    """
    TTS that writes directly to a file. No PortAudio / device I/O.
    gTTS works fine on Streamlit Cloud.
    """
    from gtts import gTTS

    tts = gTTS(text=text, lang="en")
    tts.save(str(TTS_OUTPUT_PATH))
    return str(TTS_OUTPUT_PATH)


# ----------------------------------------------------------------
# SPEECH TO TEXT (FILE ONLY)
# works on cloud because it reads WAV file, not microphone.
# ----------------------------------------------------------------
def transcribe_audio(path: str) -> str:
    """
    Run STT on a WAV file only. Does not use mic hardware.
    Modify this to your actual STT implementation.
    """
    import whisper

    model = whisper.load_model("base")   # or "tiny", "small", etc.
    result = model.transcribe(path)
    text = result.get("text", "")
    return text.strip()


# ----------------------------------------------------------------
# Optional initialization hook (empty but keeps code compatible)
# ----------------------------------------------------------------
def initialize_stt_model():
    """
    No hardware to initialize in cloud deployments.
    This function stays for API compatibility.
    """
    pass
