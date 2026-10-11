"""Preprocessing and text extraction for the reward strip."""

import cv2
import numpy as np
import pytesseract

from .config import Config


class OcrLine:
    def __init__(self, text: str, confidence: float) -> None:
        self.text = text
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"OcrLine({self.text!r}, {self.confidence:.0f})"


def setup(cfg: Config) -> None:
    """Point pytesseract at the configured binary, if any."""
    if cfg.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd
    if cfg.engine != "tesseract":
        raise ValueError(f"Unsupported OCR engine: {cfg.engine}")


def preprocess(img: np.ndarray) -> np.ndarray:
    """Grayscale, upscale, and threshold the light-on-dark reward text."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def read_lines(img: np.ndarray) -> list[OcrLine]:
    """OCR the preprocessed strip and return one line per reward slot row."""
    data = pytesseract.image_to_data(
        img, config="--psm 6", output_type=pytesseract.Output.DICT
    )
    lines: dict[tuple[int, int, int], list[tuple[str, int]]] = {}
    for i in range(len(data["text"])):
        word = data["text"][i].strip()
        if not word:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append((word, int(data["conf"][i])))
    result = []
    for key in sorted(lines):
        words = lines[key]
        text = " ".join(word for word, _ in words)
        confidence = sum(conf for _, conf in words) / len(words)
        result.append(OcrLine(text, confidence))
    return result