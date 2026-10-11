"""Gemini vision as an alternative to Tesseract for reading the reward strip.

Enabled with `python -m src.main --gemini` or `[ocr] engine = "gemini"` in
config.toml. The captured strip is sent to the Gemini API as an image and the
reply is parsed into the same OcrLine objects the rest of the pipeline uses.
"""

import json
import logging
import os

import cv2
import httpx
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from .config import Config
from .ocr import OcrLine

logger = logging.getLogger(__name__)

PROMPT = (
    "This screenshot shows the reward screen from the game Warframe, with one "
    "item name per reward slot. Read every item name exactly as written, "
    "including primes, apostrophes, and ampersands. Ignore UI elements that "
    "are not item names. Reply with only a JSON array of the item name strings."
    "Do not use the term [ITEM NAME] set, such as Paris Prime set. You only look for it's individual components, not the entire set."
    "If the item is Forma. skip it."
)

# Gemini reports no per-word confidence, so a fixed high score keeps the
# pipeline uniform. Match quality is still gated by the fuzzy-match threshold.
CONFIDENCE = 95.0


class GeminiError(RuntimeError):
    """Raised when the Gemini request fails outright; the scan reports an error."""


def parse_names(text: str) -> list[str]:
    """Extract item names from the reply: a JSON array, or one name per line."""
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return [line.strip(" -*") for line in text.splitlines() if line.strip(" -*")]


def read_lines(img: np.ndarray, cfg: Config) -> list[OcrLine]:
    """Send the reward strip to Gemini and return one line per item name."""
    # Read GEMINI_API_KEY from a .env file in the working directory, if present.
    # Real environment variables always win over .env values.
    load_dotenv()
    api_key = cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise GeminiError(
            "No Gemini API key: set [gemini] api_key in config.toml, "
            "GEMINI_API_KEY in the environment, or GEMINI_API_KEY=... in .env"
        )
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise GeminiError("Failed to encode the capture as PNG")
    try:
        with genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30_000),
        ) as client:
            response = client.models.generate_content(
                model=cfg.gemini_model,
                contents=[
                    types.Part.from_bytes(data=buf.tobytes(), mime_type="image/png"),
                    PROMPT,
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=1024,
                ),
            )
            text = response.text
        if text is None:
            raise GeminiError("Gemini returned an empty response")
    except (errors.APIError, httpx.RequestError) as exc:
        raise GeminiError(f"Gemini request failed: {exc}") from exc
    logger.debug("Gemini raw response: %s", text)
    return [OcrLine(name, CONFIDENCE) for name in parse_names(text)]