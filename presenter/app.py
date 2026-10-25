"""Wires the tool bar, the stage, the magnifier, and the shortcuts."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QSettings, QTimer
from PyQt6.QtGui import QAction, QCursor, QGuiApplication, QIcon, QKeySequence
from PyQt6.QtWidgets import QApplication, QMenu, QMenuBar, QSystemTrayIcon

from presenter.capture import screen_recording_allowed
from presenter.cocoa import (
    accessibility_trusted,
    request_accessibility,
    request_screen_recording,
    set_system_cursor_hidden,
    window_number,
)
from presenter.dock import Dock, Guide
from presenter.hotkeys import Hotkeys
from presenter.icons import tray_pixmap
from presenter.lens import Lens
from presenter.model import Document
from presenter.overlay import Overlay

_MODES = ("laser", "spotlight", "lens", "draw", "text")
_SHAPES = ("pen", "marker", "line", "arrow", "rect", "ellipse")


class Presenter(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.document = Document()
        self.overlay = Overlay(self.document)
        self.lens = Lens()
        self.dock = Dock()
        self.guide = Guide()
        self.dock.keep_above(self.overlay)
        self.guide.keep_above(self.dock)
        self.overlay.keep_clear([self.dock, self.guide])
        self.hotkeys = Hotkeys()
        self._last = None
        self._esc_lock = False
        self._undo_lock = False
        self._capturing = False
        self._zoom_screen = None
        self._lens_tick = 0
        self._keys_on = False
        self._key_wait = 0
        self._tick = QTimer(self)
        self._tick.setInterval(40)
        self._tick.timeout.connect(self._on_tick)
        self.overlay.changed.connect(self.sync)
        self.overlay.escapeRequested.connect(self._escape)
        self.overlay.undoRequested.connect(self._undo)
        self.dock.action.connect(self.on_action)
        self.dock.colorPicked.connect(self.overlay.set_color)
        self.dock.widthChanged.connect(self.overlay.set_width)
        self.dock.dimChanged.connect(self.overlay.set_dim)
        self._tray: QSystemTrayIcon | None = None
        self._menu: QMenuBar | None = None
        self._build_tray()
        self._build_menu()

    def start(self) -> None:
        self._keys_on = False
        self._ensure_hotkeys()
        self._tick.start()
        self.sync()
        self.dock.place_initial()
        self.dock.show()
        self._raise_chrome()
        if self._tray is not None:
            self._tray.show()
        if not accessibility_trusted():
            request_accessibility()
        settings = QSettings()
        seen = settings.value("guideShown", 0)
        try:
            seen = int(seen)
        except (TypeError, ValueError):
            seen = 1 if seen else 0
        if not seen:
            settings.setValue("guideShown", 1)
            self._show_guide()

    def on_action(self, name: str) -> None:
        if self._capturing:
            return
        if name == "quit":
            set_system_cursor_hidden(False)
            QApplication.quit()
            return
        if name == "hide":
            self.dock.collapse()
            return
        if name == "dock":
            self.dock.toggle_collapsed()
            return
        if name == "help":
            self._show_guide()
            return

        self.dock.expand()
        if name not in ("nudge-up", "nudge-down", "undo", "clear"):
            self.guide.hide()
        if self.overlay.picking_zoom and name != "zoom" and not name.startswith("zoom-screen-"):
            self.overlay.picking_zoom = False

        if name == "done":
            self.overlay.exit_mode()
        elif name == "undo":
            self.overlay.undo()
        elif name == "clear":
            self.overlay.clear()
        elif name == "frame":
            if self.overlay.mode != "spotlight":
                self.overlay.set_mode("spotlight")
            self.overlay.toggle_frame()
        elif name == "pan":
            if self.overlay.mode != "zoom":
                self._begin_zoom()
                return
            self.overlay.set_shape("pan")
        elif name.startswith("zoom-screen-") and name.removeprefix("zoom-screen-").isdigit():
            index = int(name.removeprefix("zoom-screen-"))
            screens = QGuiApplication.screens()
            if 0 <= index < len(screens):
                self._begin_zoom(screens[index])
                return
        elif name == "ink-text":
            if self.overlay.mode == "zoom":
                self.overlay.set_shape("text")
            else:
                self._enter("text")
        elif name in _SHAPES:
            if self.overlay.mode != "zoom":
                if self.overlay.mode != "draw":
                    self.overlay.set_mode("draw")
            self.overlay.set_shape(name)
        elif name == "zoom":
            if self.overlay.mode == "zoom":
                self.overlay.exit_mode()
            elif len(QGuiApplication.screens()) > 1:
                self.overlay.picking_zoom = not self.overlay.picking_zoom
            else:
                self._begin_zoom(QApplication.primaryScreen())
                return
        elif name in _MODES:
            self._enter(name)
        elif name == "nudge-up":
            self.overlay.nudge(1)
        elif name == "nudge-down":
            self.overlay.nudge(-1)

        self._sync_lens()
        self.sync()
        self._raise_chrome()

    def sync(self) -> None:
        state = self.overlay.ui_state()
        if state == self._last:
            return
        self._last = state
        self.dock.apply(state)
        self._sync_laser_cursor()
        interval = 16 if state.mode != "idle" else 40
        if self._tick.interval() != interval:
            self._tick.setInterval(interval)

    def _ensure_hotkeys(self) -> None:
        if self._keys_on:
            return
        self._keys_on = self.hotkeys.start()

    def _enter(self, mode: str) -> None:
        if self.overlay.mode == mode:
            self.overlay.exit_mode()
        else:
            self.overlay.set_mode(mode)

    def _begin_zoom(self, screen=None) -> None:
        self.overlay.picking_zoom = False
        if not screen_recording_allowed():
            request_screen_recording()
            self.overlay.notify("Permite Grabación de pantalla, cierra Presenter y ábrelo de nuevo.")
            self.sync()
            return
        if screen is None:
            screen = QGuiApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self._zoom_screen = screen
        self._capturing = True
        self.guide.hide()
        self.lens.hide()
        self.dock.hide()
        self.overlay.hide()
        QApplication.processEvents()
        QTimer.singleShot(160, self._finish_zoom)

    def _finish_zoom(self) -> None:
        self._capturing = False
        screen = self._zoom_screen
        self._zoom_screen = None
        captured = self.overlay.capture_and_zoom(screen)
        if not captured:
            request_screen_recording()
            self.overlay.notify("No se pudo capturar la pantalla. Permite Grabación de pantalla, cierra Presenter y ábrelo de nuevo.")
            self.overlay.sync_visibility()
        self._sync_lens()
        self.dock.show()
        self.sync()
        self._raise_chrome()

    def _escape(self) -> None:
        if self._esc_lock or self._capturing:
            return
        self._esc_lock = True
        QTimer.singleShot(60, self._unlock_escape)
        if self.overlay.mode == "idle" and not self.overlay.editor_open() and self.guide.isVisible():
            self.guide.hide()
            return
        self.overlay.handle_escape()
        self._sync_lens()
        self.sync()
        self._raise_chrome()

    def _undo(self) -> None:
        if self._undo_lock or self._capturing:
            return
        if self.overlay.mode not in ("draw", "text", "zoom", "spotlight"):
            return
        self._undo_lock = True
        QTimer.singleShot(60, self._unlock_undo)
        self.overlay.undo()
        self.sync()

    def _unlock_escape(self) -> None:
        self._esc_lock = False

    def _unlock_undo(self) -> None:
        self._undo_lock = False

    def _on_tick(self) -> None:
        if self._capturing:
            return
        if not self._keys_on:
            self._key_wait += 1
            if self._key_wait >= 50:
                self._key_wait = 0
                self._ensure_hotkeys()
        actions, steps, alt, left, ctrl = self.hotkeys.drain()
        for action in actions:
            if action == "escape":
                self._escape()
            elif action == "undo":
                self._undo()
            else:
                self.on_action(action)
        if self._capturing:
            return
        if self.overlay.mode != "idle" or self.overlay.editor_open():
            self.overlay.pointer_tick(steps, alt, left, ctrl)
        self._sync_laser_cursor()
        if self.overlay.mode == "lens":
            self._lens_tick += 1
            if self._lens_tick % 3 == 0:
                if not self.lens.isVisible():
                    self.lens.show()
                self.lens.refresh(self.overlay.lens_power, self._below_id())
                self._raise_chrome()

    def _sync_laser_cursor(self) -> None:
        if self.overlay.mode != "laser":
            set_system_cursor_hidden(False)
            return
        pos = QCursor.pos()
        over_chrome = self.dock.frameGeometry().contains(pos)
        if self.guide.isVisible() and self.guide.frameGeometry().contains(pos):
            over_chrome = True
        set_system_cursor_hidden(not over_chrome)

    def _sync_lens(self) -> None:
        if self.overlay.mode == "lens":
            self.lens.show()
            self.lens.apply_native()
            self.lens.refresh(self.overlay.lens_power, self._below_id())
        elif self.lens.isVisible():
            self.lens.hide()

    def _below_id(self) -> int | None:
        for widget in (self.overlay, self.lens, self.dock):
            if widget.isVisible():
                number = window_number(widget)
                if number:
                    return number
        return None

    def _raise_chrome(self) -> None:
        self.dock.raise_()
        self.dock.apply_native()
        if self.guide.isVisible():
            self.guide.raise_()
            self.guide.apply_native()

    def _show_guide(self) -> None:
        self.dock.expand()
        self.guide.present_over(self.dock)
        self.guide.apply_native()

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self)
        tray.setIcon(QIcon(tray_pixmap()))
        tray.setToolTip("Presenter")
        menu = QMenu()
        menu.addAction("Mostrar herramientas", lambda: self.dock.expand())
        menu.addAction("Atajos", self._show_guide)
        menu.addSeparator()
        for label, action in (
            ("Resaltar", "spotlight"),
            ("Láser", "laser"),
            ("Zoom", "zoom"),
            ("Dibujar", "draw"),
            ("Escribir", "text"),
        ):
            menu.addAction(label, lambda _checked=False, name=action: self.on_action(name))
        menu.addSeparator()
        menu.addAction("Salir de Presenter", lambda: QApplication.quit())
        tray.setContextMenu(menu)
        tray.activated.connect(self._tray_activated)
        self._tray = tray
        self._tray_menu = menu

    def _tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.dock.expand()
            self._raise_chrome()

    def _build_menu(self) -> None:
        menu = QMenuBar()
        app_menu = menu.addMenu("Presenter")
        app_menu.addAction("Mostrar herramientas", lambda: self.dock.expand())
        app_menu.addAction("Atajos", self._show_guide)
        app_menu.addSeparator()
        quit_action = QAction("Salir de Presenter", menu)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(QApplication.quit)
        app_menu.addAction(quit_action)
        self._menu = menu
        QApplication.instance().aboutToQuit.connect(self.hotkeys.stop)
        QApplication.instance().aboutToQuit.connect(lambda: set_system_cursor_hidden(False))
