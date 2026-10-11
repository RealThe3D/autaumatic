"""
Measure crop regions on a screenshot. 
Usage: python tools/calibrate.py reward.png
"""

import sys

import cv2


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python tools/calibrate.py <screenshot>")
    img = cv2.imread(sys.argv[1])
    if img is None:
        sys.exit(f"Could not read {sys.argv[1]}")
    x, y, w, h = cv2.selectROI("Drag a box over the reward strip, press Enter", img)
    print("# config.toml [capture] crop = [left, top, right, bottom] (fractions)")
    print(f"crop = [{x / img.shape[1]:.4f}, {y / img.shape[0]:.4f}, "
          f"{(x + w) / img.shape[1]:.4f}, {(y + h) / img.shape[0]:.4f}]")


if __name__ == "__main__":
    main()