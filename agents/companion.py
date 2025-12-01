import datetime
import time
import os
from google import genai
from tools import stt_tts_tools, memory_tools
from agents.guardian import guardian_check
from agents.analyst import analyze_and_log_session

try:
    client = genai.Client()
except Exception:
    client = None

def get_companion_prompt(transcript: str, history: list, profile: dict) -> str:
    # Include language setting in the prompt so the model knows which language to use
    language = os.getenv('language', 'en')
    language_line = f"Language: {language}\n"
    history_str = "\n".join([f"- {h[1][:10]}: {h[3]}" for h in history])
    profile_str = "\n".join([f"- {k}: {v}" for k, v in profile.items()])
    return (
        language_line +
        "You are SerenAI, the user's empathetic best friend and daily wellness companion.\n"
        "Behavior Constraints:\n"
        "1. Tone: Be warm, casual, and supportive.\n"
        "2. Length: Keep responses concise (2-4 sentences max).\n"
        "3. Goal: Always end with an open-ended follow-up question.\n"
        "Context to Use:\n"
        "User's Recent History (Last 7 Days):\n" + (history_str or "No recent history available.") + "\n"
        "User's Personality Profile:\n" + (profile_str or "No personality profile established yet.") + "\n"
        "User just said: \"" + transcript + "\"\n"
        "Based on the context, give your empathetic response and thoughtful follow-up question."
    )

def run_session_loop():
    if client is None:
        print("Companion Agent Error: Gemini client not initialized.")
        return
    memory_tools.setup_database()
    stt_tts_tools.initialize_stt_model()
    print("Initiating SerenAI Daily Check-in")
    while True:
        # Wait for the user to start the next recording to avoid auto-restart
        try:
            start_cmd = input("Press Enter to start recording (or type 'quit' to exit):\n")
        except Exception:
            start_cmd = ""
        if isinstance(start_cmd, str) and start_cmd.strip().lower() in {"quit", "exit", "stop", "end"}:
            try:
                stt_tts_tools.speak_text("Okay, session ended. Take care — I'm here when you need me.")
            except Exception:
                pass
            break

        # Record one whole input (user presses Enter when finished). Set a generous max duration.
        audio_result = audio_tools.record_user_input(duration=600)
        # audio_result may be (filename, stop_session) or just filename
        if isinstance(audio_result, tuple):
            audio_path, stop_session = audio_result
        else:
            audio_path = audio_result
            stop_session = False

        # If user requested to end the entire session from within the recorder, say goodbye and break
        if stop_session:
            try:
                stt_tts_tools.speak_text("Got it. Session ended. Take care — I'm here when you need me.")
            except Exception:
                pass
            break

        if not audio_path:
            # No audio captured this round; prompt and continue
            try:
                stt_tts_tools.speak_text("I didn't catch that. When you're ready, you can try again.")
            except Exception:
                pass
            continue

        # Transcribe the single full-user-input recording
        try:
            transcript = stt_tts_tools.transcribe_audio(audio_path)
        except Exception as e:
            print(f"Transcription error: {e}")
            transcript = ""

        if not transcript:
            stt_tts_tools.speak_text("I didn't quite catch that. Could you try saying it again?")
            continue

        print(f"You: {transcript}")
        safety_alert = guardian_check(transcript)
        if safety_alert:
            print(safety_alert)
            stt_tts_tools.speak_text(safety_alert)
            break

        recent_history = memory_tools.get_recent_history(days=7)
        user_profile = memory_tools.get_user_profile()
        prompt = get_companion_prompt(transcript, recent_history, user_profile)
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            companion_response = response.text
        except Exception as e:
            companion_response = f"Oops, I had a little trouble. Tell me more. (Error: {e})"

        print(f"SerenAI: {companion_response}")
        stt_tts_tools.speak_text(companion_response)
        analyze_and_log_session(transcript, audio_path)

        # After the agent speaks, the user can reply — loop will record the next full input.
        if "goodbye" in transcript.lower() or "that's all for today" in transcript.lower():
            stt_tts_tools.speak_text("Got it. Thanks for checking in today. I'm here tomorrow if you need me!")
            break
        print("When you're ready to reply, speak and press Enter when finished...")

if __name__ == '__main__':
    print("Run the full application via main.py")
