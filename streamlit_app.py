import streamlit as st
from utils.llm import analyze_rules
import json
import pandas as pd

st.title("🧠 RuleSense.AI")

st.sidebar.header("Upload & Config")
uploaded = st.sidebar.file_uploader(
    "Upload existing rules (.txt/.md/.xlsx/.xls)", 
    type=["txt", "md", "xlsx", "xls"]
)
requirement = st.sidebar.text_input("Requirement (e.g., 'Add Aadhaar check on profile update')")

def read_rules_file(uploaded_file):
    if uploaded_file is None:
        return None
    file_type = uploaded_file.name.split('.')[-1].lower()
    if file_type in ["txt", "md"]:
        return uploaded_file.read().decode()
    elif file_type in ["xlsx", "xls"]:
        df = pd.read_excel(uploaded_file)
        # Combine all text from the DataFrame into a single string
        return "\n".join(df.astype(str).apply(lambda row: " | ".join(row), axis=1))
    else:
        return None

if st.sidebar.button("Analyze"):
    if not uploaded or not requirement:
        st.sidebar.error("Please upload rules and specify a requirement.")
    else:
        text_rules = read_rules_file(uploaded)
        if not text_rules:
            st.sidebar.error("Could not read the uploaded file. Please check the format.")
        else:
            with st.spinner("Analyzing rules using Gemini..."):
                ai_out = analyze_rules(text_rules, requirement)
            try:
                data = json.loads(ai_out)
            except Exception:
                st.error("Failed to parse AI output. Raw response:")
                st.code(ai_out)
            else:
                st.subheader("🔧 Modifications")
                for m in data.get("modifications", []):
                    st.write(f"- **{m['rule_id']}**: {m['current']} → {m['suggested']} *({m['rationale']})*")
                st.subheader("➕ Additions")
                for a in data.get("additions", []):
                    st.write(f"- **{a['rule_id']}**: {a['rule']} *({a['rationale']})*")
                st.subheader("📋 Jira Stories")
                for s in data.get("stories", []):
                    st.write(f"- {s}")
                if st.button("Export to JSON"):
                    st.download_button("Download Results", json.dumps(data, indent=2), "results.json")
