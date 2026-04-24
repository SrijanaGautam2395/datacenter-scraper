"""
Scraper for DataCenterFrontier (datacenterfrontier.com).

Strategy:
  - The site uses Nuxt.js; the homepage does not expose article dates.
  - However, the article sitemap (/sitemap/Article.xml) contains all article URLs
    with lastmod timestamps — we use lastmod as a proxy for publish date.
  - Only articles with lastmod within the last 5 days are visited for full details.
  - Each article page contains JSON-LD (NewsArticle schema) with:
      headline, datePublished, mainEntityOfPage (URL)
"""

import json

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from utils.filters import is_within_days, detect_region

SITEMAP_URL = "https://www.datacenterfrontier.com/sitemap/Article.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _parse_sitemap_articles(days: int = 5) -> list[str]:
    """
    Parse the article sitemap and return URLs of articles
    whose lastmod date falls within the last `days` days.
    """
    candidate_urls = []
    try:
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"  [DCF] Failed to fetch sitemap: {e}")
        return candidate_urls

    soup = BeautifulSoup(response.content, "xml")
    for url_tag in soup.find_all("url"):
        loc = url_tag.find("loc")
        lastmod = url_tag.find("lastmod")
        if not loc:
            continue

        url = loc.get_text(strip=True)

        # Use lastmod as publish-date proxy; skip if missing
        if lastmod and lastmod.get_text(strip=True):
            raw = lastmod.get_text(strip=True)
            try:
                date_str = dateparser.parse(raw).strftime("%Y-%m-%d")
            except Exception:
                date_str = "N/A"
        else:
            date_str = "N/A"

        if is_within_days(date_str, days):
            candidate_urls.append(url)

    return candidate_urls


def _fetch_article_details(url: str) -> dict | None:
    """
    Fetch a single article page and extract title + date from JSON-LD.
    Returns dict or None on failure.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"  [DCF] Failed to fetch article {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "lxml")

    # Check for Cloudflare challenge
    if "Just a moment" in (soup.title.string or "") if soup.title else False:
        print(f"  [DCF] Cloudflare blocked: {url}")
        return None

    # Primary: JSON-LD NewsArticle schema
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "")
            if isinstance(ld, dict) and ld.get("@type") in ("NewsArticle", "Article"):
                title = ld.get("headline", "")
                date_str = ld.get("datePublished", "N/A")
                if date_str and date_str != "N/A":
                    try:
                        date_str = dateparser.parse(date_str).strftime("%Y-%m-%d")
                    except Exception:
                        date_str = "N/A"
                if title:
                    return {"title": title, "date": date_str, "url": url}
        except Exception:
            continue

    # Fallback: <div class="date"> + <title> tag
    title_tag = soup.title
    title = title_tag.string.split("|")[0].strip() if title_tag else ""

    date_div = soup.find("div", class_="date")
    if date_div:
        raw = date_div.get_text(strip=True)
        try:
            date_str = dateparser.parse(raw).strftime("%Y-%m-%d")
        except Exception:
            date_str = "N/A"
    else:
        # Try meta tag
        meta_date = soup.find("meta", attrs={"name": "date-pub"})
        if meta_date:
            try:
                date_str = dateparser.parse(meta_date["content"]).strftime("%Y-%m-%d")
            except Exception:
                date_str = "N/A"
        else:
            date_str = "N/A"

    if title:
        return {"title": title, "date": date_str, "url": url}
    return None


def scrape_dcf() -> list[dict]:
    """
    Scrape DataCenterFrontier via article sitemap + individual article pages.
    Returns list of dicts: {Title, Date, Source, URL}.
    Applies: 5-day date filter.
    """
    results = []

    candidate_urls = _parse_sitemap_articles(days=5)
    print(f"  [DCF] {len(candidate_urls)} recent articles found in sitemap")

    for url in candidate_urls:
        details = _fetch_article_details(url)
        if not details:
            continue

        # Double-check with published date (sitemap lastmod might differ slightly)
        if not is_within_days(details["date"]):
            continue

        results.append({
            "Title": details["title"],
            "Date": details["date"],
            "Source": "DataCenterFrontier",
            "Region": detect_region(details["title"]) or "",
            "URL": details["url"],
        })

    return results
