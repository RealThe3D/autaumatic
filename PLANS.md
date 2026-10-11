Roadmap for a hotkey-triggered Warframe relic reward scanner. When the user presses a keybind on the relic reward screen, the app reads the item names with OCR, looks up platinum and ducat values, and shows them in a Tauri overlay on top of the game.
 
## Goals
 
- Scan only on an explicit keypress (default `Alt+\``), never continuously.
- Read the reward item names from a screenshot with OCR.
- Match noisy OCR text to real item names, then fetch plat and ducat values.
- Broadcast results from the Python backend over a local WebSocket.
- Show results in a Tauri overlay (the frontend) that subscribes to the WebSocket and renders on top of the game window.
- Work across resolutions, aspect ratios, UI scales, and squad sizes (1 to 4 players).
## Non-goals
 
- No reading game memory, injecting into the game, or automating input. Screen capture only.
- No always-on scanning or background polling of the game.
- No exposing the server beyond `127.0.0.1`.
- The overlay is a separate always-on-top window. It never hooks into or injects into the game process.
## Architecture
 
```
hotkey (pynput) -> capture (mss) -> preprocess (OpenCV) -> OCR (Tesseract/EasyOCR)
   or Gemini vision (--gemini flag)
   -> fuzzy match (rapidfuzz vs. cached item list) -> market lookup (warframe.market)
   -> broadcast JSON (FastAPI WebSocket on 127.0.0.1)
   -> Tauri overlay (frontend) receives the message and renders it
```
 
The backend and the overlay are two separate processes. The backend knows nothing about how the data is displayed. The overlay knows nothing about OCR.
 
- The hotkey listener must never block. It sets a flag or hands work to a worker thread.
- Match against the cached item list and use each item's `url_name` from the API. Do not rely on hand-slugified names except as a fallback.
- One JSON message per scan: `{"items": [{"name": "...", "url_name": "...", "plat": 0, "ducats": 0}]}`.
## Milestones
 
### M1: Crop calibration
- [ ] Take reference screenshots of the reward screen at 1080p and 1440p, at least 1 and 4 players.
- [ ] Build `tools/calibrate.py` using `cv2.selectROI` to print crop boxes as fractions of screen size.
- [ ] Store ratios in `config.toml`, keyed by UI scale.
- [ ] Handle ultrawide by anchoring to the screen center.
### M2: OCR pipeline
- [ ] Capture one wide strip covering all four reward slots, then split into per-slot crops.
- [x] Preprocess: grayscale, 2-3x upscale, threshold. Light text on a dark background.
- [ ] OCR each slot with Tesseract. Compare against EasyOCR on the same crops.
- [x] Gemini vision alternative (`--gemini`): send the strip to Gemini
      flash-lite and parse item names from the reply.
- [x] Dump debug crops to disk behind a `--debug` flag.
### M3: Matching and market data
- [x] Fetch an item from `https://api.warframe.market/v2/item/{slug}` with a TTL. Ignore forma blueprints.
- [x] Fuzzy-match OCR text with `rapidfuzz`, with a minimum score and an "unknown item" result below it.
- [x] Fetch plat prices and ducat values, with rate limiting and caching.
- [x] Slugifier fallback (lowercase, underscores, strip apostrophes, `&` to `and`).
### M4: Hotkey and app shell
- [x] Global hotkey via `pynput.keyboard.GlobalHotKeys`, configurable in `config.toml`.
- [x] Short delay (~0.5 s) after keypress so the reward screen has finished rendering.
- [x] Debounce repeated presses while a scan is running.
- [ ] Tray icon (`pystray`) with quit and status.
### M5: WebSocket backend
- [x] FastAPI server bound to `127.0.0.1` with a `/ws` endpoint.
- [x] Connection manager that broadcasts each scan result to all connected clients.
- [x] Message schema with a version field and message types: `scan_result`, `scan_started`, `error`, `status`.
- [x] Send the last result to a client when it connects, so a restarted overlay is not blank.
- [x] Heartbeat or ping so dead connections are dropped.
### M6: Tauri overlay (frontend)
- [ ] Scaffold a Tauri app with a small web UI (TypeScript).
- [ ] Transparent, borderless, always-on-top window that does not take focus from the game.
- [ ] Click-through by default (`set_ignore_cursor_events`), so the overlay never blocks mouse input to the game.
- [x] WebSocket client with automatic reconnect and backoff. Show a "backend disconnected" state.
- [ ] Render each reward slot: item name, plat price, ducat value, and a highlight on the best pick.
- [ ] Show low-confidence and unknown-item matches clearly instead of hiding them.
- [ ] Position the overlay near the reward slots, with offsets stored as screen fractions in config.
- [ ] Auto-hide after a configurable timeout and show again on the next scan.
- [ ] Optional: a small settings view for hotkey, position, and timeout.
- [ ] Optional: backend launches the overlay, or the overlay launches the backend as a sidecar.
### M7: Polish
- [ ] Config file for hotkey, resolution override, UI scale, OCR engine.
- [ ] Packaging (PyInstaller) and a short install guide.
- [ ] Re-check Warframe's current terms of service before distributing.
## Risks and open questions
 
- **Keybind layout:** backtick is a dead key or needs AltGr on some layouts, so the hotkey must be rebindable.
- **UI scale and aspect ratio:** ratios may not hold across every setting. Needs test screenshots for each.
- **Long names:** wrapping to two lines can break single-line OCR. Pad crops and test.
- **API limits:** warframe.market rate limits and schema changes. Cache aggressively and handle failures.
- **Borderless vs. fullscreen:** capture may fail in exclusive fullscreen, and an overlay cannot draw over it. Document borderless/windowed as required.
- **Overlay focus and click-through:** the overlay must not steal focus or block clicks. Test with the game in the foreground.
- **Multi-monitor and DPI:** overlay placement must handle scaling and the monitor the game is on.
- **Tauri window behavior differs by OS:** transparency and click-through need testing on each target platform.
- **WebSocket message schema:** keep it versioned so the backend and overlay can be updated independently.
- **Process lifecycle:** decide who starts and stops whom (backend, overlay, or a tray launcher).