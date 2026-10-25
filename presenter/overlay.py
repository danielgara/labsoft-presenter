"""Fullscreen stage: spotlight, zoom, laser, drawing, and type."""

from __future__ import annotations

import sys

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QRectF,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QGuiApplication,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
    QRegion,
)
from PyQt6.QtWidgets import QApplication, QFrame, QTextEdit, QWidget

from presenter.capture import capture_screen
from presenter.cocoa import FloatingWindow, activate_app
from presenter.ink import measure_note, paint_frame, paint_note, paint_stroke
from presenter.model import Document, Frame, Note, Stroke, UiState, dist
from presenter.theme import ACCENT, DOCK_SHADOW, PALETTE

_DRAW_SHAPES = ("pen", "marker", "line", "arrow", "rect", "ellipse", "eraser")
# Windows sends clicks on fully transparent pixels to the window below, so a
# stage that takes the pen keeps an invisible film to receive them.
_HIT_FILL = QColor(0, 0, 0, 1) if sys.platform == "win32" else QColor(Qt.GlobalColor.transparent)
_HINTS = {
    "idle": "Resalta, amplía y escribe sobre la diapositiva",
    "laser": "La luz es el puntero",
    "spotlight": "Pulsa Marco y arrastra alrededor de un elemento  ·  ⌥ y arrastrar también enmarca",
    "zoom": "Muévete en esta pantalla para mirar  ·  doble clic pasa al lápiz  ·  desplázate para ampliar",
    "lens": "Una lupa sigue al puntero  ·  + y − cambian la potencia",
    "draw": "La tinta permanece al salir  ·  ⌘Z deshace",
    "text": "Haz clic donde debe ir el texto y escribe  ·  Enter lo coloca",
}


def _is_tap(points: list[QPointF]) -> bool:
    if len(points) <= 1:
        return True
    return max(dist(points[0], point) for point in points) < 6


