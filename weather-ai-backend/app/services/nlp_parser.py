import re
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ParsedWeatherRequest:
    location: str
    start_date: date
    end_date: date


MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

GPS_INPUT_PATTERN = re.compile(
    r"^\s*[+-]?\d+(?:\.\d+)?\s*[,\s]\s*[+-]?\d+(?:\.\d+)?\s*$"
)


def _extract_dates(text: str) -> tuple[list[date], str]:
    found_dates: list[date] = []
    cleaned = text
    today = date.today()

    # 1. Relative keywords ("today", "tomorrow", "day after tomorrow")
    if re.search(r"\bday after tomorrow\b", cleaned, re.I):
        found_dates.append(today + timedelta(days=2))
        cleaned = re.sub(r"\bday after tomorrow\b", " ", cleaned, flags=re.I)
    if re.search(r"\btomorrow\b", cleaned, re.I):
        found_dates.append(today + timedelta(days=1))
        cleaned = re.sub(r"\btomorrow\b", " ", cleaned, flags=re.I)
    if re.search(r"\btoday\b", cleaned, re.I):
        found_dates.append(today)
        cleaned = re.sub(r"\btoday\b", " ", cleaned, flags=re.I)

    # 2. ISO format: YYYY-MM-DD or YYYY/MM/DD
    for m in re.finditer(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", cleaned):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            found_dates.append(date(y, mo, d))
        except ValueError:
            pass
    cleaned = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", cleaned)

    # 3. Day-first or Month-first numeric: DD-MM-YYYY, DD/MM/YYYY, MM-DD-YYYY
    for m in re.finditer(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", cleaned):
        p1, p2, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        day_val, month_val = (p1, p2) if p1 > 12 or p2 <= 12 else (p2, p1)
        try:
            found_dates.append(date(y, month_val, day_val))
        except ValueError:
            pass
    cleaned = re.sub(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b", " ", cleaned)

    # 4. Month name formats: "14 Nov 2026", "Nov 14, 2026", "14 Nov", "Nov 14"
    month_names = "|".join(MONTH_MAP.keys())
    pattern_dmy = re.compile(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})(?:\s*,?\s*(\d{{4}}))?\b",
        re.I,
    )
    for m in pattern_dmy.finditer(cleaned):
        d = int(m.group(1))
        mo = MONTH_MAP[m.group(2).lower()]
        y = int(m.group(3)) if m.group(3) else today.year
        try:
            found_dates.append(date(y, mo, d))
        except ValueError:
            pass
    cleaned = pattern_dmy.sub(" ", cleaned)

    pattern_mdy = re.compile(
        rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{{4}}))?\b",
        re.I,
    )
    for m in pattern_mdy.finditer(cleaned):
        mo = MONTH_MAP[m.group(1).lower()]
        d = int(m.group(2))
        y = int(m.group(3)) if m.group(3) else today.year
        try:
            found_dates.append(date(y, mo, d))
        except ValueError:
            pass
    cleaned = pattern_mdy.sub(" ", cleaned)

    return found_dates, cleaned


def parse_freeform_query(raw_text: str) -> ParsedWeatherRequest:
    today = date.today()
    dates, remaining = _extract_dates(raw_text)
    remaining = re.sub(r"right\s*now\b", " ", remaining, flags=re.I)
    coordinate_input = remaining.strip()

    # Strip conversational filler words while keeping location tokens intact
    filler_pattern = re.compile(
        r"\b("
        r"i|me|my|we|you|it|its|it's|what|whats|what's|tell|show|get|give|check|find|know|exact|"
        r"is|are|was|were|be|been|being|do|does|did|can|could|would|should|will|"
        r"the|a|an|this|that|these|those|over|there|here|right|now|currently|current|"
        r"time|date|day|weather|forecast|temperature|temp|report|climate|conditions|"
        r"in|at|near|around|for|on|from|to|between|and|of|with|please|hey|hi|hello"
        r")\b",
        flags=re.I,
    )
    location_clean = filler_pattern.sub(" ", remaining)
    if GPS_INPUT_PATTERN.fullmatch(coordinate_input):
        location_clean = coordinate_input
    else:
        location_clean = re.sub(r"[?!.,;:\"'()]+", " ", location_clean)
    location_clean = re.sub(r"\s+", " ", location_clean).strip()

    if not location_clean:
        location_clean = raw_text.strip()

    if len(dates) >= 2:
        start_d, end_d = min(dates[0], dates[1]), max(dates[0], dates[1])
    elif len(dates) == 1:
        start_d = end_d = dates[0]
    else:
        start_d = today
        end_d = today + timedelta(days=4)

    return ParsedWeatherRequest(
        location=location_clean,
        start_date=start_d,
        end_date=end_d,
    )

def get_default_date_range() -> tuple[date, date]:
    start_date = date.today()
    end_date = start_date + timedelta(days=4)  # 5 inclusive calendar days
    return start_date, end_date