# Autaumatic

## Submission for KnightHacks IX

A Warframe relic reward scanner: press a hotkey on the reward screen, and the
backend OCRs the item names, looks up plat and ducat values, and broadcasts
the result to a Tauri overlay over a local WebSocket.

## Running the whole app (Windows)

Capture and the global hotkey must run on Windows, where the game runs.

1. Install prerequisites:
   - Python 3.14+ (or [uv](https://docs.astral.sh/uv/))
   - [Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki) —
     if it is not on `PATH`, set `[ocr] tesseract_cmd` in `config.toml`
   - Node.js and the Rust toolchain (for the Tauri overlay)
2. Clone the repo onto Windows (not the `\\wsl$` share) and copy
   `config.toml` over — it is not checked in.
3. Run the backend:
   ```
   uv sync
   python -m src.main          # add --debug to save crops and OCR text to debug/
   ```
   Add `--gemini` to read item names with Gemini vision instead of Tesseract
   (set `[gemini] api_key` in `config.toml`, the `GEMINI_API_KEY` env var, or
   `GEMINI_API_KEY=...` in a `.env` file in the working directory).
4. Run the overlay:
   ```
   cd autaumatic-overlay
   npm install
   npm run tauri dev           # or npm run tauri build for a standalone exe
   ```
5. On the relic reward screen (windowed or borderless, not exclusive
   fullscreen), press `Alt+\``. Repeated presses while a scan runs are
   ignored.

Note: the overlay window is not transparent/click-through yet (see
`PLANS.md` M6), so it behaves like a normal window for now.

## Backend quick start (WSL/dev)

```
uv sync                          # install Python dependencies
python -m src.main               # run the backend
python -m src.main --debug       # also save crops and OCR text to debug/
python -m src.main --gemini      # use Gemini vision instead of Tesseract OCR
uv run pytest                    # run tests
```

The backend boots and serves `ws://127.0.0.1:8765/ws` from WSL, but the
global hotkey never fires while a Windows window is focused, so real scans
only happen on Windows. The overlay can still be previewed from WSL with
`cd autaumatic-overlay && npm run dev`, then open `http://localhost:1420`.

- Configuration lives in `config.toml` (hotkey, crop fractions, thresholds,
  cache TTL). Crop fractions are fractions of screen size; measure them with
  `python tools/calibrate.py reward.png`.
- Gemini vision is configured under `[gemini]` (model, API key). The key can
  also come from the `GEMINI_API_KEY` environment variable or a `.env` file
  in the working directory (`.env` is gitignored).
- The server binds to `127.0.0.1:8765` and exposes `ws://127.0.0.1:8765/ws`.
- The WebSocket message schema is documented in `src/messages.py`.