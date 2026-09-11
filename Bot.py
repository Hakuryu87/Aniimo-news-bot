import os
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# ANIIMO è l'unico soggetto che ci interessa
QUERY = '"ANIIMO Italia"'

def get_news():
    url = (
        "https://news.google.com/rss/search?q="
        + quote(QUERY)
        + "&hl=it&gl=IT&ceid=IT:it"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    news = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")

        # Filtro fondamentale:
        # se ANIIMO non compare nel titolo, scartiamo.
        if "aniimo" not in title.lower():
            continue

        news.append({
            "title": title,
            "link": link,
            "date": pub_date
        })

    return news


def get_updates():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json().get("result", [])


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False
        },
        timeout=20
    ).raise_for_status()


# Per ora recuperiamo il gruppo dall'ultimo messaggio
# ricevuto dal bot.
updates = get_updates()

chat_id = None

for update in reversed(updates):
    message = update.get("message", {})
    chat = message.get("chat", {})

    if chat.get("type") in ("group", "supergroup"):
        chat_id = chat.get("id")
        break

if not chat_id:
    print("Nessun gruppo trovato. Scrivi /news nel gruppo.")
    exit(0)

news = get_news()

if not news:
    print("Nessuna nuova notizia ANIIMO.")
    exit(0)

# Per ora pubblichiamo al massimo le 3 più recenti.
for article in news[:3]:
    text = (
        "🏳️‍🌈 ANIIMO NEWS\n\n"
        f"📰 {article['title']}\n\n"
        f"🔗 {article['link']}"
    )

    send_message(chat_id, text)

print(f"Pubblicate {min(len(news), 3)} notizie.")
