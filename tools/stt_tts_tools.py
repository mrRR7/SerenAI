import whisper
from gtts import gTTS
from pydub import AudioSegment
import os
TTS_OUTPUT_PATH = "data/temp_audio/ai_response.mp3"
os.makedirs("data/temp_audio", exist_ok=True)
whisper_model = None
def initialize_stt_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
def transcribe_audio(audio_file_path: str) -> str:
    global whisper_model
    if whisper_model is None:
        initialize_stt_model()
    try:
        result = whisper_model.transcribe(audio_file_path, fp16=False)
        transcript = result["text"].strip()
        return transcript
    except Exception as e:
        return ""
def speak_text(text: str):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(TTS_OUTPUT_PATH)
        audio = AudioSegment.from_mp3(TTS_OUTPUT_PATH)
    except Exception as e:
        pass
if __name__ == '__main__':
    initialize_stt_model()
    test_text = "Hello there. I am SerenAI, your compassionate wellness companion. How are you feeling today?"
    speak_text(test_text)