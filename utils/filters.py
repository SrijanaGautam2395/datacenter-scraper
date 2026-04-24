"""
Filtering utilities: date filter and region detection (all sources).
"""

from datetime import datetime, timedelta, timezone


def is_within_days(date_str: str, days: int = 5) -> bool:
    """Return True if date_str (YYYY-MM-DD) is within the last `days` days."""
    if not date_str or date_str == "N/A":
        return False
    try:
        article_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        return article_date >= cutoff
    except ValueError:
        return False


# Keywords used to detect region from article title.
# Applied to ALL sources via keyword matching on the title.
REGION_KEYWORDS = {
    "North America": [
        "us ", "u.s.", "usa", "united states", "american", "america",
        "canada", "canadian", "mexico", "texas", "virginia", "ohio",
        "california", "georgia", "illinois", "new york", "nevada",
        "arizona", "florida", "north carolina", "iowa", "wyoming",
        "new mexico", "alabama", "pennsylvania", "new jersey",
        "silicon valley", "aws", "google", "meta", "microsoft",
        "switch", "flexential", "coreweave", "equinix us",
    ],
    "Europe": [
        "europe", "european", "uk", "united kingdom", "england",
        "ireland", "germany", "german", "france", "french",
        "netherlands", "dutch", "sweden", "swedish", "finland",
        "finland", "denmark", "norway", "spain", "italy", "poland",
        "switzerland", "austria", "belgium", "portugal", "czechia",
        "luxembourg", "edinburgh", "london", "amsterdam", "frankfurt",
        "dublin", "paris", "stockholm", "brussels", "warsaw",
        "cellnex", "vantage", "pure dc", "global data",
    ],
    "Middle East": [
        "middle east", "saudi", "uae", "dubai", "abu dhabi", "qatar",
        "bahrain", "kuwait", "oman", "jordan", "egypt", "israel",
        "riyadh", "neom",
    ],
    "Asia Pacific": [
        "asia", "pacific", "apac", "india", "indian", "china",
        "chinese", "japan", "japanese", "singapore", "australia",
        "australian", "south korea", "korean", "indonesia", "malaysia",
        "thailand", "philippines", "taiwan", "hong kong", "new zealand",
        "mumbai", "bangalore", "hyderabad", "delhi", "beijing",
        "shanghai", "tokyo", "sydney", "melbourne", "seoul",
    ],
}

ALLOWED_REGIONS = set(REGION_KEYWORDS.keys())


def detect_region(*texts: str) -> str | None:
    """
    Detect region from one or more text strings (title, description, URL, body)
    via keyword matching. Checks all provided texts.
    Returns region name if matched, else None.
    """
    combined = " ".join(t for t in texts if t).lower()
    for region, keywords in REGION_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return region
    return None


def passes_region_filter(title: str) -> bool:
    """Return True if the article title matches an allowed region."""
    return detect_region(title) is not None
