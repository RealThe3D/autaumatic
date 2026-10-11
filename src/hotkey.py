"""Global hotkey listener. The callback must stay non-blocking; it only queues work."""

import logging

from pynput import keyboard

logger = logging.getLogger(__name__)


def start(combo: str, on_trigger: callable) -> keyboard.GlobalHotKeys:
    """Start listening for the configured combo. on_trigger must return immediately."""

    def on_press() -> None:
        logger.info("Hotkey pressed")
        on_trigger()

    listener = keyboard.GlobalHotKeys({combo: on_press})
    listener.start()
    return listener