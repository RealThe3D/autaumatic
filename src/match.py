"""Fuzzy matching of OCR text against the cached item list, with a slugify fallback."""

import re

from rapidfuzz import fuzz, process


class Match:
    def __init__(self, name: str, url_name: str, confidence: float, known: bool) -> None:
        self.name = name
        self.url_name = url_name
        self.confidence = confidence  # fuzzy score, 0-100
        self.known = known            # False when below the threshold

    def __repr__(self) -> str:
        return f"Match({self.name!r}, {self.url_name!r}, {self.confidence:.0f}, known={self.known})"


def slugify(text: str) -> str:
    """Fallback slug: lowercase, underscores, apostrophes stripped, & to 'and'.

    Used only when the cached item list is unavailable and we cannot verify
    a match against real entries.
    """
    text = text.lower().replace("&", " and ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def resolve(text: str, items: dict[str, str] | None, threshold: int) -> Match:
    """Match OCR text against an item index of {name: url_name}.

    Below-threshold matches are reported as unknown instead of guessing.
    """
    if items:
        best = process.extractOne(text, items.keys(), scorer=fuzz.WRatio)
        if best and best[1] >= threshold:
            return Match(name=best[0], url_name=items[best[0]], confidence=best[1], known=True)
    return Match(name=text, url_name=slugify(text), confidence=0.0, known=False)