class _CaretBar(QWidget):
    """Gold insertion mark. The native caret never reaches a translucent window."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.hide()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(12, 12, 14))
        painter.drawRect(self.rect())
        painter.setBrush(ACCENT)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        painter.end()


class InkEditor(QTextEdit):
    commitRequested = pyqtSignal()
    cancelRequested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        self.document().setDocumentMargin(0)
        self.setCursorWidth(0)
        self.setMinimumSize(8, 8)
        self._caret_on = True
        self._caret_timer = QTimer(self)
        self._caret_timer.timeout.connect(self._toggle_caret)
        self._caret_bar = _CaretBar(self.viewport())
        self.cursorPositionChanged.connect(self._wake_caret)
        self.hide()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.commitRequested.emit()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancelRequested.emit()
            return
        if event.key() == Qt.Key.Key_Tab:
            return
        super().keyPressEvent(event)
        self.fit()
        self._sync_caret()

    def fit(self) -> None:
        sample = self.toPlainText() or " "
        rect = self.fontMetrics().boundingRect(0, 0, 680, 480, int(Qt.TextFlag.TextDontClip), sample)
        self.setFixedWidth(max(20, min(680, rect.width() + 8)))
        self.setFixedHeight(max(self.fontMetrics().height() + 4, min(360, rect.height() + 6)))
        self._sync_caret()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._wake_caret()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._caret_timer.stop()
        super().hideEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        self._wake_caret()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        self._caret_on = False
        self._caret_timer.stop()
        super().focusOutEvent(event)
        self.viewport().update()

    def _sync_caret(self) -> None:
        rect = self.cursorRect()
        if rect.height() >= 2:
            self._caret_bar.setGeometry(max(0, rect.x()), rect.y(), 4, rect.height())
        show = self._caret_on and self.hasFocus() and self.isVisible() and rect.height() >= 2
        self._caret_bar.setVisible(show)
        if show:
            self._caret_bar.raise_()

    def _wake_caret(self) -> None:
        self._caret_on = True
        flash = QApplication.cursorFlashTime()
        self._caret_timer.setInterval(max(280, flash // 2))
        if self.isVisible():
            self._caret_timer.start()
        self._sync_caret()

    def _toggle_caret(self) -> None:
        self._caret_on = not self._caret_on
        self._sync_caret()


def _screen_key(screen) -> tuple[int, int, int, int]:
    geo = screen.geometry()
    return (geo.x(), geo.y(), geo.width(), geo.height())


def _ink_hits(document: Document, screen) -> bool:
    area = QRectF(screen.geometry())
    for stroke in document.strokes:
        if any(area.contains(point) for point in stroke.points):
            return True
    for note in document.notes:
        rect = QRectF(note.origin, note.bounds.size())
        if rect.intersects(area):
            return True
    for frame in document.frames:
        if QRectF(frame.rect).intersects(area):
            return True
    return False


def _paint_ink(painter: QPainter, document: Document, origin: QPointF) -> None:
    def local(point: QPointF) -> QPointF:
        return QPointF(point.x() - origin.x(), point.y() - origin.y())

    for stroke in document.strokes:
        paint_stroke(painter, stroke, [local(point) for point in stroke.points], 1.0)
    for note in document.notes:
        paint_note(painter, note, local(note.origin), 1.0)
    for frame in document.frames:
        rect = frame.rect
        paint_frame(painter, QRectF(local(rect.topLeft()), local(rect.bottomRight())).normalized(), 1.0)


class InkSheet(FloatingWindow):
    """Click-through copy of the ink left on a screen the pointer has left."""

    level_offset = -1

    def __init__(self, document: Document) -> None:
        super().__init__()
        self.doc = document
        self.origin = QPointF()
        self.set_click_through(True)
        self.hide()

    def place(self, screen) -> None:
        geo = screen.geometry()
        self.winId()
        handle = self.windowHandle()
        if handle is not None and handle.screen() is not screen:
            handle.setScreen(screen)
        self.setGeometry(geo)
        self.origin = QPointF(geo.topLeft())

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        _paint_ink(painter, self.doc, self.origin)
        painter.end()


class Overlay(FloatingWindow):
    changed = pyqtSignal()
    escapeRequested = pyqtSignal()
    undoRequested = pyqtSignal()

    level_offset = 0

    def __init__(self, document: Document) -> None:
        super().__init__()
        self.doc = document
        self.mode = "idle"
        self.picking_zoom = False
        self.shape = "pen"
        self.inking = False
        self.framing = False
        self.zoom = 2.0
        self.lens_power = 2.5
        self.dim = 0.62
        self.radius = 180.0
        self.stroke_width = 3.5
        self.text_size = 36
        self.color = QColor(PALETTE[0])
        self._message = ""
        self._message_gen = 0
        self.shot: QPixmap | None = None
        self.view_center = QPointF()
        self.origin = QPointF()
        self._screen = None
        self.space_held = False
        self._live_points: list[QPointF] = []
        self._live_frame: QRectF | None = None
        self._frame_origin: QPointF | None = None
        self._option_dragging = False
        self._erasing = False
        self._click_token = 0
        self._last_cursor = QPoint()
        self._hover = QPointF()
        self._editor_anchor: QPointF | None = None
        self._anim = None
        self.editor = InkEditor(self)
        self.editor.commitRequested.connect(self._commit_editor)
        self.editor.cancelRequested.connect(self.escapeRequested.emit)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._blank = self._make_blank_cursor()
        self._sheets: dict[tuple[int, int, int, int], InkSheet] = {}
        self._clear: list[QWidget] = []
        self.changed.connect(self._sync_sheets)
        self.hide()

    def keep_clear(self, widgets: list[QWidget]) -> None:
        """Leave a hole over the tool bar and guide on X11.

        X11 hands the stage every click inside it, even on clear pixels, and
        the window manager may stack it above the bar. A hole in its shape
        sends those clicks to the bar below, whatever the stacking.
        """
        if sys.platform in ("darwin", "win32"):
            return
        self._clear = list(widgets)
        for widget in self._clear:
            widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched in self._clear and event.type() in (
            QEvent.Type.Move,
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
        ):
            self._sync_hole()
        return super().eventFilter(watched, event)

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._sync_hole()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_hole()

    def _sync_hole(self) -> None:
        if not self._clear:
            return
        left, top, right, bottom = DOCK_SHADOW
        region = QRegion(self.rect())
        for widget in self._clear:
            if widget.isVisible():
                glass = widget.geometry().adjusted(left, top, -right, -bottom)
                region -= QRegion(glass.translated(-self.geometry().topLeft()))
        if region == QRegion(self.rect()):
            self.clearMask()
        else:
            self.setMask(region)

    def ui_state(self) -> UiState:
        return UiState(
            mode=self.mode,
            shape=self.shape,
            inking=self.inking,
            framing=self.framing,
            zoom=self.zoom,
            lens_power=self.lens_power,
            dim=self.dim,
            radius=self.radius,
            width=self.stroke_width,
            text_size=self.text_size,
            color=self.color.name().upper(),
            can_undo=self.doc.can_undo(),
            hint=self._hint(),
            message=self._message,
            picking_zoom=self.picking_zoom,
        )

    def editor_open(self) -> bool:
        return self.editor.isVisible()

    def notify(self, text: str) -> None:
        self._message = text
        self._message_gen += 1
        generation = self._message_gen

        def clear() -> None:
            if self._message_gen == generation:
                self._message = ""
                self.changed.emit()

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(6400, clear)
        self.changed.emit()

    def set_mode(self, mode: str) -> None:
        self.picking_zoom = False
        self._stop_anim()
        self.shot = None
        self.mode = mode
        self.framing = False
        self._option_dragging = False
        self._live_points = []
        self._live_frame = None
        self._frame_origin = None
        if mode == "draw":
            self.inking = True
            if self.shape not in _DRAW_SHAPES:
                self.shape = "pen"
        elif mode == "text":
            self.inking = False
            self.shape = "text"
        else:
            self.inking = False
        if mode != "text":
            self._commit_editor()
        self._present()

    def exit_mode(self) -> None:
        self.picking_zoom = False
        self._stop_anim()
        self.shot = None
        self.mode = "idle"
        self.inking = False
        self.framing = False
        self.space_held = False
        if self._erasing:
            self._erasing = False
            self.doc.end_erase()
        self._option_dragging = False
        self._live_points = []
        self._live_frame = None
        self._frame_origin = None
        self._commit_editor()
        self._present()

    def capture_and_zoom(self, screen=None) -> bool:
        if screen is None:
            screen = QGuiApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return False
        shot = capture_screen(screen)
        if shot.isNull() or shot.width() < 2:
            return False
        self.picking_zoom = False
        self._stop_anim()
        self.place(screen)
        self.shot = shot
        geo = screen.geometry()
        cursor = QCursor.pos()
        if geo.contains(cursor):
            local = cursor - geo.topLeft()
            self.view_center = QPointF(float(local.x()), float(local.y()))
        else:
            self.view_center = QPointF(geo.width() / 2, geo.height() / 2)
        self.zoom = 1.0
        self.mode = "zoom"
        self.inking = False
        self.framing = False
        self.shape = "pan"
        self._live_points = []
        self._commit_editor()
        self.show()
        self._apply_interaction()
        self._animate_zoom()
        self.update()
        self.changed.emit()
        return True

    def sync_visibility(self) -> None:
        self._present()

    def handle_escape(self) -> None:
        if self.editor.isVisible():
            self._cancel_editor()
            self.changed.emit()
            return
        if self._live_points:
            self._live_points = []
            self.update()
            return
        if self._live_frame is not None or self.framing or self._option_dragging:
            self._live_frame = None
            self._frame_origin = None
            self._option_dragging = False
            self.framing = False
            self._apply_interaction()
            self.changed.emit()
            self.update()
            return
        if self.mode == "zoom" and self.inking:
            self.inking = False
            self.shape = "pan"
            self._apply_interaction()
            self.changed.emit()
            self.update()
            return
        if self.picking_zoom:
            self.picking_zoom = False
            self.changed.emit()
            return
        if self.mode != "idle":
            self.exit_mode()

    def set_shape(self, shape: str) -> None:
        self.shape = shape
        if self.mode == "zoom":
            self.inking = shape in _DRAW_SHAPES or shape == "text"
        self._update_cursor()
        self.changed.emit()
        self.update()

    def toggle_frame(self) -> None:
        if self.mode != "spotlight":
            self.set_mode("spotlight")
        self.framing = not self.framing
        if not self.framing:
            self._live_frame = None
            self._frame_origin = None
        self._apply_interaction()
        self.changed.emit()
        self.update()

    def set_color(self, color: QColor) -> None:
        self.color = QColor(color)
        self._style_editor()
        self.changed.emit()

    def set_width(self, width: float) -> None:
        self.stroke_width = min(18.0, max(1.2, width))
        self.changed.emit()
        self.update()

    def set_dim(self, dim: float) -> None:
        self.dim = min(0.84, max(0.22, dim))
        self.changed.emit()
        self.update()

    def nudge(self, direction: int) -> None:
        if self.mode == "zoom":
            anchor = self._hover if not self._hover.isNull() else QPointF(self.width() / 2, self.height() / 2)
            self._set_zoom(self.zoom * (1.18 ** direction), anchor)
        elif self.mode == "lens":
            self.lens_power = min(6.0, max(1.4, self.lens_power * (1.16 ** direction)))
        elif self.mode == "spotlight":
            self.radius = min(520.0, max(48.0, self.radius + direction * 24))
            self.update()
        elif self.mode == "text":
            self.text_size = int(min(96, max(16, self.text_size + direction * 4)))
            self._style_editor()
            self._reposition_editor()
        elif self.mode == "draw":
            self.stroke_width = min(18.0, max(1.2, self.stroke_width + direction))
            self.update()
        self.changed.emit()

    def undo(self) -> None:
        self.doc.undo()
        self.update()
        self.changed.emit()

    def clear(self) -> None:
        self.doc.clear()
        self.update()
        self.changed.emit()

    def pointer_tick(self, steps: int, alt: bool, left: bool, ctrl: bool) -> None:
        pos = QCursor.pos()
        moved = pos != self._last_cursor
        self._last_cursor = pos
        self._follow_screen(pos)
        if self.mode == "zoom":
            buttons = Qt.MouseButton.LeftButton if left else Qt.MouseButton.NoButton
            self._track_zoom_pointer(buttons)
            return
        if self.mode == "laser":
            self._track_laser(pos, moved)
            return
        if self.mode == "spotlight":
            self._track_option_frame(pos, alt, left)
            if steps and ctrl and not self.captures_mouse():
                self.radius = min(520.0, max(48.0, self.radius + steps * 22))
                self.changed.emit()
            if moved or self._option_dragging:
                self.update()
            return
        if self.mode == "lens" and steps and ctrl:
            self.nudge(steps)

    def place(self, screen) -> None:
        self._screen = screen
        geo = screen.geometry()
        self.winId()
        handle = self.windowHandle()
        if handle is not None and handle.screen() is not screen:
            handle.setScreen(screen)
        self.setGeometry(geo)
        self.origin = QPointF(geo.topLeft())

    def captures_mouse(self) -> bool:
        if self.mode in ("draw", "text", "zoom"):
            return True
        return self.framing

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), _HIT_FILL if self.captures_mouse() else Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self.mode == "zoom" and self.shot is not None and not self.shot.isNull():
            self._paint_zoom(painter)
        if self.mode == "spotlight":
            self._paint_spotlight(painter)

        scale = self._ink_scale()
        for stroke in self.doc.strokes:
            paint_stroke(painter, stroke, [self.global_to_widget(point) for point in stroke.points], scale)
        if self._live_points:
            preview = Stroke(self.shape, QColor(self.color), self.stroke_width, list(self._live_points))
            if preview.kind != "eraser":
                paint_stroke(painter, preview, [self.global_to_widget(point) for point in preview.points], scale)
        for note in self.doc.notes:
            paint_note(painter, note, self.global_to_widget(note.origin), scale)
        for frame in self._all_frames():
            paint_frame(painter, self._map_rect(frame), scale)
        if self.mode == "laser":
            self._paint_laser(painter)
        if self.mode == "zoom":
            self._paint_crosshair(painter)
        if self._can_draw() and self.shape == "eraser":
            self._paint_eraser(painter, scale)
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self._live_points = []
            self.update()
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press(event.position())
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if self.mode != "zoom" or event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        self._cancel_click_commit()
        self._live_points = []
        if self.editor.isVisible():
            self._commit_editor()
        if self.shape == "pen" and self.inking:
            self.set_shape("pan")
        else:
            self.set_shape("pen")
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        self._hover = pos
        if self.mode == "zoom" and self._should_pan(event.buttons()):
            self._track_zoom_pointer(event.buttons())
            event.accept()
            return
        global_pos = self.widget_to_global(pos)
        if self._erasing and event.buttons() & Qt.MouseButton.LeftButton:
            self.doc.erase_at(global_pos, self._eraser_radius())
            self.update()
            return
        if self._live_points and event.buttons() & Qt.MouseButton.LeftButton:
            self._extend_live(global_pos)
            self.update()
            return
        if self._frame_origin is not None and self.framing and event.buttons() & Qt.MouseButton.LeftButton:
            self._live_frame = QRectF(self._frame_origin, global_pos).normalized()
            self.update()
            return
        if self.shape == "eraser" and self._can_draw():
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._erasing:
            self._erasing = False
            self.doc.end_erase()
            self.changed.emit()
            self.update()
            return
        if self._live_points:
            if self.mode == "zoom" and _is_tap(self._live_points):
                self._arm_click_commit()
                return
            self._commit_stroke()
            return
        if self.framing and self._frame_origin is not None:
            self._commit_live_frame()
            self.framing = False
            self._apply_interaction()
            self.changed.emit()
            self.update()

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.pixelDelta().y()
        if delta == 0:
            return
        steps = delta / 120.0 if abs(delta) >= 40 else delta / 48.0
        if self.mode == "zoom":
            self._set_zoom(self.zoom * (1.12 ** steps), event.position())
            self._reposition_editor()
        elif self.mode == "spotlight":
            self.radius = min(520.0, max(48.0, self.radius + steps * 18))
            self.update()
        elif self.mode == "draw":
            self.stroke_width = min(18.0, max(1.2, self.stroke_width + steps * 0.8))
            self.update()
        elif self.mode == "text":
            self.text_size = int(min(96, max(16, self.text_size + steps * 4)))
            self._style_editor()
            self._reposition_editor()
        else:
            return
        self.changed.emit()
        event.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.escapeRequested.emit()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undoRequested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space_held = True
            self._update_cursor()
            event.accept()
            return
        digit = event.text()
        if digit in {"1", "2", "3", "4", "5", "6"} and self.mode in ("draw", "text", "zoom"):
            self.set_color(QColor(PALETTE[int(digit) - 1]))
            event.accept()
            return
        if event.key() in (Qt.Key.Key_BracketLeft, Qt.Key.Key_Minus):
            self.nudge(-1)
            event.accept()
            return
        if event.key() in (Qt.Key.Key_BracketRight, Qt.Key.Key_Equal):
            self.nudge(1)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space_held = False
            self._update_cursor()
        super().keyReleaseEvent(event)

    def _hint(self) -> str:
        if self.picking_zoom:
            return "Elige la pantalla donde quieres ampliar"
        if self.mode == "spotlight" and self.framing:
            return "Arrastra alrededor del elemento que quieres mostrar"
        if self.mode == "zoom" and self.inking and self.shape == "text":
            return "Haz clic en la diapositiva ampliada y escribe  ·  mantén Espacio para mirar"
        if self.mode == "zoom" and self.inking and self.shape == "pen":
            return "Dibuja con el lápiz  ·  doble clic vuelve a mover"
        if self.mode == "zoom" and self.inking:
            return "Dibuja sobre la diapositiva ampliada  ·  mantén Espacio para mirar"
        return _HINTS.get(self.mode, _HINTS["idle"])

    def _present(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        needed = self.mode in ("laser", "spotlight", "zoom", "draw", "text") or self.doc.has_ink
        if self.mode == "lens":
            needed = self.doc.has_ink
        if self.mode == "zoom" and (self.shot is None or self.shot.isNull()):
            needed = self.doc.has_ink
        if needed and screen is not None:
            if self.mode != "zoom" or self.shot is None:
                self.place(screen)
            if not self.isVisible():
                self.show()
            self._apply_interaction()
            self.update()
        else:
            self.hide()
        self.changed.emit()

    def _sync_sheets(self) -> None:
        screens = QGuiApplication.screens()
        live = {_screen_key(screen): screen for screen in screens}
        for key in list(self._sheets):
            if key not in live:
                self._sheets.pop(key).hide()
        covered = _screen_key(self._screen) if self.isVisible() and self._screen is not None else None
        for key, screen in live.items():
            show = self.doc.has_ink and key != covered and _ink_hits(self.doc, screen)
            sheet = self._sheets.get(key)
            if not show:
                if sheet is not None and sheet.isVisible():
                    sheet.hide()
                continue
            if sheet is None:
                sheet = InkSheet(self.doc)
                self._sheets[key] = sheet
            sheet.place(screen)
            if not sheet.isVisible():
                sheet.show()
            sheet.apply_native()
            sheet.update()

    def _apply_interaction(self) -> None:
        capture = self.captures_mouse()
        self.set_click_through(not capture)
        if capture:
            activate_app()
            self.raise_()
            self.activateWindow()
            self.setFocus(Qt.FocusReason.OtherFocusReason)
        self._update_cursor()

    def _update_cursor(self) -> None:
        if self.mode == "laser":
            self.setCursor(self._blank)
        elif self.mode == "zoom" and (not self.inking or self.space_held):
            self.setCursor(self._blank)
        elif self.mode == "text" or (self.inking and self.shape == "text"):
            self.setCursor(Qt.CursorShape.IBeamCursor)
        elif self.framing or (self._can_draw() and self.shape != "eraser"):
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif self._can_draw() and self.shape == "eraser":
            self.setCursor(self._blank)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _can_draw(self) -> bool:
        if self.mode == "draw":
            return self.shape in _DRAW_SHAPES
        return self.mode == "zoom" and self.inking and self.shape in _DRAW_SHAPES

    def _track_zoom_pointer(self, buttons) -> None:
        if not self._should_pan(buttons) or self._screen is None or self.shot is None:
            return
        cursor = QCursor.pos()
        geo = self._screen.geometry()
        if not geo.contains(cursor):
            return
        local = cursor - geo.topLeft()
        center = QPointF(float(local.x()), float(local.y()))
        if abs(center.x() - self.view_center.x()) < 0.5 and abs(center.y() - self.view_center.y()) < 0.5:
            return
        self.view_center = center
        self._hover = center
        self._reposition_editor()
        self.update()

    def _should_pan(self, buttons) -> bool:
        if self.mode != "zoom":
            return False
        if buttons & Qt.MouseButton.LeftButton and (self.shape == "text" or self.shape in _DRAW_SHAPES):
            return False
        if not self.inking or self.shape in ("pan", "text"):
            return True
        return self.space_held

    def _arm_click_commit(self) -> None:
        self._click_token += 1
        token = self._click_token
        QTimer.singleShot(QApplication.doubleClickInterval() + 40, lambda: self._finish_click(token))

    def _cancel_click_commit(self) -> None:
        self._click_token += 1

    def _finish_click(self, token: int) -> None:
        if token != self._click_token or not self._live_points:
            return
        self._commit_stroke()

    def _press(self, pos: QPointF) -> None:
        global_pos = self.widget_to_global(pos)
        editor_was_open = self.editor.isVisible()
        if editor_was_open:
            self._commit_editor()
        if self.mode == "text" or (self.mode == "zoom" and self.inking and self.shape == "text"):
            self._open_editor(global_pos, pos)
            return
        if self.framing and self.mode == "spotlight":
            self._frame_origin = global_pos
            self._live_frame = QRectF(global_pos, global_pos)
            self.update()
            return
        if not self._can_draw():
            return
        if self.shape == "eraser":
            self.doc.begin_erase()
            self._erasing = True
            self.doc.erase_at(global_pos, self._eraser_radius())
            self.update()
            return
        self._live_points = [global_pos]
        self.update()

    def _extend_live(self, global_pos: QPointF) -> None:
        if self.shape in ("line", "arrow", "rect", "ellipse"):
            if len(self._live_points) == 1:
                self._live_points.append(global_pos)
            else:
                self._live_points[-1] = global_pos
            return
        if self._live_points and dist(self._live_points[-1], global_pos) < 1.25:
            return
        self._live_points.append(global_pos)

    def _commit_stroke(self) -> None:
        points = list(self._live_points)
        self._live_points = []
        if not points:
            return
        if len(points) >= 2 and self.shape in ("line", "arrow", "rect", "ellipse"):
            if dist(points[0], points[-1]) < 4:
                self.update()
                return
        self.doc.add_stroke(Stroke(self.shape, QColor(self.color), self.stroke_width, points))
        self.changed.emit()
        self.update()

    def _commit_live_frame(self) -> None:
        rect = self._live_frame.normalized() if self._live_frame is not None else None
        self._live_frame = None
        self._frame_origin = None
        if rect is not None and rect.width() >= 8 and rect.height() >= 8:
            self.doc.add_frame(Frame(rect))

    def _eraser_radius(self) -> float:
        return max(16.0, self.stroke_width * 3.2)

    def _open_editor(self, anchor: QPointF, widget_pos: QPointF) -> None:
        self._editor_anchor = anchor
        self.editor.clear()
        self._style_editor()
        self.editor.move(int(widget_pos.x()), int(widget_pos.y()))
        self.editor.fit()
        self.editor.show()
        self.editor.raise_()
        self.editor.setFocus()

    def _commit_editor(self) -> None:
        if not self.editor.isVisible() and not self.editor.toPlainText().strip():
            self.editor.hide()
            return
        text = self.editor.toPlainText().strip()
        anchor = self._editor_anchor
        self.editor.hide()
        self.editor.clear()
        if not text or anchor is None:
            return
        bounds = measure_note(text, self.text_size)
        bounds.moveTopLeft(anchor)
        self.doc.add_note(Note(anchor, text, QColor(self.color), self.text_size, bounds))
        self._editor_anchor = None
        self.update()
        self.changed.emit()

    def _cancel_editor(self) -> None:
        self.editor.hide()
        self.editor.clear()
        self._editor_anchor = None
        self.update()

    def _style_editor(self) -> None:
        from PyQt6.QtGui import QTextCharFormat

        from presenter.ink import note_font

        size = max(12, int(round(self.text_size * self._ink_scale())))
        font = note_font(size)
        color = self.color.name()
        family = font.family().replace('"', "")
        self.editor.setStyleSheet(
            "QTextEdit, QTextEdit viewport {"
            "background: transparent;"
            f"color: {color};"
            f'font-family: "{family}";'
            f"font-size: {size}pt;"
            "font-weight: 500;"
            "border: none;"
            "padding: 0px;"
            "selection-background-color: rgba(231, 177, 90, 0.35);"
            "}"
        )
        self.editor.viewport().setStyleSheet("background: transparent;")
        self.editor.setFont(font)
        self.editor.document().setDefaultFont(font)
        fmt = QTextCharFormat()
        fmt.setFont(font)
        self.editor.setCurrentCharFormat(fmt)

    def _reposition_editor(self) -> None:
        if not self.editor.isVisible() or self._editor_anchor is None:
            return
        point = self.global_to_widget(self._editor_anchor)
        self._style_editor()
        self.editor.move(int(point.x()), int(point.y()))
        self.editor.fit()

    def _animate_zoom(self) -> None:
        from PyQt6.QtCore import QVariantAnimation

        self._stop_anim()
        anim = QVariantAnimation(self)
        anim.setStartValue(1.0)
        anim.setEndValue(2.0)
        anim.setDuration(230)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self._on_zoom_frame)
        anim.start()
        self._anim = anim

    def _on_zoom_frame(self, value) -> None:
        self.zoom = float(value)
        self.update()
        self.changed.emit()

    def _stop_anim(self) -> None:
        if self._anim is not None:
            self._anim.stop()
            self._anim = None

    def _set_zoom(self, zoom: float, anchor: QPointF) -> None:
        zoom = min(8.0, max(1.0, zoom))
        if self.shot is not None and not self.shot.isNull():
            src = self._source_rect()
            safe = max(self.zoom, 0.01)
            local_x = src.x() + anchor.x() / safe
            local_y = src.y() + anchor.y() / safe
            self.zoom = zoom
            self.view_center = QPointF(
                local_x - anchor.x() / zoom + self.width() / (2 * zoom),
                local_y - anchor.y() / zoom + self.height() / (2 * zoom),
            )
        else:
            self.zoom = zoom
        self._stop_anim()
        self.update()

    def _source_rect(self) -> QRectF:
        zoom = max(self.zoom, 1.0)
        src_w = self.width() / zoom
        src_h = self.height() / zoom
        shot_w, shot_h = self._shot_logical_size()
        x = self.view_center.x() - src_w / 2
        y = self.view_center.y() - src_h / 2
        x = min(max(0.0, x), max(0.0, shot_w - src_w))
        y = min(max(0.0, y), max(0.0, shot_h - src_h))
        return QRectF(x, y, min(src_w, shot_w), min(src_h, shot_h))

    def _shot_logical_size(self) -> tuple[float, float]:
        if self.shot is None or self.shot.isNull():
            return float(self.width()), float(self.height())
        ratio = self.shot.devicePixelRatio() or 1
        return self.shot.width() / ratio, self.shot.height() / ratio

    def _ink_scale(self) -> float:
        if self.mode == "zoom" and self.shot is not None and not self.shot.isNull():
            src = self._source_rect()
            if src.width() > 1:
                return self.width() / src.width()
        return 1.0

    def widget_to_global(self, pos: QPointF) -> QPointF:
        if self.mode == "zoom" and self.shot is not None and not self.shot.isNull():
            src = self._source_rect()
            scale = self.width() / src.width() if src.width() else 1
            return QPointF(self.origin.x() + src.x() + pos.x() / scale, self.origin.y() + src.y() + pos.y() / scale)
        return QPointF(self.origin.x() + pos.x(), self.origin.y() + pos.y())

    def global_to_widget(self, pos: QPointF) -> QPointF:
        local_x = pos.x() - self.origin.x()
        local_y = pos.y() - self.origin.y()
        if self.mode == "zoom" and self.shot is not None and not self.shot.isNull():
            src = self._source_rect()
            scale = self.width() / src.width() if src.width() else 1
            return QPointF((local_x - src.x()) * scale, (local_y - src.y()) * scale)
        return QPointF(local_x, local_y)

    def _map_rect(self, rect: QRectF) -> QRectF:
        return QRectF(self.global_to_widget(rect.topLeft()), self.global_to_widget(rect.bottomRight())).normalized()

    def _all_frames(self) -> list[QRectF]:
        frames = [frame.rect for frame in self.doc.frames]
        if self._live_frame is not None:
            frames.append(self._live_frame.normalized())
        return frames

    def _paint_zoom(self, painter: QPainter) -> None:
        src = self._source_rect()
        ratio = self.shot.devicePixelRatio() or 1
        source = QRectF(src.x() * ratio, src.y() * ratio, src.width() * ratio, src.height() * ratio)
        painter.drawPixmap(QRectF(self.rect()), self.shot, source)
        painter.fillRect(0, 0, self.width(), 2, QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 180))

    def _paint_spotlight(self, painter: QPainter) -> None:
        painter.save()
        dim = QColor(8, 7, 6, int(255 * self.dim))
        painter.fillRect(self.rect(), dim)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        center = self.global_to_widget(QPointF(self._last_cursor))
        gradient = QRadialGradient(center, self.radius)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 255))
        gradient.setColorAt(0.62, QColor(0, 0, 0, 230))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(center, self.radius, self.radius)
        for rect in self._all_frames():
            mapped = self._map_rect(rect)
            painter.setBrush(QColor(0, 0, 0, 255))
            radius = min(12.0, mapped.width() / 3, mapped.height() / 3)
            painter.drawRoundedRect(mapped, radius, radius)
        painter.restore()
        ring = QColor(ACCENT)
        ring.setAlpha(80)
        painter.setPen(QPen(ring, 1.25))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, self.radius * 0.86, self.radius * 0.86)

    def _paint_laser(self, painter: QPainter) -> None:
        cursor = self.global_to_widget(QPointF(QCursor.pos()))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 32, 32, 90))
        painter.drawEllipse(cursor, 18, 18)
        painter.setBrush(QColor(255, 48, 48, 235))
        painter.drawEllipse(cursor, 8, 8)
        painter.setBrush(QColor(255, 170, 170))
        painter.drawEllipse(cursor, 3.2, 3.2)

    def _paint_crosshair(self, painter: QPainter) -> None:
        if self.inking and not self.space_held:
            return
        center = QPointF(self.width() / 2, self.height() / 2)
        gap, arm = 5.0, 15.0
        for color, width in ((QColor(0, 0, 0, 120), 3.0), (QColor(247, 244, 236, 230), 1.15)):
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(center.x() - arm, center.y()), QPointF(center.x() - gap, center.y()))
            painter.drawLine(QPointF(center.x() + gap, center.y()), QPointF(center.x() + arm, center.y()))
            painter.drawLine(QPointF(center.x(), center.y() - arm), QPointF(center.x(), center.y() - gap))
            painter.drawLine(QPointF(center.x(), center.y() + gap), QPointF(center.x(), center.y() + arm))

    def _paint_eraser(self, painter: QPainter, scale: float) -> None:
        radius = self._eraser_radius() * scale
        painter.setPen(QPen(QColor(247, 244, 236, 170), 1.2))
        painter.setBrush(QColor(255, 255, 255, 16))
        painter.drawEllipse(self._hover, radius, radius)

    def _track_laser(self, _pos: QPoint, moved: bool) -> None:
        if moved:
            self.update()

    def _track_option_frame(self, pos: QPoint, alt: bool, left: bool) -> None:
        if self.captures_mouse():
            self._option_dragging = False
            return
        point = QPointF(pos)
        if alt and left and not self._option_dragging:
            self._option_dragging = True
            self._frame_origin = point
            self._live_frame = QRectF(point, point)
        elif self._option_dragging and left and self._frame_origin is not None:
            self._live_frame = QRectF(self._frame_origin, point).normalized()
        elif self._option_dragging and not left:
            self._option_dragging = False
            self._commit_live_frame()
            self.changed.emit()

    def _follow_screen(self, pos: QPoint) -> None:
        if self.mode == "zoom" or self._live_points or self._erasing or self.editor.isVisible():
            return
        if self.mode not in ("laser", "spotlight", "draw", "text", "idle"):
            return
        if self.mode == "idle" and not self.doc.has_ink:
            return
        screen = QGuiApplication.screenAt(pos)
        if screen is None or screen is self._screen:
            return
        self.place(screen)
        self.apply_native()
        self.update()
        self._sync_sheets()

    @staticmethod
    def _make_blank_cursor():
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        return QCursor(pixmap)
