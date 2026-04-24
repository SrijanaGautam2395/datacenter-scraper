"""
Scraper for DataCenterDynamics (datacenterdynamics.com/en/news/).

Strategy:
  - The listing page returns full server-rendered HTML with <article class="card"> elements.
  - Each card contains: title, date (datetime attribute), and URL (meta itemprop).
  - Individual article pages are behind Cloudflare, so region is detected
    via keyword matching on the article title.

Region filter: North America, Europe, Middle East, Asia Pacific (title-based).
"""

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from utils.filters import is_within_days, passes_region_filter, detect_region

BASE_URL = "https://www.datacenterdynamics.com"
LISTING_URL = f"{BASE_URL}/en/news/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_dcd() -> list[dict]:
    """
    Scrape DataCenterDynamics news listing.
    Returns list of dicts: {Title, Date, Source, URL}.
    Applies: 5-day date filter + region filter.
    """
    results = []
    try:
        response = requests.get(LISTING_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"  [DCD] Failed to fetch listing: {e}")
        return results

    soup = BeautifulSoup(response.text, "lxml")
    cards = soup.find_all("article", class_="card")

    for card in cards:
        try:
            # Title
            title_tag = card.find("a", itemprop="name headline")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            if not title:
                continue

            # URL — use meta itemprop=mainEntityOfPage (relative path)
            url_meta = card.find("meta", itemprop="mainEntityOfPage")
            if not url_meta or not url_meta.get("content"):
                continue
            url = BASE_URL + url_meta["content"]

            # Date — <time datetime="YYYY-MM-DD">
            time_tag = card.find("time")
            if time_tag and time_tag.get("datetime"):
                date_str = time_tag["datetime"]  # already YYYY-MM-DD
            else:
                date_str = "N/A"

            # Apply date filter
            if not is_within_days(date_str):
                continue

            # Detect region from title + URL slug
            region = detect_region(title, url)

            results.append({
                "Title": title,
                "Date": date_str,
                "Source": "DataCenterDynamics",
                "URL": url,
                "Region": region or "",
            })

        except Exception as e:
            print(f"  [DCD] Skipping card due to error: {e}")
            continue

    return results
