import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
import json

# -------------------------
# CONFIG
# -------------------------
SPREADSHEET_NAME = "News Dashboard"
SHEET_NAME = "Headlines"

# -------------------------
# GOOGLE SHEETS FUNCTIONS
# -------------------------
def get_sheet():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    json_keyfile = st.secrets["service_account_json"]
    credentials = Credentials.from_service_account_info(json.loads(json_keyfile), scopes=SCOPES)
    client = gspread.authorize(credentials)
    sheet = client.open(SPREADSHEET_NAME)
    return sheet

def load_feeds_from_sheet():
    sheet = get_sheet()
    feeds_sheet = sheet.worksheet("Feeds")
    rows = feeds_sheet.get_all_values()[1:]  # Skip header
    return {row[0]: row[1] for row in rows if row[1].startswith("http")}

# -------------------------
# BOOLEAN FILTERING
# -------------------------
def parse_boolean_query(query, text):
    try:
        text = text.lower()
        query = query.lower()
        terms = re.split(r"\s+(AND|OR|NOT)\s+", query)
        expression = ""
        for t in terms:
            if t in ["and", "or", "not"]:
                expression += f" {t} "
            else:
                expression += f"('{t.strip()}' in text)"
        return eval(expression)
    except Exception:
        return False

# -------------------------
# SHEET PUSH
# -------------------------
def push_to_sheet(rows):
    try:
        sheet = get_sheet().worksheet(SHEET_NAME)
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
        st.success(f"{len(rows)} results pushed to Google Sheet.")
    except Exception as e:
        st.error(f"Sheet update failed: {e}")

# -------------------------
# APP SETUP
# -------------------------
DEFAULT_QUERY = (
    '"Russia" OR "Russians" OR "Russian" OR "wagner" OR "Africa Corps" OR '
    '"Russian instructors" OR "Russian military specialists"'
)

st.set_page_config(page_title="News Monitor Dashboard", layout="wide")
st.title("🌍 News Monitor Dashboard")

query = st.text_area("Boolean Query", value=DEFAULT_QUERY, height=100)

# Load RSS feeds
RSS_FEEDS = load_feeds_from_sheet()

# -------------------------
# MAIN EXECUTION
# -------------------------
if st.button("🔁 Run Search"):
    results = []
    with st.spinner("Loading feeds and applying filter..."):
        for name, url in RSS_FEEDS.items():
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "")
                combined_text = f"{title} {summary}"
                if parse_boolean_query(query, combined_text):
                    results.append([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        title,
                        summary,
                        link,
                        name,
                        "",  # Country (optional)
                        query
                    ])

    if results:
        df = pd.DataFrame(results, columns=["Timestamp", "Title", "Summary", "Url", "Source", "Country", "Matched Keywords"])
        st.dataframe(df)
        push_to_sheet(results)
    else:
        st.warning("No matching results found.")

