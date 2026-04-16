"""
FastAPI server — exposes the scraper as a REST API.

Endpoints:
  GET /api/articles          → scrape all sources, return JSON
  GET /api/articles?source=dcd   → filter by source name
  GET /api/articles/cached   → return last cached result (no re-scrape)

Run:
  py -m uvicorn api:app --reload --port 8000

Then call from frontend:
  fetch("http://localhost:8000/api/articles")
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from scrapers.dcd import scrape_dcd
from scrapers.dck import scrape_dck
from scrapers.dcf import scrape_dcf
from scrapers.dcm import scrape_dcm

app = FastAPI(title="Data Center News Scraper API", version="1.0.0")

# ── CORS — allow any frontend origin during development ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to your domain in production
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Simple in-memory cache ─────────────────────────────────────────────────────
_cache: dict = {"articles": [], "scraped_at": None}

SOURCE_MAP = {
    "dcd": scrape_dcd,
    "dck": scrape_dck,
    "dcf": scrape_dcf,
    "dcm": scrape_dcm,
}


def _run_scrapers(sources: list[str], days: int = 5, keyword: str = "") -> list[dict]:
    """Run selected scrapers IN PARALLEL and return deduplicated, filtered articles."""
    all_articles = []
    errors = []

    # Run all scrapers at the same time — cuts total time from ~8s to ~3s
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(SOURCE_MAP[key]): key
            for key in sources if key in SOURCE_MAP
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                articles = future.result()
                all_articles.extend(articles)
            except Exception as e:
                errors.append({"source": key, "error": str(e)})

    # Deduplicate by URL
    seen = set()
    unique = []
    for art in all_articles:
        if art["URL"] not in seen:
            seen.add(art["URL"])
            unique.append(art)

    # Apply days filter (re-filter with user-requested days value)
    from utils.filters import is_within_days
    unique = [a for a in unique if is_within_days(a["Date"], days)]

    # Apply keyword filter
    if keyword:
        kw = keyword.lower()
        unique = [a for a in unique if kw in a["Title"].lower()]

    # Sort newest first
    unique.sort(key=lambda x: x["Date"], reverse=True)
    return unique, errors


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/api/articles")
def get_articles(
    source: Optional[str] = Query(default=None, description="dcd,dck,dcf,dcm (comma-separated). Omit for all."),
    days: int = Query(default=5, ge=1, le=30, description="Only articles published within last N days."),
    keyword: Optional[str] = Query(default=None, description="Filter articles whose title contains this keyword."),
):
    """
    Scrape and return articles as JSON.

    Query params:
      ?source=dcd,dck   → only those sources
      ?days=7           → last 7 days (default: 5)
      ?keyword=nvidia   → title must contain 'nvidia'
    """
    start = time.time()

    if source:
        requested = [s.strip().lower() for s in source.split(",")]
        sources = [s for s in requested if s in SOURCE_MAP]
    else:
        sources = list(SOURCE_MAP.keys())

    articles, errors = _run_scrapers(sources, days=days, keyword=keyword or "")

    # Update cache
    _cache["articles"] = articles
    _cache["scraped_at"] = datetime.now().isoformat(timespec="seconds")

    return {
        "count": len(articles),
        "scraped_at": _cache["scraped_at"],
        "elapsed_seconds": round(time.time() - start, 2),
        "articles": articles,
        "errors": errors,
    }


@app.get("/api/articles/cached")
def get_cached_articles():
    """Return the last scraped result without triggering a new scrape."""
    if not _cache["scraped_at"]:
        return {"count": 0, "scraped_at": None, "articles": [], "message": "No cache yet. Call /api/articles first."}
    return {
        "count": len(_cache["articles"]),
        "scraped_at": _cache["scraped_at"],
        "articles": _cache["articles"],
    }


@app.get("/")
def root():
    return {
        "message": "Data Center News Scraper API",
        "endpoints": {
            "GET /api/articles": "Scrape all sources and return articles",
            "GET /api/articles?source=dcd,dck": "Scrape specific sources",
            "GET /api/articles/cached": "Return last cached result",
        },
    }
