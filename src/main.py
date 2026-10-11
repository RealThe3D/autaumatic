"""App entry point. Run with: python -m src.main [--debug] [--gemini]"""

import argparse
import logging
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import uvicorn

from . import capture, gemini, hotkey, market, messages, ocr, server
from .config import Config, load_config
from .match import resolve

logger = logging.getLogger(__name__)

DEBUG_DIR = Path("debug")


def scan_once(cfg: Config, market: market.Market, broadcaster: server.Broadcaster,
              debug: bool = False, engine: str = "tesseract") -> None:
    """Capture, read item names, match, look up prices, and broadcast the result."""
    broadcaster.broadcast(messages.scan_started())
    img = capture.capture_strip(cfg)
    if engine == "gemini":
        lines = gemini.read_lines(img, cfg)
        processed = None
    else:
        processed = ocr.preprocess(img)
        lines = ocr.read_lines(processed)
    items = market.item_index()

    results = []
    for line in lines:
        match = resolve(line.text, items, cfg.match_threshold)
        if match.known:
            plat, ducats = market.lookup(match.url_name)
            url_name: str | None = match.url_name
        else:
            plat, ducats, url_name = None, None, None
        results.append({
            "name": match.name,
            "url_name": url_name,
            "plat": plat,
            "ducats": ducats,
            "confidence": round(line.confidence, 1),
            "known": match.known,
        })
    if debug:
        save_debug(img, processed, lines)
    broadcaster.broadcast(messages.scan_result(results))


def save_debug(img, processed, lines) -> None:
    """Save the crop, the preprocessed image, and the read text for inspection."""
    out = DEBUG_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / "crop.png"), img)
    if processed is not None:
        cv2.imwrite(str(out / "processed.png"), processed)
    with open(out / "ocr.txt", "w") as f:
        for line in lines:
            f.write(f"{line.confidence:5.1f}  {line.text}\n")
    logger.info("Debug output saved to %s", out)


def worker(queue: queue.Queue, cfg: Config, market: market.Market,
           broadcaster: server.Broadcaster, debug: bool, engine: str) -> None:
    """Runs scans one at a time on the hotkey's behalf."""
    while True:
        queue.get()  # debounces: extra presses are dropped while busy
        time.sleep(cfg.scan_delay)
        try:
            scan_once(cfg, market, broadcaster, debug, engine)
        except gemini.GeminiError as exc:
            logger.error("%s", exc)
            broadcaster.broadcast(messages.error(str(exc)))
        except Exception:
            logger.exception("Scan failed")
            broadcaster.broadcast(messages.error("Scan failed, see backend log"))
        broadcaster.broadcast(messages.status("idle"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Autaumatic relic reward scanner backend")
    parser.add_argument("--debug", action="store_true",
                        help="save each crop and its OCR text to disk")
    parser.add_argument("--gemini", action="store_true",
                        help="use Gemini vision instead of Tesseract OCR")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    cfg = load_config(Path("config.toml"))
    engine = "gemini" if args.gemini else cfg.engine
    if engine == "gemini":
        logger.info("Using Gemini vision (%s)", cfg.gemini_model)
    else:
        ocr.setup(cfg)

    broadcaster = server.Broadcaster()
    thread = threading.Thread(
        target=uvicorn.run,
        args=(server.create_app(broadcaster),),
        kwargs={"host": cfg.host, "port": cfg.port, "log_level": "warning"},
        daemon=True,
    )
    thread.start()

    scans: queue.Queue = queue.Queue(maxsize=1)
    hotkey.start(cfg.hotkey, lambda: scans.put_nowait(None))
    logger.info("Ready. Press %s on the reward screen to scan.", cfg.hotkey)
    worker(scans, cfg, market.Market(cfg.cache_ttl, cfg.rate_limit),
           broadcaster, args.debug, engine)


if __name__ == "__main__":
    main()