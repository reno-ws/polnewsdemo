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


def fetch(query):
    """Holt die Treffer zu einer Suchanfrage von Google News Schweiz."""
    q = urllib.parse.quote(f"{query} when:{DAYS}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=de&gl=CH&ceid=CH:de"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    items = []
    for item in root.iter("item"):
        source = item.find("source")
        items.append({
            "title": item.findtext("title", ""),
            "link": item.findtext("link", ""),
            "date": parsedate_to_datetime(item.findtext("pubDate")),
            "source": source.text if source is not None else "",
            "source_url": source.get("url", "") if source is not None else "",
            "query": query,
        })
    return items


def is_priority(article):
    return any(p in article["source_url"] for p in PRIORITY)


# 2) Alle Suchanfragen ausführen
articles = {}
cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
for query in build_queries():
    try:
        for a in fetch(query):
            if a["date"] >= cutoff and a["title"] not in articles:
                articles[a["title"]] = a
    except Exception as e:
        print(f"Fehler bei Anfrage {query}: {e}")
    time.sleep(2)  # kurze Pause, damit Google uns nicht blockiert

# 3) Sortieren: Prioritätsquellen zuerst, dann neueste zuerst
result = sorted(articles.values(),
                key=lambda a: (not is_priority(a), -a["date"].timestamp()))
print(f"{len(result)} Artikel gefunden")

# 4) Webseite erstellen
tz = ZoneInfo("Europe/Zurich")
now = datetime.now(tz).strftime("%d.%m.%Y, %H:%M")
rows = ""
for a in result:
    star = "★ " if is_priority(a) else ""
    rows += f"""
    <div class="item{' prio' if star else ''}">
      {html.escape(a['link'])}{html.escape(a['title'])}</a>
      <div class="meta">{star}{html.escape(a['source'])} · {a['date'].astimezone(tz).strftime('%d.%m.%Y %H:%M')}</div>
    </div>"""
if not rows:
    rows = "<p>Keine neuen Artikel gefunden.</p>"

page = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Medienmonitoring {html.escape(config['organisation'])}</title>
<style>
 body {{ font-family: Arial, sans-serif; max-width: 860px; margin: 40px auto; padding: 0 16px; color: #222; }}
 h1 {{ font-size: 24px; margin-bottom: 4px; }}
 .sub {{ color: #666; margin-bottom: 24px; }}
 .item {{ padding: 12px 14px; border-bottom: 1px solid #eee; }}
 .item.prio {{ background: #f5f7ff; }}
 .item a {{ font-size: 16px; color: #1a3e8c; text-decoration: none; }}
 .item a:hover {{ text-decoration: underline; }}
 .meta {{ color: #777; font-size: 13px; margin-top: 4px; }}
</style></head><body>
<h1>Medienmonitoring {html.escape(config['organisation'])}</h1>
<div class="sub">{len(result)} Artikel der letzten {DAYS} Tag(e) · Stand {now} · ★ = Prioritätsquelle</div>
{rows}
</body></html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(page)
