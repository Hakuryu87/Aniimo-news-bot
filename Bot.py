import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

QUERY = '"ANIIMO Italia"'
SEEN_FILE = "published.json"


def get_news():
    url = (
        "https://news.google.com/rss/search?q="
        + quote(QUERY)
        + "&hl=it&gl=IT&ceid=IT:it"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    articles = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        description = item.findtext("description", "")

        # ANIIMO deve comparire esplicitamente
        text = (title + " " + description).lower()

        if "aniimo" not in text:
            continue

        if not title or not link:
            continue

        articles.append({
            "title": title,
            "link": link
        })

    return articles


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)


def get_group_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    updates = response.json().get("result", [])

    for update in reversed(updates):
        message = update.get("message", {})
        chat = message.get("chat", {})

        if chat.get("type") in ("group", "supergroup"):
            return chat.get("id")

    return None


def send_message(chat_id, article):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    message = (
        "🏳️‍🌈 ANIIMO NEWS\n\n"
        f"📰 {article['title']}\n\n"
        f"🔗 {article['link']}"
    )

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False
        },
        timeout=30
    )

    response.raise_for_status()


def main():
    print("Controllo news ANIIMO...")

    chat_id = get_group_id()

    if not chat_id:
        print("Nessun gruppo trovato.")
        print("Scrivi /news nel gruppo ANIIMO.")
        return

    print(f"Gruppo trovato: {chat_id}")

    seen = load_seen()
    articles = get_news()

    new_articles = []

    for article in articles:
        if article["link"] not in seen:
            new_articles.append(article)

    if not new_articles:
        print("Nessuna nuova notizia ANIIMO.")
        return

    # Pubblica massimo 3 nuove notizie per controllo
    for article in new_articles[:3]:
        send_message(chat_id, article)
        seen.add(article["link"])

    save_seen(seen)

    print(f"Pubblicate {min(len(new_articles), 3)} nuove notizie ANIIMO.")


if __name__ == "__main__":
    main()
