from google import genai
from tools import audio_tools, memory_tools
import json
import uuid
import datetime
try:
    client = genai.Client()
except Exception as e:
    client = None
def get_analyst_prompt(transcript, biomarker_data):
    biomarker_str = json.dumps(biomarker_data, indent=2)
    return (
        "You are the Analyst Agent for a mental wellness companion. Your task is to objectively analyze the user's conversation and vocal data.\n"
        "Conversation Transcript:\n---\n" + transcript + "\n---\n"
        "Vocal Biomarkers:\n---\n" + biomarker_str + "\n---\n"
        "Based ONLY on the content and the vocal data, provide the following structured analysis in a single JSON block. Do not include any other text.\n"
        "1. mood_score: A score from 1 (Very Negative/Distressed) to 10 (Very Positive/Optimistic) reflecting the overall emotional tone.\n"
        "2. anxiety_score: A score from 1 (Very Calm) to 10 (High Distress/Anxiety). Pay special attention to 'jitter_local' and pitch variation.\n"
        "3. risk_level: An INTEGER score from 0 (No Risk) to 3 (Immediate Concern). Keep this conservative; the Guardian Agent will handle extremes.\n"
        "4. topics_discussed: A list of the top 3 main topics discussed (e.g., ['Work Stress', 'Weekend Plans', 'Hobby']).\n"
        "5. sentiment_summary: A brief, objective 2-sentence summary of the overall sentiment and vocal characteristics."
    )
def analyze_and_log_session(transcript, audio_file_path):
    if client is None:
        return None
    session_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    biomarkers = audio_tools.extract_vocal_biomarkers(audio_file_path)
    prompt = get_analyst_prompt(transcript, biomarkers)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        analysis = json.loads(response.text)
    except Exception as e:
        analysis = {}
    log_data = {
        'timestamp': timestamp,
        'session_id': session_id,
        'transcript_summary': analysis.get('sentiment_summary', transcript[:100] + "..."),
        'mood_score': analysis.get('mood_score', 0),
        'anxiety_score': analysis.get('anxiety_score', 0),
        'risk_level': analysis.get('risk_level', 0),
        'jitter_score': biomarkers.get('jitter_local', 0.0),
        'loudness_mean': biomarkers.get('loudness_mean', 0.0)
    }
    memory_tools.save_daily_log(log_data)
    update_user_profile_traits(transcript)
    return log_data
def update_user_profile_traits(transcript):
    current_profile = memory_tools.get_user_profile()
    profile_prompt = (
        f"Based on the latest conversation: '{transcript}'\n"
        f"And the user's current known profile: {json.dumps(current_profile, indent=2)}\n"
        "Identify ONE new hobby, interest, or personality trait that emerged or was reinforced.\n"
        "Output a single JSON object with two keys: 'key' and 'value'.\n"
        "Example: {\"key\": \"Coping Mechanism\", \"value\": \"Uses humor to deflect.\"}"
    )
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=profile_prompt,
            config={"response_mime_type": "application/json"}
        )
        new_trait = json.loads(response.text)
        memory_tools.update_user_profile(new_trait['key'], new_trait['value'])
    except Exception as e:
        pass
if __name__ == '__main__':
    import sys
    memory_tools.setup_database()
    test_audio_path = "data/temp_audio/user_input.wav"
    test_transcript = "I had a terrible day. My boss yelled at me for a mistake that wasn't mine, and now I'm thinking about just quitting my job and moving to the mountains to start a goat farm. I don't know what to do."
    if client:
        log_entry = analyze_and_log_session(test_transcript, test_audio_path)
        print(log_entry)
