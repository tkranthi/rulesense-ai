import streamlit as st
from utils.llm import analyze_rules
import json
import pandas as pd
import os
import re
import io

def extract_json(text):
    """Extract the first JSON object from a string."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return None

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

def update_excel_with_ai(existing_df, ai_data):
    # Adjust columns as per your Excel structure
    df = existing_df.copy()
    # Apply modifications
    for mod in ai_data.get("modifications", []):
        mask = df['rule_id'] == mod.get('rule_id')
        df.loc[mask, 'rule'] = mod.get('suggested', df.loc[mask, 'rule'])
        df.loc[mask, 'rationale'] = mod.get('rationale', df.loc[mask, 'rationale'])
    # Add new rules
    for add in ai_data.get("additions", []):
        new_row = {
            'rule_id': add.get('rule_id', ''),
            'rule': add.get('rule', ''),
            'rationale': add.get('rationale', '')
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df

st.title("🧠 RuleSense.AI")

st.sidebar.header("Upload & Config")
uploaded = st.sidebar.file_uploader(
    "Upload existing rules (.txt/.md/.xlsx/.xls)", 
    type=["txt", "md", "xlsx", "xls"]
)
requirement = st.sidebar.text_input("Requirement (e.g., 'Add Aadhaar check on profile update')")

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
            json_str = extract_json(ai_out)
            if not json_str:
                st.error("Failed to find JSON in AI output. Raw response:")
                st.code(ai_out)
            else:
                try:
                    data = json.loads(json_str)
                    st.session_state["ai_data"] = data
                    # Store the DataFrame if Excel was uploaded
                    if uploaded.name.split('.')[-1].lower() in ["xlsx", "xls"]:
                        st.session_state["excel_df"] = pd.read_excel(uploaded)
                except Exception:
                    st.error("Failed to parse extracted JSON. Raw response:")
                    st.code(ai_out)
                else:
                    st.subheader("🔧 Modifications")
                    for m in data.get("modifications", []):
                        st.write(f"- **{m.get('rule_id', '')}**: {m.get('current', '')} → {m.get('suggested', '')} *({m.get('rationale', '')})*")
                    st.subheader("➕ Additions")
                    for a in data.get("additions", []):
                        st.write(f"- **{a.get('rule_id', '')}**: {a.get('rule', '')} *({a.get('rationale', '')})*")
                    st.subheader("📋 Jira Stories")
                    for s in data.get("stories", []):
                        st.write(f"- {s}")

# Show the download button for JSON
if "ai_data" in st.session_state:
    st.download_button(
        "Download Results",
        json.dumps(st.session_state["ai_data"], indent=2),
        "results.json"
    )

# Show the download button for updated Excel if Excel was uploaded
if "ai_data" in st.session_state and "excel_df" in st.session_state:
    updated_df = update_excel_with_ai(st.session_state["excel_df"], st.session_state["ai_data"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        updated_df.to_excel(writer, index=False)
    st.download_button(
        label="Download Updated Excel",
        data=output.getvalue(),
        file_name="updated_rules.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
