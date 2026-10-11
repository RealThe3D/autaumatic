"""Loads config.toml into a Config dataclass. All crop regions are fractions of screen size."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    hotkey: str = "<alt>+`"
    scan_delay: float = 0.5
    monitor: int = 1
    ui_scale: float = 1.0
    crop: tuple[float, float, float, float] = (0.31, 0.36, 0.69, 0.62)
    engine: str = "tesseract"
    tesseract_cmd: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_api_key: str = ""
    match_threshold: int = 85
    cache_ttl: float = 300.0
    rate_limit: float = 0.3
    host: str = "127.0.0.1"
    port: int = 8765


def load_config(path: Path) -> Config:
    """Read config.toml and merge it over the defaults. Unknown keys are ignored."""
    data: dict = {}
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
    hotkey = data.get("hotkey", {})
    capture = data.get("capture", {})
    ocr = data.get("ocr", {})
    gemini = data.get("gemini", {})
    match = data.get("match", {})
    market = data.get("market", {})
    server = data.get("server", {})
    return Config(
        hotkey=hotkey.get("combo", Config.hotkey),
        scan_delay=float(hotkey.get("scan_delay", Config.scan_delay)),
        monitor=int(capture.get("monitor", Config.monitor)),
        ui_scale=float(capture.get("ui_scale", Config.ui_scale)),
        crop=tuple(float(v) for v in capture.get("crop", Config.crop)),
        engine=ocr.get("engine", Config.engine),
        tesseract_cmd=ocr.get("tesseract_cmd", Config.tesseract_cmd),
        gemini_model=gemini.get("model", Config.gemini_model),
        gemini_api_key=gemini.get("api_key", Config.gemini_api_key),
        match_threshold=int(match.get("threshold", Config.match_threshold)),
        cache_ttl=float(market.get("cache_ttl", Config.cache_ttl)),
        rate_limit=float(market.get("rate_limit", Config.rate_limit)),
        host=server.get("host", Config.host),
        port=int(server.get("port", Config.port)),
    )