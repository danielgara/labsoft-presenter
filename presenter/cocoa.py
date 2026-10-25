"""Keep Presenter above slides, including fullscreen presentation spaces."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QWidget

_LEVEL: int | None = None


def screen_saver_level() -> int:
    global _LEVEL
    if _LEVEL is not None:
        return _LEVEL
    _LEVEL = 1000
    if sys.platform != "darwin":
        return _LEVEL
    try:
        from Quartz import CGWindowLevelForKey, kCGScreenSaverWindowLevelKey

        _LEVEL = int(CGWindowLevelForKey(kCGScreenSaverWindowLevelKey))
    except Exception:
        _LEVEL = 1000
    return _LEVEL


def set_native_level(widget: QWidget, level: int) -> None:
    """Drop or restore the Cocoa window level so a file dialog can appear in front."""
    if sys.platform != "darwin":
        return
    try:
        import objc

        view = objc.objc_object(c_void_p=int(widget.winId()))
        window = view.window()
        if window is not None:
            window.setLevel_(int(level))
    except Exception:
        return


def prepare_window(widget: QWidget, *, level_offset: int = 0, click_through: bool = False) -> None:
    if sys.platform != "darwin":
        return
    try:
        import objc
        from AppKit import (
            NSColor,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowCollectionBehaviorIgnoresCycle,
            NSWindowCollectionBehaviorStationary,
        )
    except Exception:
        return
    view = objc.objc_object(c_void_p=int(widget.winId()))
    window = view.window()
    if window is None:
        return
    window.setOpaque_(False)
    window.setBackgroundColor_(NSColor.clearColor())
    window.setHasShadow_(False)
    window.setLevel_(screen_saver_level() + level_offset)
    window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorFullScreenAuxiliary
        | NSWindowCollectionBehaviorIgnoresCycle
        | NSWindowCollectionBehaviorStationary
    )
    window.setHidesOnDeactivate_(False)
    window.setIgnoresMouseEvents_(bool(click_through))


def window_number(widget: QWidget) -> int | None:
    if sys.platform != "darwin" or not widget.isVisible():
        return None
    try:
        import objc

        view = objc.objc_object(c_void_p=int(widget.winId()))
        window = view.window()
        if window is None:
            return None
        return int(window.windowNumber())
    except Exception:
        return None


def activate_app() -> None:
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication

        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception:
        pass


def accessibility_trusted() -> bool:
    if sys.platform != "darwin":
        return True
    try:
        from ApplicationServices import AXIsProcessTrusted

        return bool(AXIsProcessTrusted())
    except Exception:
        return True


def request_accessibility() -> None:
    if sys.platform != "darwin":
        return
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

        AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except Exception:
        pass


_CURSOR_HIDDEN = False


def set_system_cursor_hidden(hidden: bool) -> None:
    """Hide the arrow so the laser glow can be the pointer."""
    global _CURSOR_HIDDEN
    if sys.platform != "darwin" or hidden == _CURSOR_HIDDEN:
        return
    try:
        from AppKit import NSCursor

        if hidden:
            NSCursor.hide()
        else:
            NSCursor.unhide()
        _CURSOR_HIDDEN = hidden
    except Exception:
        return


def request_screen_recording() -> None:
    if sys.platform != "darwin":
        return
    try:
        from Quartz import CGRequestScreenCaptureAccess

        CGRequestScreenCaptureAccess()
    except Exception:
        pass


class FloatingWindow(QWidget):
    """Frameless translucent window that can float over a fullscreen slide."""

    level_offset = 2

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._click_through = False
        self._input_cut = False
        self._owner: QWidget | None = None

    def keep_above(self, owner: QWidget) -> None:
        """Stay above owner on Windows, as window levels do on macOS.

        Windows brings a clicked or activated window to the front, but always
        keeps an owned window above its owner.
        """
        if sys.platform != "win32":
            return
        self._owner = owner

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._sync_input()
        self._attach_owner()
        QTimer.singleShot(0, self.apply_native)
        if sys.platform not in ("darwin", "win32"):
            QTimer.singleShot(250, self._reshape_frame)

    def _reshape_frame(self) -> None:
        """Have the window manager's frame take on the stage's input shape.

        Openbox and xfwm4 wrap each mapped window in a frame of their own and
        copy the input shape to it only when it changes after framing, so a
        stage mapped click-through would still catch every click.
        """
        handle = self.windowHandle()
        if not self.isVisible() or not self._click_through or handle is None:
            return
        handle.setFlag(Qt.WindowType.WindowTransparentForInput, False)
        handle.setFlag(Qt.WindowType.WindowTransparentForInput, True)

    def _attach_owner(self) -> None:
        if self._owner is None:
            return
        self._owner.winId()
        handle = self.windowHandle()
        owner = self._owner.windowHandle()
        if handle is not None and owner is not None and handle.transientParent() is not owner:
            handle.setTransientParent(owner)

    def apply_native(self) -> None:
        prepare_window(self, level_offset=self.level_offset, click_through=self._click_through)
        self._sync_input()

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = enabled
        self._sync_input()
        if self.isVisible():
            self.apply_native()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        handle = self.windowHandle()
        if self._input_cut and not self._click_through and handle is not None:
            # Qt fixes the input shape to the size the window had when clicks came back.
            handle.setFlag(Qt.WindowType.WindowTransparentForInput, True)
            handle.setFlag(Qt.WindowType.WindowTransparentForInput, False)

    def _sync_input(self) -> None:
        """Let clicks fall through on X11, where even clear pixels take them."""
        if sys.platform in ("darwin", "win32"):
            return
        handle = self.windowHandle()
        flag = Qt.WindowType.WindowTransparentForInput
        if handle is not None and bool(handle.flags() & flag) != self._click_through:
            handle.setFlag(flag, self._click_through)
            self._input_cut = True
