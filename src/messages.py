"""WebSocket message schema — the single source of truth, version 1.

Every message is a JSON object with a "type" and a "version" field:

    scan_started: {"type": "scan_started", "version": 1}
    scan_result:  {"type": "scan_result", "version": 1,
                   "items": [{"name": str, "url_name": str|null,
                              "plat": int|null, "ducats": int|null,
                              "confidence": float, "known": bool}]}
    error:        {"type": "error", "version": 1, "message": str}
    status:       {"type": "status", "version": 1, "state": "idle"|"scanning"}

Unknown items have url_name null, no prices, and known false. The overlay
renders whatever it receives and must treat nulls as "not available".
Backend and overlay change together when this version bumps.
"""

VERSION = 1


def scan_started() -> dict:
    return {"type": "scan_started", "version": VERSION}


def scan_result(items: list[dict]) -> dict:
    return {"type": "scan_result", "version": VERSION, "items": items}


def error(message: str) -> dict:
    return {"type": "error", "version": VERSION, "message": message}


def status(state: str) -> dict:
    return {"type": "status", "version": VERSION, "state": state}