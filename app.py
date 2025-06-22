import streamlit as st
import feedparser
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -------------------------
# CONFIGURATION
# -------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_NAME = "News Monitor Dashboard"
SHEET_NAME = "Headlines"
JSON_KEYFILE = "service_account.json"  # Upload this as a secret or file

RSS_FEEDS = {
    "BBC Africa": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    "Reuters Africa": "https://www.reutersagency.com/feed/?best-topics=africa",
    "Le Monde Afrique": "https://www.lemonde.fr/afrique/rss_full.xml",
    "France24": "https://www.france24.com/en/africa/rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "NYT Africa": "https://rss.nytimes.com/services/xml/rss/nyt/Africa.xml",
    "Forbidden Stories": "https://forbiddenstories.org/feed/",
    # Add your AllAfrica country feeds here too
}

DEFAULT_QUERY = (
    "Russia OR Russians OR Russian OR wagner OR Africa Corps OR Russian instructors "
    "OR Russian military specialists OR Russie OR Russes OR Russe OR instructeurs russes "
    "OR groupe Wagner OR Corps africain OR spécialistes militaires russes OR روسيا OR روسيون "
    "OR روسي OR فاغنر OR فيلق أفريقيا OR مدربون روس OR خبراء عسكريون روس"
)

# -------------------------
# BOOLEAN FILTERING
# -------------------------
def parse_boolean_query(query, text):
    try:
        text = text.lower()
        query = query.lower()
        # Split phrases into words
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
# GOOGLE SHEETS SETUP
# -------------------------
def get_sheet():
    credentials = Credentials.from_service_account_file(JSON_KEYFILE, scopes=SCOPES)
    client = gspread.authorize(credentials)
    sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)
    return sheet

def push_to_sheet(rows):
    try:
        sheet = get_sheet()
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
        st.success(f"{len(rows)} results pushed to Google Sheet.")
    except Exception as e:
        st.error(f"Sheet update failed: {e}")

# -------------------------
# STREAMLIT UI
# -------------------------
st.set_page_config(page_title="News Monitor Dashboard", layout="wide")

st.title("🌍 News Monitor Dashboard")
query = st.text_area("Boolean Query", value=DEFAULT_QUERY, height=100)

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
                        "",  # Country is optional
                        query
                    ])

    if results:
        df = pd.DataFrame(results, columns=["Timestamp", "Title", "Summary", "Url", "Source", "Country", "Matched Keywords"])
        st.dataframe(df)
        push_to_sheet(results)
    else:
        st.warning("No matching results found.")
