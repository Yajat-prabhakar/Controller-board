"""Click-through, focus-free overlays: the 3x3 keyboard HUD and toast messages."""
import time

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from .. import layout
from ..engine import is_sentence_start
from ..winutil import force_topmost, make_no_activate
from . import theme

# HUD geometry in unscaled "design" pixels.
PAD, HEADER_H, PREVIEW_H, PRED_H, CELL_W, CELL_H, GAP = 14, 26, 38, 42, 124, 102, 8
BASE_W = PAD * 2 + CELL_W * 3 + GAP * 2
BASE_H = PAD + HEADER_H + 6 + PREVIEW_H + 6 + PRED_H + 8 + CELL_H * 3 + GAP * 2 + PAD

KEY_OFFSETS = {"Y": (0, -30), "X": (-38, 0), "B": (38, 0), "A": (0, 30)}
KEY_RADIUS = 17
SPECIAL_LABELS = {layout.ENTER: "↵", layout.BKSP: "⌫", layout.SPACE: "␣"}
DPAD_GLYPHS = ("▲", "◀", "▶", "▼")


def _font(px, bold=False):
    f = QFont(theme.FONT_FAMILY)
    f.setPixelSize(px)
    f.setBold(bold)
    return f


def _alpha(color, a):
    c = QColor(color)
    c.setAlpha(a)
    return c


