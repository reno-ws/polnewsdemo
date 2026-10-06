# News-Monitor: sucht Schweizer News nach Erwähnungen einer Organisation
# und erstellt daraus die Webseite index.html.

import json
import html
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

# 1) Einstellungen aus config.json laden
with open("config.json", encoding="utf-8") as f:
    config = json.load(f)

DAYS = config["days_back"]
CONTEXT = config["context_word"]
PRIORITY = config["priority_sources"]
LINK_START = "<" + "a href=\""  # Beginn eines Links


def build_queries():
    """Erstellt die Suchanfragen für Google News (je max. 6 Begriffe pro Anfrage)."""
    queries = []
    direct = [f'"{t}"' for t in config["direct_terms"]]
    for i in range(0, len(direct), 6):
        queries.append(" OR ".join(direct[i:i + 6]))
    context = [f'"{t}"' for t in config["context_terms"]]
    for i in range(0, len(context), 6):
        queries.append(f'{CONTEXT} ({" OR ".join(context[i:i + 6])})')
    return queries


