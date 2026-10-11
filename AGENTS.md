Guidance for AI coding agents working in this repo. See `PLANS.md` for the roadmap.
 
## Project overview
 
A Python app that, on a global hotkey press, captures the Warframe relic reward screen, OCRs the item names, fuzzy-matches them to real items, fetches plat and ducat values from warframe.market, and broadcasts the result over a local WebSocket to a Tauri overlay (the frontend) that displays it on top of the game.
 
## Stack
 
- Python 3.14+
- Hotkey: `pynput`
- Capture: `mss`
- Image processing: `opencv-python`
- OCR: `pytesseract`
- Matching: `rapidfuzz`
- HTTP: `requests`
- Server: FastAPI with a WebSocket endpoint
- Frontend: Tauri overlay (Rust shell) with a TypeScript web UI that connects to the WebSocket
- Tray: `pystray`
## Suggested layout
 
```
src/
  hotkey.py      # global hotkey listener, non-blocking
  capture.py     # screen grab and crop using fractional coordinates
  ocr.py         # preprocessing and text extraction
  match.py       # fuzzy matching against cached item list
  market.py      # warframe.market client and cache
  server.py      # FastAPI app, WebSocket endpoint, localhost only
  config.py      # loads config.toml
tools/
  calibrate.py   # cv2.selectROI helper that prints crop fractions
tests/
  fixtures/      # reference screenshots by resolution and UI scale
overlay/         # Tauri app
  src/           # web UI: WebSocket client, rendering
  src-tauri/     # Rust side: window config, always-on-top, click-through
config.toml
```
 
## Commands
 
```
pip install -r requirements.txt
python -m src.main            # run the app
python tools/calibrate.py reward.png   # measure crop regions
pytest                        # run tests
 
cd overlay
npm install
npm run tauri dev             # run the overlay in dev mode
npm run tauri build           # build the overlay
```
 
Start the backend first, then the overlay. The overlay should still start and show a "disconnected" state if the backend is not running.
 
Tesseract must be installed separately and be on `PATH`.
 
## Rules
 
**Scope and safety**
- Scan only when the user presses the hotkey. Never add continuous or timed scanning.
- Screen capture only. Do not read game memory, inject code, or simulate game input.
- Bind the server to `127.0.0.1`. Never `0.0.0.0`.
**Code conventions**
- Store crop regions as fractions of screen width and height, never hardcoded pixels. Convert at runtime.
- The hotkey callback must return immediately. Run capture, OCR, and network calls in a worker thread.
- Match OCR text against the cached item list and use the entry's `url_name`. The slugify helper is a fallback only.
- Reject matches below the configured fuzzy-score threshold and report them as unknown instead of guessing.
- Keep the hotkey, OCR engine, UI scale, and resolution override in `config.toml`. Do not hardcode them.
- Cache the item list and prices with a TTL, and respect warframe.market rate limits.
- Type hints on public functions. Keep functions small and testable.
**Overlay and WebSocket**
- The overlay only reads from the backend WebSocket. It must not do OCR, capture the screen, or call warframe.market itself.
- The backend is the source of truth. The overlay renders whatever message it receives.
- Keep the message schema versioned and documented in one place. Change the backend and overlay together when it changes.
- Message types: `scan_started`, `scan_result`, `error`, `status`. A `scan_result` carries a list of items with `name`, `url_name`, `plat`, `ducats`, and `confidence`.
- The overlay window must be transparent, borderless, always-on-top, non-focusable, and click-through by default. It must never steal focus or block mouse input to the game.
- The WebSocket client must reconnect automatically with backoff and show a clear disconnected state.
- Store overlay position and size as fractions of the screen, not pixels.
- The overlay is a separate window. Never hook into, inject into, or read memory from the game process.
**Testing**
- Test OCR and matching against saved screenshots in `tests/fixtures/`, not the live game.
- Add a fixture for every new resolution, UI scale, or squad size that gets supported.
- Unit-test the slugifier and matcher with tricky names (apostrophes, `&`, long two-line names).
**Debugging**
- Add or keep a `--debug` flag that saves each crop and its OCR text to disk. Check crops visually before tuning OCR settings.
## Before you finish a change
 
1. Tests pass.
2. No hardcoded pixel coordinates or hotkeys were added.
3. The hotkey callback is still non-blocking.
4. The WebSocket message schema is consistent between backend and overlay.
5. The overlay is still transparent, click-through, and non-focusable.
6. `PLANS.md` checkboxes are updated if a milestone item was completed.
 