class OverlayWidget(QWidget):
    """Frameless, always-on-top, click-through window that never takes focus."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool
                         | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._opacity = 0.0
        self._styled = False
        self._anim = QPropertyAnimation(self, b"overlayOpacity", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._on_anim_done)

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, value):
        self._opacity = value
        self.update()

    overlayOpacity = pyqtProperty(float, _get_opacity, _set_opacity)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            if not self._styled:
                make_no_activate(int(self.winId()))
                self._styled = True
            force_topmost(int(self.winId()))
        except OSError:
            pass

    def fade_to(self, target, ms=180):
        if target > 0 and not self.isVisible():
            self.show()
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(float(target))
        self._anim.setDuration(ms)
        self._anim.start()

    def _on_anim_done(self):
        if self._opacity <= 0.001:
            self.hide()


class KeyboardHUD(OverlayWidget):
    def __init__(self, engine, config, sender):
        super().__init__()
        self.engine = engine
        self.cfg = config
        self.sender = sender
        self._flash = {}
        self._shown = False
        self._caps = False
        self._last_activity = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._tick)
        self.apply_config()

    # -- configuration / placement -------------------------------------------
    def apply_config(self):
        s = float(self.cfg["hud"]["scale"])
        self.setFixedSize(int(BASE_W * s), int(BASE_H * s))
        self._reposition()
        if self._shown:
            self.wake()
        self.update()

    def _reposition(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        pos, m = self.cfg["hud"]["position"], 24
        w, h = self.width(), self.height()
        if pos.endswith("left"):
            x = screen.left() + m
        elif pos.endswith("right"):
            x = screen.right() - w - m
        else:
            x = screen.center().x() - w // 2
        y = screen.top() + m if pos.startswith("top") else screen.bottom() - h - m
        self.move(x, y)

    # -- visibility ------------------------------------------------------------
    def show_hud(self):
        self._shown = True
        self._reposition()
        self._timer.start()
        self.wake()

    def hide_hud(self):
        self._shown = False
        self._timer.stop()
        if self.isVisible():
            self.fade_to(0.0, 160)

    def wake(self):
        if not self._shown:
            return
        self._last_activity = time.monotonic()
        target = float(self.cfg["hud"]["active_opacity"])
        if not self.isVisible() or abs(self._opacity - target) > 0.01:
            self.fade_to(target, 120)

    def flash(self, cell, face):
        self._flash[(cell, face)] = time.monotonic() + 0.18
        self.update()
        QTimer.singleShot(200, self.update)

    def _tick(self):
        caps = self.sender.caps_lock_on()
        if caps != self._caps:
            self._caps = caps
            self.update()
        idle = float(self.cfg["hud"]["idle_opacity"])
        if (time.monotonic() - self._last_activity > float(self.cfg["hud"]["idle_seconds"])
                and self._opacity > idle + 0.01
                and self._anim.state() != QPropertyAnimation.State.Running):
            self.fade_to(idle, 600)

    # -- painting ----------------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setOpacity(self._opacity)
        s = self.width() / BASE_W
        p.scale(s, s)

        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.setBrush(theme.PANEL_BG)
        p.drawRoundedRect(QRectF(0.5, 0.5, BASE_W - 1, BASE_H - 1), 16, 16)

        self._draw_header(p, QRectF(PAD, PAD, BASE_W - 2 * PAD, HEADER_H))
        y = PAD + HEADER_H + 6
        self._draw_preview(p, QRectF(PAD, y, BASE_W - 2 * PAD, PREVIEW_H))
        y += PREVIEW_H + 6
        self._draw_predictions(p, QRectF(PAD, y, BASE_W - 2 * PAD, PRED_H))
        y += PRED_H + 8

        e = self.engine
        upper = self._caps or e.shift_held or (e.cfg["typing"]["auto_capitalize"] and is_sentence_start(e.history))
        now = time.monotonic()
        for i, cell in enumerate(layout.CELLS):
            r, c = divmod(i, 3)
            rect = QRectF(PAD + c * (CELL_W + GAP), y + r * (CELL_H + GAP), CELL_W, CELL_H)
            self._draw_cell(p, rect, cell, upper, now)
        p.end()

    def _pill(self, p, x, y, text, active, color):
        f = _font(11, True)
        w = QFontMetrics(f).horizontalAdvance(text) + 16
        rect = QRectF(x, y, w, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_alpha(color, 220) if active else QColor(255, 255, 255, 16))
        p.drawRoundedRect(rect, 10, 10)
        p.setFont(f)
        p.setPen(QColor("#0E0E0E") if active else theme.TEXT_DIM)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        return w

    def _draw_header(self, p, rect):
        e = self.engine
        x, y = rect.x(), rect.y() + 3
        x += self._pill(p, x, y, "ABC" if e.layer == "letters" else "123", True, theme.ACCENT) + 5
        x += self._pill(p, x, y, "CAPS", self._caps, theme.FACE_COLORS["Y"]) + 5
        x += self._pill(p, x, y, "SHIFT", e.shift_held, theme.FACE_COLORS["A"]) + 5
        x += self._pill(p, x, y, "CTRL", e.ctrl_held, theme.FACE_COLORS["B"]) + 5
        x += self._pill(p, x, y, "ALT", e.alt_held, theme.FACE_COLORS["X"]) + 5
        p.setFont(_font(11, False))
        p.setPen(theme.TEXT_DIM)
        right = QRectF(x, rect.y(), rect.right() - x, rect.height())
        p.drawText(right, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "⧉ hide   ☰ settings")

    def _draw_preview(self, p, rect):
        line = self.engine.history.rsplit("\n", 1)[-1]
        has_text = bool(line)
        p.setPen(QPen(theme.ACCENT if has_text else QColor(255, 255, 255, 26), 1.2))
        p.setBrush(QColor(12, 12, 14, 210))
        p.drawRoundedRect(rect, 9, 9)

        inner = rect.adjusted(12, 0, -12, 0)
        if has_text:
            f = _font(15, False)
            p.setFont(f)
            p.setPen(theme.TEXT)
            fm = QFontMetrics(f)
            shown = fm.elidedText(line, Qt.TextElideMode.ElideLeft, max(20, int(inner.width()) - 12))
            p.drawText(inner, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, shown)
            cx = min(inner.right() - 2, inner.x() + fm.horizontalAdvance(shown) + 2)
            p.setPen(QPen(theme.ACCENT, 2.2))
            p.drawLine(QPointF(cx, rect.y() + 9), QPointF(cx, rect.bottom() - 9))
        else:
            p.setFont(_font(13, False))
            p.setPen(theme.TEXT_DIM)
            p.drawText(inner, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "✎  Live typing preview…")

    def _draw_predictions(self, p, rect):
        e = self.engine
        gap = 6
        w = (rect.width() - gap * 3) / 4
        for i in range(4):
            r = QRectF(rect.x() + i * (w + gap), rect.y(), w, rect.height())
            word = e.suggestion_label(e.suggestions[i]) if i < len(e.suggestions) else ""
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18 if word else 8))
            p.drawRoundedRect(r, 10, 10)
            p.setFont(_font(10, True))
            p.setPen(theme.ACCENT if word else theme.TEXT_DIM)
            p.drawText(QRectF(r.x() + 8, r.y(), 14, r.height()), Qt.AlignmentFlag.AlignVCenter, DPAD_GLYPHS[i])
            p.setFont(_font(14, True))
            p.setPen(theme.TEXT if word else theme.TEXT_DIM)
            tr = QRectF(r.x() + 22, r.y(), r.width() - 26, r.height())
            label = QFontMetrics(p.font()).elidedText(word or "—", Qt.TextElideMode.ElideRight, int(tr.width()))
            p.drawText(tr, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter, label)

    def _draw_cell(self, p, rect, cell, upper, now):
        e = self.engine
        selected = cell == e.cell
        if selected:
            p.setPen(QPen(theme.ACCENT, 2))
            p.setBrush(QColor(255, 255, 255, 34))
        else:
            p.setPen(QPen(theme.CELL_BORDER, 1))
            p.setBrush(QColor(255, 255, 255, 22) if cell == "C" else theme.CELL_BG)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 12, 12)

        p.setFont(_font(11, True))
        p.setPen(theme.ACCENT if selected else theme.TEXT_DIM)
        p.drawText(QRectF(rect.x() + 8, rect.y() + 4, 20, 16), Qt.AlignmentFlag.AlignLeft, layout.CELL_ARROWS[cell])

        cx, cy = rect.center().x(), rect.center().y()
        for face, (dx, dy) in KEY_OFFSETS.items():
            key = layout.key_at(e.layer, cell, face)
            flashing = self._flash.get((cell, face), 0) > now
            self._draw_key(p, QPointF(cx + dx, cy + dy), face, key, selected, flashing, upper)

    def _draw_key(self, p, center, face, key, selected, flashing, upper):
        col = theme.FACE_COLORS[face]
        if flashing:
            p.setPen(QPen(col, 2))
            p.setBrush(col)
        elif selected:
            p.setPen(QPen(col, 2))
            p.setBrush(_alpha(col, 70))
        else:
            p.setPen(QPen(_alpha(col, 120), 1.5))
            p.setBrush(QColor(255, 255, 255, 10))
        p.drawEllipse(center, KEY_RADIUS, KEY_RADIUS)

        if key == layout.LAYER:
            label = "123" if self.engine.layer == "letters" else "ABC"
        elif key in SPECIAL_LABELS:
            label = SPECIAL_LABELS[key]
        else:
            label = key.upper() if upper and key.isalpha() else key
        p.setFont(_font(16 if len(label) == 1 else 11, True))
        p.setPen(QColor("#111111") if flashing else theme.TEXT)
        r = KEY_RADIUS
        p.drawText(QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r), Qt.AlignmentFlag.AlignCenter, label)


class Toast(OverlayWidget):
    """Small pill message at the top of the screen."""

    def __init__(self):
        super().__init__()
        self._text = ""
        self._hide = QTimer(self)
        self._hide.setSingleShot(True)
        self._hide.timeout.connect(lambda: self.fade_to(0.0, 300))

    def show_text(self, text, ms=1800):
        self._text = text
        fm = QFontMetrics(_font(14, True))
        self.setFixedSize(fm.horizontalAdvance(text) + 56, 44)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.top() + 36)
        self.update()
        self.fade_to(1.0, 150)
        self._hide.start(ms)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(QColor(255, 255, 255, 34), 1))
        p.setBrush(theme.PANEL_BG)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.ACCENT)
        p.drawEllipse(QPointF(22, r.center().y()), 5, 5)
        p.setFont(_font(14, True))
        p.setPen(theme.TEXT)
        p.drawText(r.adjusted(36, 0, -16, 0), Qt.AlignmentFlag.AlignVCenter, self._text)
        p.end()
