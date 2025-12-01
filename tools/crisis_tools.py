CRISIS_RESOURCES = {
    "988": "988 Suicide & Crisis Lifeline (US/Canada) - Call or Text 988",
    "741741": "Crisis Text Line (US/Canada) - Text HOME to 741741",
    "LOCAL_INTL_RESOURCE": "Please search for your local emergency number or mental health hotline immediately."
}

def get_crisis_helpline(location="global"):
    if location == "global":
        return f"Immediate help: {CRISIS_RESOURCES['988']} or Text {CRISIS_RESOURCES['741741']}."
    return CRISIS_RESOURCES['LOCAL_INTL_RESOURCE']