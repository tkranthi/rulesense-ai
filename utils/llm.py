import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_rules(existing_rules: str, requirement: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")  # or your available model
    prompt = f"""
Here are existing profile update rules:

{existing_rules}

Requirement: {requirement}

Please propose:
1. Modified rules (with rationale)
2. New rules
3. Suggested Jira-style user stories
Format your answer as JSON with keys: modifications, additions, stories.
Respond ONLY with valid JSON, no explanation or extra text.
"""
    resp = model.generate_content(prompt)
    return resp.text
