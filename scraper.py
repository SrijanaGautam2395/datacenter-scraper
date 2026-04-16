"""
Data Center News Scraper
========================
Scrapes recent articles from 4 data center industry websites:
  1. DataCenterDynamics  (datacenterdynamics.com)
  2. DataCenterKnowledge (datacenterknowledge.com)
  3. DataCenterFrontier  (datacenterfrontier.com)
  4. DataCentre Magazine (datacentremagazine.com)

Filters:
  - Last 5 days (all sources)
  - Region: North America / Europe / Middle East / Asia Pacific (DCD only)

Output:
  - CSV file in ./output/
  - Optional: Google Sheets (set PUSH_TO_SHEETS = True and configure GOOGLE_SHEET_ID)

Usage:
  py scraper.py
"""

import io
import sys
import time

# Force UTF-8 output on Windows to avoid encoding errors with special characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from scrapers.dcd import scrape_dcd
from scrapers.dck import scrape_dck
from scrapers.dcf import scrape_dcf
from scrapers.dcm import scrape_dcm
from utils.output import save_to_csv, push_to_google_sheets

# ── Configuration ──────────────────────────────────────────────────────────────

# Set to True to also push results to Google Sheets.
# Requires service_account.json (see utils/output.py for full setup instructions).
PUSH_TO_SHEETS = False

# Your Google Sheet ID (from the URL: .../spreadsheets/d/<SHEET_ID>/edit)
GOOGLE_SHEET_ID = "YOUR_SHEET_ID_HERE"

# Worksheet (tab) name to write into
GOOGLE_SHEET_WORKSHEET = "Articles"

# Path to your Google service account credentials JSON
GOOGLE_CREDENTIALS_FILE = "service_account.json"

# ── Main ───────────────────────────────────────────────────────────────────────


def run():
    start = time.time()
    all_articles = []

    scrapers = [
        ("DataCenterDynamics",  scrape_dcd),
        ("DataCenterKnowledge", scrape_dck),
        ("DataCenterFrontier",  scrape_dcf),
        ("DataCentre Magazine", scrape_dcm),
    ]

    for name, scrape_fn in scrapers:
        print(f"\n[{name}] Scraping...")
        try:
            articles = scrape_fn()
            print(f"  → {len(articles)} articles collected")
            all_articles.extend(articles)
        except Exception as e:
            print(f"  [ERROR] {name} failed entirely: {e}")

    # Deduplicate by URL
    seen_urls = set()
    unique_articles = []
    for art in all_articles:
        if art["URL"] not in seen_urls:
            seen_urls.add(art["URL"])
            unique_articles.append(art)

    duplicates_removed = len(all_articles) - len(unique_articles)

    # Sort by date descending
    unique_articles.sort(key=lambda x: x["Date"], reverse=True)

    # Save to CSV
    csv_path = save_to_csv(unique_articles)

    elapsed = time.time() - start

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  SCRAPE COMPLETE  ({elapsed:.1f}s)")
    print("=" * 60)
    print(f"  Total articles collected : {len(all_articles)}")
    print(f"  Duplicates removed       : {duplicates_removed}")
    print(f"  Unique articles          : {len(unique_articles)}")
    print(f"  CSV saved to             : {csv_path}")
    print()

    # Per-source breakdown
    from collections import Counter
    counts = Counter(a["Source"] for a in unique_articles)
    for source, count in sorted(counts.items()):
        print(f"    {source:<30} {count} articles")

    # Optional Google Sheets push
    if PUSH_TO_SHEETS:
        print("\n[Google Sheets] Pushing data...")
        push_to_google_sheets(
            unique_articles,
            sheet_id=GOOGLE_SHEET_ID,
            worksheet_name=GOOGLE_SHEET_WORKSHEET,
            credentials_file=GOOGLE_CREDENTIALS_FILE,
        )

    print()
    return unique_articles


if __name__ == "__main__":
    run()
