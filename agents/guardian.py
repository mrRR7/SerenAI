import datetime
from tools import memory_tools, crisis_tools

IMMEDIATE_RISK_KEYWORDS = [
    "kill myself", "end it all", "not worth living",
    "take my life", "suicide", "self-harm", "harm myself"
]
MAX_DAYS_IN_LOW_MOOD = 3
MAX_AVG_ANXIETY_SCORE = 7.0

def check_immediate_risk(transcript: str) -> str | None:
    transcript_lower = transcript.lower()
    for keyword in IMMEDIATE_RISK_KEYWORDS:
        if keyword in transcript_lower:
            crisis_msg = (
                "IMMEDIATE DANGER ALERT:\n"
                "I am an AI and your safety is my top priority. Based on what you said, please reach out to a human professional right now.\n"
                f"HELPLINE: {crisis_tools.get_crisis_helpline()}\n"
                "Please talk to them immediately."
            )
            return crisis_msg
    return None

def check_long_term_trend_risk() -> str | None:
    logs = memory_tools.get_recent_history(days=7)
    if not logs:
        return None
    low_mood_days = 0
    total_anxiety = 0.0
    for log in logs:
        if log[4] < 4:
            low_mood_days += 1
        else:
            low_mood_days = 0
        total_anxiety += log[5]
    if low_mood_days >= MAX_DAYS_IN_LOW_MOOD:
        return (
            "INTERVENTION SUGGESTION:\n"
            "Mood has been low for several consecutive days. Consider scheduling a professional check-in or exploring coping resources."
        )
    avg_anxiety = total_anxiety / len(logs)
    if avg_anxiety >= MAX_AVG_ANXIETY_SCORE and len(logs) >= 5:
        return (
            "ANXIETY CHECK:\n"
            "Anxiety and vocal tremor metrics have been elevated this past week. Consider focusing the next session on relaxation techniques."
        )
    return None

def guardian_check(transcript: str) -> str | None:
    crisis_alert = check_immediate_risk(transcript)
    if crisis_alert:
        return crisis_alert
    trend_alert = check_long_term_trend_risk()
    if trend_alert:
        return trend_alert
    return None

if __name__ == '__main__':
    print("Testing Guardian Agent")
    memory_tools.setup_database()
    transcript_crisis = "I am so tired of everything. I might just take my life tonight."
    alert = guardian_check(transcript_crisis)
    print("Test 1 (Immediate Crisis):")
    print(alert)
    print("Test 2 (Trend Risk):")
    alert_trend = check_long_term_trend_risk()
    if alert_trend:
        print(alert_trend)
    else:
        print("No trend alert found")