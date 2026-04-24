"""
Scraper for DataCentre Magazine (datacentremagazine.com).

Strategy:
  - The site uses Next.js; article pages are behind Cloudflare.
  - However, the /news listing page embeds full article data in __NEXT_DATA__.
  - Article objects are nested inside section.layouts.section.layout[].cols[]
    .widgetArea.widgets[].articles.results[].
  - Each article has: headline, fullUrlPath, _id (MongoDB ObjectID).
  - The MongoDB ObjectID's first 4 bytes encode a Unix timestamp → publication date.
    This avoids needing to visit individual article pages.
"""

import json
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from utils.filters import is_within_days, detect_region

NEWS_URL = "https://datacentremagazine.com/news"
BASE_URL = "https://datacentremagazine.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _objectid_to_date(oid: str) -> str:
    """
    Decode publication date from a MongoDB ObjectID string.
    The first 8 hex chars represent a Unix timestamp (seconds).
    Returns date as YYYY-MM-DD string.
    """
    try:
        timestamp = int(oid[:8], 16)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return "N/A"


def _extract_articles_from_layout(layout: list) -> list[dict]:
    """Walk the section layout tree and collect all article result objects."""
    articles = []
    for row in layout:
        for col in row.get("cols", []):
            widget_area = col.get("widgetArea", {})
            for widget in widget_area.get("widgets", []):
                for art in widget.get("articles", {}).get("results", []):
                    articles.append(art)
    return articles


def scrape_dcm() -> list[dict]:
    """
    Scrape DataCentre Magazine via __NEXT_DATA__ on the /news page.
    Returns list of dicts: {Title, Date, Source, URL}.
    Applies: 5-day date filter.
    """
    results = []
    try:
        response = requests.get(NEWS_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"  [DCM] Failed to fetch news page: {e}")
        return results

    soup = BeautifulSoup(response.text, "lxml")
    nd_script = soup.find("script", id="__NEXT_DATA__")
    if not nd_script or not nd_script.string:
        print("  [DCM] __NEXT_DATA__ not found on page")
        return results

    try:
        data = json.loads(nd_script.string)
    except json.JSONDecodeError as e:
        print(f"  [DCM] Failed to parse __NEXT_DATA__: {e}")
        return results

    page_props = data.get("props", {}).get("pageProps", {})
    layout = (
        page_props
        .get("section", {})
        .get("layouts", {})
        .get("section", {})
        .get("layout", [])
    )

    raw_articles = _extract_articles_from_layout(layout)
    seen_urls = set()

    for art in raw_articles:
        try:
            oid = art.get("_id", "")
            headline = art.get("headline", "")
            full_path = art.get("fullUrlPath", "")

            if not headline or not full_path or not oid:
                continue

            url = BASE_URL + full_path
            if url in seen_urls:
                continue
            seen_urls.add(url)

            date_str = _objectid_to_date(oid)

            # Apply date filter
            if not is_within_days(date_str):
                continue

            results.append({
                "Title": headline,
                "Date": date_str,
                "Source": "DataCentre Magazine",
                "Region": detect_region(headline) or "",
                "URL": url,
            })

        except Exception as e:
            print(f"  [DCM] Skipping article due to error: {e}")
            continue

    return results
