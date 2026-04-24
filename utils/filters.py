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
    "Asia Pacific": [
        "asia", "pacific", "apac", "india", "indian", "china",
        "chinese", "japan", "japanese", "singapore", "australia",
        "australian", "south korea", "korean", "indonesia", "malaysia",
        "thailand", "philippines", "taiwan", "hong kong", "new zealand",
        "mumbai", "bangalore", "hyderabad", "delhi", "beijing",
        "shanghai", "tokyo", "sydney", "melbourne", "seoul",
        "vietnam", "sri lanka", "pakistan", "bangladesh",
        "chennai", "pune", "kolkata", "osaka", "yokohama",
        "jakarta", "kuala lumpur", "bangkok", "manila",
        "auckland", "perth", "brisbane", "adelaide",
    ],
    "Europe": [
        "europe", "european", "uk", "united kingdom", "england",
        "ireland", "germany", "german", "france", "french",
        "netherlands", "dutch", "sweden", "swedish", "finland",
        "finnish", "denmark", "norway", "norwegian", "spain", "spanish",
        "italy", "italian", "poland", "polish",
        "switzerland", "swiss", "austria", "austrian", "belgium",
        "portugal", "czechia", "czech", "romania", "greece", "greek",
        "luxembourg", "iceland", "croatia", "serbia", "hungary",
        "edinburgh", "london", "amsterdam", "frankfurt",
        "dublin", "paris", "stockholm", "brussels", "warsaw",
        "munich", "berlin", "madrid", "milan", "barcelona",
        "manchester", "birmingham", "marseille", "vienna", "zurich",
        "oslo", "helsinki", "copenhagen", "lisbon",
        "stellium",
    ],
    "Middle East": [
        "middle east", "saudi", "uae", "dubai", "abu dhabi", "qatar",
        "bahrain", "kuwait", "oman", "jordan", "egypt", "israel",
        "riyadh", "neom", "jeddah", "muscat", "doha", "tel aviv",
        "cairo", "amman",
    ],
    "North America": [
        "us ", "u.s.", "usa", "united states", "american", "america",
        "canada", "canadian", "mexico", "mexican",
        "texas", "virginia", "ohio", "california", "georgia",
        "illinois", "new york", "nevada", "arizona", "florida",
        "north carolina", "south carolina", "iowa", "wyoming",
        "new mexico", "alabama", "pennsylvania", "new jersey",
        "alaska", "colorado", "connecticut", "delaware", "hawaii",
        "idaho", "indiana", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska",
        "new hampshire", "north dakota", "oklahoma", "oregon",
        "rhode island", "south dakota", "tennessee", "utah",
        "vermont", "washington", "west virginia", "wisconsin",
        "silicon valley", "wall street",
        "austin", "dallas", "houston", "san antonio", "phoenix",
        "chicago", "los angeles", "san francisco", "seattle",
        "denver", "atlanta", "boston", "miami", "detroit",
        "minneapolis", "portland", "salt lake", "las vegas",
        "san jose", "san diego", "nashville", "memphis",
        "charlotte", "raleigh", "richmond", "pittsburgh",
        "columbus", "cleveland", "milwaukee", "kansas city",
        "st. louis", "tampa", "orlando", "jacksonville",
        "leesburg", "ashburn", "manassas", "prince william",
        "loudoun", "quincy", "des moines", "mesa", "chandler",
        "hillsboro", "papillion", "elk grove", "lithia springs",
        "toronto", "montreal", "vancouver", "calgary", "ottawa",
        "quebec", "ontario", "alberta", "british columbia",
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
