"""Screen grab and crop using fractional coordinates."""

import mss
import numpy as np

from .config import Config


def capture_strip(cfg: Config) -> np.ndarray:
    """Grab the configured monitor and crop it to the reward strip using fractions.

    Returns a BGR image. Fractions are resolved against the monitor size at
    runtime, so they hold across resolutions and aspect ratios.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[cfg.monitor]
        shot = sct.grab(monitor)
    img = np.asarray(shot)[:, :, :3]  # BGRA -> BGR
    height, width = img.shape[:2]
    left, top, right, bottom = cfg.crop
    return img[
        int(top * height):int(bottom * height),
        int(left * width):int(right * width),
    ]