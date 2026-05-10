import feedparser
import config
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def fetch_headlines(max_total=15):
    all_articles = []
    seen_titles = set()

    for source_name, feed_url in config.RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                published = entry.get("published", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                all_articles.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "published": published,
                    "summary": summary,
                })
        except Exception as e:
            logging.warning(f"Failed to parse feed {feed_url}: {e}")
            continue

    return all_articles[:max_total]
