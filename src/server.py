"""FastAPI server bound to 127.0.0.1 with a /ws broadcast endpoint."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from . import messages


class Broadcaster:
    """Tracks connected overlays and broadcasts messages from any thread."""

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.last_result: dict[str, Any] | None = None

    def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to every client; safe to call from the scan thread."""
        if message.get("type") == "scan_result":
            self.last_result = message
        if self.loop is not None:
            asyncio.run_coroutine_threadsafe(self._send_all(message), self.loop)

    async def _send_all(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for client in self.clients:
            try:
                await client.send_json(message)
            except Exception:
                dead.append(client)
        self.clients.difference_update(dead)


def create_app(broadcaster: Broadcaster) -> FastAPI:
    # uvicorn pings websockets by default, so dead connections get dropped.

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # The scan thread broadcasts through this loop.
        broadcaster.loop = asyncio.get_running_loop()
        yield
        broadcaster.loop = None

    app = FastAPI(lifespan=lifespan)

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        broadcaster.clients.add(websocket)
        if broadcaster.last_result:
            await websocket.send_json(broadcaster.last_result)
        else:
            await websocket.send_json(messages.status("idle"))
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            broadcaster.clients.discard(websocket)

    return app