import os
import json
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

CHAT_ID = "-1004412503318"

SEEN_FILE = "published.json"

QUERIES = [
    '"ANIIMO Italia"',
    '"ANIIMO"',
    '"ANIIMO" news',
    '"ANIIMO Italia" news',
]


def get_news():
    articles = {}

    for query in QUERIES:
        print(f"Ricerca: {query}")

        url = (
            "https://news.google.com/rss/search?q="
            + quote(query)
            + "&hl=it&gl=IT&ceid=IT:it"
        )

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.text)

            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                description = item.findtext("description", "").strip()

                if not title or not link:
                    continue

                # ANIIMO deve comparire nel titolo
                if "aniimo" not in title.lower():
                    continue

                articles[link] = {
                    "title": title,
                    "link": link,
                    "description": description
                }

        except Exception as e:
            print(f"Errore nella ricerca {query}: {e}")

    return list(articles.values())


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(
            list(seen),
            f,
            ensure_ascii=False,
            indent=2
        )


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        },
        timeout=30
    )

    response.raise_for_status()


def main():
    print("===================================")
    print("       ANIIMO NEWS - CONTROLLO")
    print("===================================")

    articles = get_news()

    print(f"Articoli trovati: {len(articles)}")

    if not articles:
        print("Nessun articolo ANIIMO trovato.")
        return

    seen = load_seen()

    new_articles = [
        article
        for article in articles
        if article["link"] not in seen
    ]

    print(f"Nuovi articoli: {len(new_articles)}")

    if not new_articles:
        print("Nessuna nuova notizia ANIIMO.")
        return

    for article in new_articles[:3]:
        message = (
            "🏳️‍🌈 ANIIMO NEWS\n\n"
            f"📰 {article['title']}\n\n"
            f"🔗 {article['link']}"
        )

        send_message(message)

        seen.add(article["link"])

        print(f"Pubblicata: {article['title']}")

    save_seen(seen)

    print(
        f"Pubblicate {min(len(new_articles), 3)} nuove notizie."
    )


if __name__ == "__main__":
    main()
