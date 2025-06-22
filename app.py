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

RSS_FEEDS = {
    # 🌍 Major International Media
    "BBC Africa": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    "Al Jazeera (Global)": "https://www.aljazeera.com/xml/rss/all.xml",
    "Al Jazeera Africa": "https://www.aljazeera.com/xml/rss/all.xml",  # Filter in-app
    "Reuters Africa": "https://www.reutersagency.com/feed/?best-topics=africa",
    "France24 Africa": "https://www.france24.com/en/africa/rss",
    "Le Monde Afrique": "https://www.lemonde.fr/afrique/rss_full.xml",
    "NYT Africa": "https://rss.nytimes.com/services/xml/rss/nyt/Africa.xml",
    "The Guardian (Global Dev)": "https://www.theguardian.com/global-development/rss",
    "DW Africa": "https://rss.dw.com/rdf/rss-en-all",
    "VOA News Africa": "https://www.voanews.com/api/zp$ovegu$opi",
    "RFI Afrique (FR)": "https://www.rfi.fr/fr/afrique/rss",
    "RFI English": "https://www.rfi.fr/en/rss",
    "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
    "AP World": "https://apnews.com/rss/apf-intlnews",
    "Bloomberg Africa": "https://www.bloomberg.com/feeds/politics.rss",  # Filtered
    "Forbidden Stories": "https://forbiddenstories.org/feed/",
    
    # 🌍 Africa-Wide / Aggregators
    "AllAfrica Africa Top News": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
    "AllAfrica West Africa": "https://allafrica.com/tools/headlines/rdf/westafrica/headlines.rdf",
    "AllAfrica East Africa": "https://allafrica.com/tools/headlines/rdf/eastafrica/headlines.rdf",
    "AllAfrica Central Africa": "https://allafrica.com/tools/headlines/rdf/centralafrica/headlines.rdf",
    "AllAfrica Southern Africa": "https://allafrica.com/tools/headlines/rdf/southernafrica/headlines.rdf",
    "AllAfrica North Africa": "https://allafrica.com/tools/headlines/rdf/northafrica/headlines.rdf",

    # 🇳🇬 Nigeria
    "Punch Nigeria": "https://punchng.com/feed/",
    "The Guardian Nigeria": "https://guardian.ng/feed/",
    "Vanguard Nigeria": "https://www.vanguardngr.com/feed/",
    "Daily Trust": "https://dailytrust.com/feed/",
    "Premium Times": "https://www.premiumtimesng.com/feed",

    # 🇰🇪 Kenya
    "Daily Nation": "https://nation.africa/kenya/rss",
    "The Standard (Kenya)": "https://www.standardmedia.co.ke/rss/headlines.php",
    "Kenya News Agency": "https://www.kenyanews.go.ke/feed/",

    # 🇿🇦 South Africa
    "News24 South Africa": "https://www.news24.com/rss",
    "Mail & Guardian": "https://mg.co.za/feed/",
    "Daily Maverick": "https://www.dailymaverick.co.za/feed/",

    # 🇺🇬 Uganda
    "Daily Monitor Uganda": "https://www.monitor.co.ug/rss",

    # 🇬🇭 Ghana
    "GhanaWeb": "https://www.ghanaweb.com/GhanaHomePage/NewsArchive/rss.xml",
    "Joy Online": "https://www.myjoyonline.com/feed/",

    # 🇸🇩 Sudan
    "Sudan Tribune": "https://www.sudantribune.com/spip.php?page=backend",
    
    # 🇪🇹 Ethiopia
    "Addis Standard": "https://addisstandard.com/feed/",
    "The Reporter Ethiopia": "https://www.thereporterethiopia.com/rss.xml",

    # 🇲🇱 Mali
    "Maliweb": "https://www.maliweb.net/feed",

    # 🇨🇩 DR Congo
    "Actualite.cd": "https://actualite.cd/rss",

    # 🇪🇬 Egypt
    "Ahram Online": "https://english.ahram.org.eg/UI/Front/SearchRSS.aspx?Text=&Type=All&DateFrom=&DateTo=",

    # 🇲🇦 Morocco
    "Morocco World News": "https://www.moroccoworldnews.com/feed",

    # 🇹🇳 Tunisia
    "Tunisia News (Tap Info)": "https://www.tap.info.tn/en/rss",

    # 🇱🇾 Libya
    "Libya Observer": "https://www.libyaobserver.ly/rss.xml",

    # 🇸🇳 Senegal
    "Dakaractu": "https://www.dakaractu.com/xml/atom.xml",

    # 🇨🇮 Côte d’Ivoire
    "FratMat (CI)": "https://www.fratmat.info/rss.xml"
}

DEFAULT_QUERY = (
    '"Russia" OR "Russians" OR "Russian" OR "wagner" OR "Africa Corps" OR "Russian instructors" OR "Russian military specialists"'
)

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
# GOOGLE SHEETS SETUP
# -------------------------
def get_sheet():
    SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
    ]
    json_keyfile = st.secrets["service_account_json"]
    credentials = Credentials.from_service_account_info(json.loads(json_keyfile), scopes=SCOPES)
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
                        "",  # Country placeholder
                        query
                    ])

    if results:
        df = pd.DataFrame(results, columns=["Timestamp", "Title", "Summary", "Url", "Source", "Country", "Matched Keywords"])
        st.dataframe(df)
        push_to_sheet(results)
    else:
        st.warning("No matching results found.")
