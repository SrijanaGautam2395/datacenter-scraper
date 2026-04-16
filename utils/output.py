"""
Output utilities: save results to CSV and optionally push to Google Sheets.
"""

import os
from datetime import datetime

import pandas as pd

# ── CSV ────────────────────────────────────────────────────────────────────────

def save_to_csv(articles: list[dict], output_dir: str = "output") -> str:
    """Save article list to a timestamped CSV file. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"articles_{timestamp}.csv")

    df = pd.DataFrame(articles, columns=["Title", "Date", "Source", "URL"])
    df.to_csv(filepath, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel compat
    return filepath


# ── Google Sheets (Optional) ───────────────────────────────────────────────────
#
# SETUP INSTRUCTIONS:
# 1. Go to https://console.cloud.google.com and create a project.
# 2. Enable the "Google Sheets API" for that project.
# 3. Create a Service Account → download the JSON key file.
# 4. Save the JSON key as "service_account.json" in the project root.
# 5. Create a Google Sheet and share it (Editor access) with the service account email
#    (looks like: name@project.iam.gserviceaccount.com).
# 6. Copy the Sheet ID from the URL:
#    https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
# 7. Set GOOGLE_SHEET_ID in scraper.py or as an env variable.

SHEET_HEADER = ["Title", "Date", "Source", "URL"]


def push_to_google_sheets(
    articles: list[dict],
    sheet_id: str,
    worksheet_name: str = "Articles",
    credentials_file: str = "service_account.json",
) -> bool:
    """
    Push articles to a Google Sheet.
    Returns True on success, False on failure.

    Requires: gspread, google-auth (already installed).
    Requires: service_account.json in the project root (see instructions above).
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_key(sheet_id)

        # Get or create worksheet
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=10)

        # Clear existing content and write fresh data
        worksheet.clear()
        rows = [SHEET_HEADER] + [
            [a["Title"], a["Date"], a["Source"], a["URL"]] for a in articles
        ]
        worksheet.update("A1", rows)

        print(f"  Google Sheets updated: {len(articles)} rows written to '{worksheet_name}'")
        return True

    except FileNotFoundError:
        print(f"  [Sheets] '{credentials_file}' not found. Skipping Google Sheets upload.")
        print("  See output.py for setup instructions.")
        return False
    except Exception as e:
        print(f"  [Sheets] Error: {e}")
        return False
