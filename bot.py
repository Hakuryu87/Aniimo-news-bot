import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlparse
from html import unescape
from html.parser import HTMLParser
from datetime import datetime, timezone


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

CHAT_ID = "-1004412503318"

SEEN_FILE = "published.json"

QUERIES = [
    '"ANIIMO Italia"',
    '"ANIIMO"',
    '"ANIIMO" news',
    '"ANIIMO Italia" news',
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script = False
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.in_script = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.in_script = False

    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            text = data.strip()
            if text:
                self.text.append(text)

    def get_text(self):
        return " ".join(self.text)


def clean_text(text):
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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
            response = requests.get(
                url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 ANIIMO-News-Bot"
                }
            )

            response.raise_for_status()

            root = ET.fromstring(response.text)

            for item in root.findall(".//item"):

                title = clean_text(
                    item.findtext("title", "")
                )

                link = item.findtext("link", "").strip()

                description = clean_text(
                    item.findtext("description", "")
                )

                pub_date = item.findtext(
                    "pubDate",
                    ""
                ).strip()

                if not title or not link:
                    continue

                # ANIIMO deve comparire nel titolo.
                if "aniimo" not in title.lower():
                    continue

                articles[link] = {
                    "title": title,
                    "link": link,
                    "description": description,
                    "pub_date": pub_date
                }

        except Exception as e:
            print(f"Errore nella ricerca {query}: {e}")

    return list(articles.values())


def get_page_text(url):

    try:

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/139 Safari/537.36"
                )
            }
        )

        response.raise_for_status()

        parser = TextExtractor()
        parser.feed(response.text)

        text = parser.get_text()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text[:100000]

    except Exception as e:

        print(
            f"Impossibile leggere articolo "
            f"{url}: {e}"
        )

        return ""


def is_relevant(article):

    title = article["title"].lower()
    description = article["description"].lower()

    # Il titolo deve contenere ANIIMO.
    if "aniimo" not in title:
        print(
            f"SCARTATO - ANIIMO non presente nel titolo: "
            f"{article['title']}"
        )
        return False

    # Proviamo a leggere la pagina.
    page_text = get_page_text(
        article["link"]
    ).lower()

    combined_text = (
        title
        + " "
        + description
        + " "
        + page_text
    )

    # Conta quante volte compare ANIIMO.
    occurrences = combined_text.count("aniimo")

    print(
        f"Controllo rilevanza: "
        f"{article['title']} "
        f"(ANIIMO x{occurrences})"
    )

    # Se compare soltanto una volta in tutta la pagina,
    # è probabilmente una citazione casuale.
    if occurrences < 2:
        print("SCARTATO - ANIIMO citato troppo poco.")
        return False

    return True


def load_seen():

    if not os.path.exists(SEEN_FILE):
        return set()

    try:

        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return set(json.load(f))

    except Exception:

        return set()


def save_seen(seen):

    with open(
        SEEN_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            list(seen),
            f,
            ensure_ascii=False,
            indent=2
        )


def get_source(url):

    try:

        domain = urlparse(url).netloc

        domain = domain.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:

        return "Fonte"


def make_summary(article):

    description = clean_text(
        article.get("description", "")
    )

    if not description:
        return ""

    # Evita descrizioni enormi.
    if len(description) > 350:
        description = description[:350].rsplit(
            " ",
            1
        )[0] + "..."

    return description


def send_message(article):

    source = get_source(
        article["link"]
    )

    summary = make_summary(
        article
    )

    message = (
        "🏳️‍🌈 ANIIMO NEWS\n\n"
        f"📰 {article['title']}\n\n"
    )

    if summary:
        message += (
            f"📌 {summary}\n\n"
        )

    message += (
        f"🌐 Fonte: {source}\n"
        f"🔗 {article['link']}"
    )

    url = (
        f"https://api.telegram.org/"
        f"bot{TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False
        },
        timeout=30
    )

    response.raise_for_status()


def main():

    print(
        "==================================="
    )

    print(
        "       ANIIMO NEWS - CONTROLLO"
    )

    print(
        "==================================="
    )

    articles = get_news()

    print(
        f"Articoli trovati dalle ricerche: "
        f"{len(articles)}"
    )

    if not articles:

        print(
            "Nessun articolo ANIIMO trovato."
        )

        return

    seen = load_seen()

    candidates = []

    for article in articles:

        if article["link"] in seen:

            print(
                f"GIÀ PUBBLICATO: "
                f"{article['title']}"
            )

            continue

        candidates.append(article)

    print(
        f"Nuovi candidati: "
        f"{len(candidates)}"
    )

    if not candidates:

        print(
            "Nessuna nuova notizia ANIIMO."
        )

        return

    relevant_articles = []

    for article in candidates:

        if is_relevant(article):

            relevant_articles.append(
                article
            )

    print(
        f"Articoli realmente rilevanti: "
        f"{len(relevant_articles)}"
    )

    if not relevant_articles:

        print(
            "Nessuna nuova notizia realmente "
            "rilevante per ANIIMO."
        )

        return

    published = 0

    for article in relevant_articles[:3]:

        try:

            send_message(article)

            seen.add(
                article["link"]
            )

            published += 1

            print(
                f"PUBBLICATA: "
                f"{article['title']}"
            )

        except Exception as e:

            print(
                f"Errore pubblicazione: {e}"
            )

    save_seen(seen)

    print(
        f"Totale pubblicate: {published}"
    )


if __name__ == "__main__":
    main()
