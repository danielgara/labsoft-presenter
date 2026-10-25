"""Global shortcuts and pointer buttons, observed without swallowing keys."""

from __future__ import annotations

import sys
import threading

try:
    from pynput import keyboard, mouse
except Exception:  # pragma: no cover - the dock still works without global hooks
    keyboard = None
    mouse = None

_LETTERS = {
    "h": "spotlight",
    "l": "laser",
    "z": "zoom",
    "m": "lens",
    "d": "draw",
    "t": "text",
    "p": "dock",
}

# ANSI virtual keycodes from HIToolbox/Events.h
_MAC_KEYS = {"h": 4, "l": 37, "z": 6, "m": 46, "d": 2, "t": 17, "p": 35}


def _codes(letter: str) -> tuple[int, ...]:
    """The key's vk as pynput reports it on each system."""
    if sys.platform == "darwin":
        return (_MAC_KEYS[letter],)
    if sys.platform == "win32":
        return (ord(letter.upper()),)  # Windows virtual-key codes
    return (ord(letter), ord(letter.upper()))  # X11 keysyms, lower and upper case


_SHORTCUTS = {code: action for letter, action in _LETTERS.items() for code in _codes(letter)}
_UNDO_KEYS = _codes("z")
_UNDO_HELD = {"cmd"} if sys.platform == "darwin" else {"ctrl"}


class Hotkeys:
    """Collects shortcuts on a background hook and hands them to the UI thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._down: set[str] = set()
        self._actions: list[str] = []
        self._scroll = 0.0
        self.alt = False
        self.ctrl = False
        self.left = False
        self.available = keyboard is not None and mouse is not None
        self._keys = None
        self._pointer = None

    def start(self) -> bool:
        if self._keys is not None:
            return True
        if not self.available:
            return False
        from presenter.cocoa import accessibility_trusted

        if not accessibility_trusted():
            return False
        try:
            self._keys = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self._keys.daemon = True
            self._keys.start()
            self._pointer = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
            self._pointer.daemon = True
            self._pointer.start()
        except Exception:
            self._keys = None
            self._pointer = None
            return False
        return True

    def stop(self) -> None:
        for listener in (self._keys, self._pointer):
            if listener is not None:
                listener.stop()

    def drain(self) -> tuple[list[str], int, bool, bool, bool]:
        with self._lock:
            actions = self._actions
            self._actions = []
            wheel = self._scroll
            self._scroll = 0.0
            alt = self.alt
            left = self.left
            ctrl = self.ctrl
        steps = 0
        if abs(wheel) >= 0.75:
            steps = 1 if wheel > 0 else -1
        return actions, steps, alt, left, ctrl

    def _on_press(self, key) -> None:
        token = self._token(key)
        if token is None:
            return
        with self._lock:
            if token in self._down:
                return
            self._down.add(token)
            self.alt = "alt" in self._down
            self.ctrl = "ctrl" in self._down
            action = self._action_for(token)
            if action:
                self._actions.append(action)

    def _on_release(self, key) -> None:
        token = self._token(key)
        if token is None:
            return
        with self._lock:
            self._down.discard(token)
            self.alt = "alt" in self._down
            self.ctrl = "ctrl" in self._down

    def _on_click(self, _x, _y, button, pressed) -> None:
        if mouse is None or button != mouse.Button.left:
            return
        with self._lock:
            self.left = bool(pressed)

    def _on_scroll(self, _x, _y, _dx, dy) -> None:
        with self._lock:
            self._scroll += float(dy)

    def _action_for(self, token: str) -> str | None:
        if token == "esc":
            return "escape"
        if not token.startswith("vk:"):
            return None
        try:
            code = int(token.split(":", 1)[1])
        except ValueError:
            return None
        if code in _UNDO_KEYS and self._down & {"cmd", "ctrl", "alt"} == _UNDO_HELD:
            return "undo"
        if "ctrl" in self._down and "alt" in self._down:
            return _SHORTCUTS.get(code)
        return None

    @staticmethod
    def _token(key) -> str | None:
        if keyboard is None:
            return None
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return "ctrl"
        if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return "alt"
        if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            return "cmd"
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            return "shift"
        if key == keyboard.Key.esc:
            return "esc"
        virtual = getattr(key, "vk", None)
        if virtual is not None:
            return f"vk:{virtual}"
        return None
