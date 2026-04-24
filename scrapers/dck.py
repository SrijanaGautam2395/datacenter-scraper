"""
Scraper for DataCenterKnowledge (datacenterknowledge.com).

Strategy:
  - The site's homepage is largely JS-rendered, but an RSS feed at /rss.xml
    is publicly accessible and returns 50 recent articles with full metadata.
  - Parse the RSS feed using BeautifulSoup's XML parser.
"""

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from utils.filters import is_within_days, detect_region

RSS_URL = "https://www.datacenterknowledge.com/rss.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def scrape_dck() -> list[dict]:
    """
    Scrape DataCenterKnowledge via RSS feed.
    Returns list of dicts: {Title, Date, Source, URL}.
    Applies: 5-day date filter.
    """
    results = []
    try:
        response = requests.get(RSS_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"  [DCK] Failed to fetch RSS: {e}")
        return results

    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")

    for item in items:
        try:
            title_tag = item.find("title")
            link_tag = item.find("link")
            pubdate_tag = item.find("pubDate")

            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text(strip=True)
            url = link_tag.get_text(strip=True)

            # Normalize date to YYYY-MM-DD
            if pubdate_tag and pubdate_tag.get_text(strip=True):
                raw_date = pubdate_tag.get_text(strip=True)
                try:
                    date_str = dateparser.parse(raw_date).strftime("%Y-%m-%d")
                except Exception:
                    date_str = "N/A"
            else:
                date_str = "N/A"

            # Apply date filter
            if not is_within_days(date_str):
                continue

            results.append({
                "Title": title,
                "Date": date_str,
                "Source": "DataCenterKnowledge",
                "Region": detect_region(title) or "",
                "URL": url,
            })

        except Exception as e:
            print(f"  [DCK] Skipping item due to error: {e}")
            continue

    return results
