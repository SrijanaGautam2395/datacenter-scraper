import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to Python path so scrapers/ and utils/ are importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scrapers.dcd import scrape_dcd
from scrapers.dck import scrape_dck
from scrapers.dcf import scrape_dcf
from scrapers.dcm import scrape_dcm
from utils.filters import is_within_days

app = FastAPI(title="Data Center News Scraper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

SOURCE_MAP = {
    "dcd": scrape_dcd,
    "dck": scrape_dck,
    "dcf": scrape_dcf,
    "dcm": scrape_dcm,
}


def _run_scrapers(sources, days=5, keyword="", region=""):
    all_articles = []
    errors = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(SOURCE_MAP[k]): k for k in sources if k in SOURCE_MAP}
        for future in as_completed(futures):
            key = futures[future]
            try:
                all_articles.extend(future.result())
            except Exception as e:
                errors.append({"source": key, "error": str(e)})

    seen, unique = set(), []
    for art in all_articles:
        if art["URL"] not in seen:
            seen.add(art["URL"])
            unique.append(art)

    unique = [a for a in unique if is_within_days(a["Date"], days)]
    if keyword:
        unique = [a for a in unique if keyword.lower() in a["Title"].lower()]
    if region:
        unique = [a for a in unique if a.get("Region", "") == region or a.get("Source") != "DataCenterDynamics"]

    unique.sort(key=lambda x: x["Date"], reverse=True)
    return unique, errors


@app.get("/api/articles")
def get_articles(
    source: Optional[str] = Query(default=None),
    days: int = Query(default=5, ge=1, le=30),
    keyword: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
):
    start = time.time()
    sources = [s.strip().lower() for s in source.split(",")] if source else list(SOURCE_MAP.keys())
    sources = [s for s in sources if s in SOURCE_MAP]
    articles, errors = _run_scrapers(sources, days=days, keyword=keyword or "", region=region or "")

    return {
        "count": len(articles),
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.time() - start, 2),
        "articles": articles,
        "errors": errors,
    }


class SheetsPayload(BaseModel):
    sheet_id: str
    articles: List[Dict[str, Any]]


@app.post("/api/export-sheets")
def export_to_sheets(payload: SheetsPayload):
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise HTTPException(status_code=500, detail="GOOGLE_SERVICE_ACCOUNT_JSON env var not set on Vercel")

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_data = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        client = gspread.authorize(creds)

        sheet = client.open_by_key(payload.sheet_id).sheet1

        # Add header row if sheet is empty
        existing = sheet.get_all_values()
        if not existing:
            sheet.append_row(["Title", "Date", "Source", "Region", "URL"])

        rows = [
            [
                a.get("Title", ""),
                a.get("Date", ""),
                a.get("Source", ""),
                a.get("Region", ""),
                a.get("URL", ""),
            ]
            for a in payload.articles
        ]
        sheet.append_rows(rows, value_input_option="USER_ENTERED")

        return {"appended": len(rows)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {"message": "Data Center News Scraper API — running on Vercel"}
