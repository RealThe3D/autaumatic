"""warframe.market client with a TTL cache and simple rate limiting."""

import time

import requests

BASE_URL = "https://api.warframe.market/v2"
HEADERS = {"Platform": "pc", "Accept": "application/json"}


class Market:
    """Fetches item names, plat prices, and ducat values, cached with a TTL."""

    def __init__(self, ttl: float = 300.0, rate_limit: float = 0.3) -> None:
        self.ttl = ttl
        self.rate_limit = rate_limit
        self._last_request = 0.0
        self._cache: dict[str, tuple[float, object]] = {}

    def _get(self, path: str) -> dict:
        """GET an API path, waiting out the rate limit, returning the raw JSON."""
        wait = self._last_request + self.rate_limit - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        response = requests.get(BASE_URL + path, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()

    def _cached(self, key: str) -> object | None:
        entry = self._cache.get(key)
        if entry and time.monotonic() < entry[0]:
            return entry[1]
        return None

    def _store(self, key: str, value: object) -> None:
        self._cache[key] = (time.monotonic() + self.ttl, value)

    def item_index(self) -> dict[str, str] | None:
        """Index of {item name: url_name (slug)}, or None if the API is unreachable.

        Forma blueprints are skipped: they are on every relic reward screen
        but are not traded.
        """
        cached = self._cached("items")
        if cached is not None:
            return cached
        try:
            data = self._get("/items")["data"]
        except requests.RequestException:
            return None
        index = {
            entry["i18n"]["en"]["name"]: entry["slug"]
            for entry in data
            if entry["slug"] != "forma_blueprint"
        }
        self._store("items", index)
        return index

    def lookup(self, url_name: str) -> tuple[int | None, int | None]:
        """Plat price and ducat value for a url_name; None on any failure."""
        if url_name in self._cache:
            cached = self._cached(url_name)
            if cached is not None:
                return cached
        try:
            top = self._get(f"/orders/item/{url_name}/top")["data"]
            item = self._get(f"/item/{url_name}")["data"]
        except (requests.RequestException, KeyError):
            return (None, None)
        sells = [order["platinum"] for order in top.get("sell", [])]
        result = (min(sells) if sells else None, item.get("ducats"))
        self._store(url_name, result)
        return result