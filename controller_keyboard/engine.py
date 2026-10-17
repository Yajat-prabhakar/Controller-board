"""Input engine: turns controller state into keyboard / mouse actions.

It knows nothing about Qt or real hardware - it receives ControllerState
snapshots and talks to an output "sender" - so it can be unit-tested.

Modes
-----
desktop  : HUD hidden. Right stick = mouse, left stick = scroll, buttons = keys.
keyboard : HUD shown. Left stick picks a cell, Y/X/B/A type, D-Pad = predictions.
settings : Game-Bar style settings overlay. Right stick = mouse, A = click, B = close.

Global (desktop + keyboard): LT = hold Alt, RT = Tab, LB = Caps Lock,
RB = hold Win, R3 = left click, L3 = right click.
View = toggle keyboard, Menu = toggle settings, View+Menu = pause / resume.
"""
import math

from . import layout
from .keys import (VK_BACK, VK_CAPITAL, VK_DELETE, VK_DOWN, VK_LEFT, VK_LCONTROL,
                   VK_LMENU, VK_LSHIFT, VK_LWIN, VK_RETURN, VK_RIGHT, VK_SPACE,
                   VK_TAB, VK_UP, VK_VOLUME_DOWN, VK_VOLUME_UP, vk_from_name)

DESKTOP, KEYBOARD, SETTINGS = "desktop", "keyboard", "settings"

# D-Pad direction -> prediction slot index (shown in this order on the HUD).
DPAD_ORDER = ("DPAD_UP", "DPAD_LEFT", "DPAD_RIGHT", "DPAD_DOWN")
DPAD_ARROWS = {"DPAD_UP": VK_UP, "DPAD_DOWN": VK_DOWN, "DPAD_LEFT": VK_LEFT, "DPAD_RIGHT": VK_RIGHT}
REPEATABLE_VKS = {VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, VK_BACK, VK_DELETE, VK_VOLUME_UP, VK_VOLUME_DOWN}
DESKTOP_BUTTONS = ("A", "B", "X", "Y") + DPAD_ORDER
SYSTEM_BUTTONS = frozenset({"VIEW", "MENU"})


def _is_word_char(c):
    return c.isalpha() or c == "'"


def text_context(history):
    """Return (current_word, previous_word) for the text typed so far.

    previous_word is None at a sentence boundary or when unknown.
    """
    i = len(history)
    while i > 0 and _is_word_char(history[i - 1]):
        i -= 1
    current = history[i:].lstrip("'")
    j = i
    while j > 0 and not _is_word_char(history[j - 1]):
        if history[j - 1] in ".!?\n":
            return current, None
        j -= 1
    k = j
    while k > 0 and _is_word_char(history[k - 1]):
        k -= 1
    prev = history[k:j].strip("'").lower()
    return current, (prev or None)


def is_sentence_start(history):
    """True if the next letter starts a sentence (after '. ', '! ', '? ' or a newline)."""
    if not history:
        return False
    if history[-1] == "\n":
        return True
    stripped = history.rstrip(" ")
    return len(stripped) < len(history) and bool(stripped) and stripped[-1] in ".!?"


def _stick_vector(x, y, deadzone, curve):
    """Return (unit_x, unit_y, amount 0..1 after deadzone + curve) or None."""
    mag = math.hypot(x, y)
    if mag <= deadzone:
        return None
    amount = min(1.0, (mag - deadzone) / (1.0 - deadzone)) ** curve
    return x / mag, y / mag, amount


class Engine:
    def __init__(self, sender, predictor, config, notify=None):
        self.sender = sender
        self.predictor = predictor
        self.cfg = config
        self.notify = notify

        self.mode = DESKTOP
        self._mode_before_settings = DESKTOP
        self.paused = False
        self.auto_paused = False
        self.auto_pause_override = False

        self.layer = "letters"
        self.cell = "C"
        self.alt_held = False
        self.ctrl_held = False
        self.win_held = False
        self.shift_held = False
        self._rb_down_time = 0.0
        self._rb_used_for_typing = False
        self.history = ""
        self.suggestions = []
        self.last_state = None

        self._prev = frozenset()
        self._lt = False
        self._rt = False
        self._sys_consumed = set()
        self._mouse_held = set()
        self._repeat = None
        self._mouse_acc = [0.0, 0.0]
        self._scroll_acc = [0.0, 0.0]
        self._refresh_suggestions()

    # ------------------------------------------------------------------ utils
    @property
    def active(self):
        return not self.paused and not (self.auto_paused and not self.auto_pause_override)

    @property
    def current_word(self):
        return text_context(self.history)[0]

    def suggestion_label(self, word):
        """The suggestion as it would be typed (with capitalisation applied)."""
        current, _ = text_context(self.history)
        return self._apply_case(word, current, self.history[:len(self.history) - len(current)])

    def release_all(self):
        """Release every held key / mouse button (used on errors and on quit)."""
        self._release_everything()

    def refresh_suggestions(self):
        self._refresh_suggestions()

    def _emit(self, event, **kw):
        if self.notify:
            self.notify(event, kw)

    # ------------------------------------------------------------- main loop
    def update(self, st, now, dt):
        self.last_state = st
        thr = self.cfg["general"]["trigger_threshold"]
        self._lt = st.lt > (thr * 0.6 if self._lt else thr)
        self._rt = st.rt > (thr * 0.6 if self._rt else thr)
        buttons = set(st.buttons)
        if self._lt:
            buttons.add("LT")
        if self._rt:
            buttons.add("RT")
        buttons = frozenset(buttons)
        pressed = buttons - self._prev
        released = self._prev - buttons
        self._prev = buttons

        self._system_buttons(buttons, released)
        if not self.active:
            return

        consumed = set()
        if self.mode != SETTINGS:
            consumed = self._global_buttons(pressed, released, buttons, now)
        pressed = pressed - consumed

        self._move_mouse(st.rx, st.ry, dt)
        self._mouse_click("R3", "left", pressed, released)
        self._mouse_click("L3", "right", pressed, released)

        if self.mode == KEYBOARD:
            self._keyboard(st, pressed, now)
        elif self.mode == DESKTOP:
            self._desktop(st, pressed, now, dt)
        else:
            self._settings(st, pressed, released, dt)
        self._process_repeat(buttons, now)

    def on_disconnect(self):
        self._release_everything()
        self._prev = frozenset()
        self._lt = self._rt = False
        self._sys_consumed.clear()
        self.last_state = None
        self._emit("changed")

    # -------------------------------------------------------- system buttons
    def _system_buttons(self, buttons, released):
        if SYSTEM_BUTTONS <= buttons and not SYSTEM_BUTTONS <= self._sys_consumed:
            self._sys_consumed |= SYSTEM_BUTTONS
            if self.auto_paused:
                self.auto_pause_override = not self.auto_pause_override
                if not self.active:
                    self._release_everything()
                self._emit("toast", text="Active over fullscreen app" if self.active
                           else "Paused (fullscreen app)")
                self._emit("rumble", strength=0.5, ms=120)
                self._emit("paused", paused=not self.active)
            else:
                self.set_paused(not self.paused)
        for b in ("VIEW", "MENU"):
            if b in released:
                if b in self._sys_consumed:
                    self._sys_consumed.discard(b)
                elif self.active:
                    if b == "VIEW":
                        self.toggle_keyboard()
                    else:
                        self.toggle_settings()

    def set_paused(self, paused):
        self.paused = paused
        if not self.active:
            self._release_everything()
        self._emit("toast", text="Controller mapping paused  (View + Menu to resume)" if paused
                   else "Controller mapping active")
        self._emit("rumble", strength=0.5, ms=120)
        self._emit("paused", paused=not self.active)

    def set_auto_paused(self, value):
        if value == self.auto_paused:
            return
        was_active = self.active
        self.auto_paused = value
        if not value:
            self.auto_pause_override = False
        if was_active and not self.active:
            self._release_everything()
            self._emit("toast", text="Paused: fullscreen app  (View + Menu to override)")
        elif not was_active and self.active:
            self._emit("toast", text="Controller mapping active")
        self._emit("paused", paused=not self.active)

    # ------------------------------------------------------------------ modes
    def set_mode(self, mode):
        if mode == self.mode:
            return
        if mode == SETTINGS:
            self._mode_before_settings = self.mode
            self._release_modifiers()
        if self.mode == SETTINGS and "left" in self._mouse_held:
            self._mouse_button("left", False)
        self.mode = mode
        self._repeat = None
        self.cell = "C"
        self._emit("mode", mode=mode)
        self._emit("changed")

    def toggle_keyboard(self):
        self.set_mode(DESKTOP if self.mode == KEYBOARD else KEYBOARD)
        self._emit("rumble", strength=0.25, ms=60)

    def toggle_settings(self):
        if self.mode == SETTINGS:
            self.close_settings()
        else:
            self.set_mode(SETTINGS)

    def close_settings(self):
        if self.mode == SETTINGS:
            self.set_mode(self._mode_before_settings)

    # ------------------------------------------------------ global buttons
    def _send_shortcut(self, vk, toast_msg):
        was_ctrl = self.ctrl_held
        if not was_ctrl:
            self.sender.key_down(VK_LCONTROL)
        self.sender.tap(vk)
        if not was_ctrl:
            self.sender.key_up(VK_LCONTROL)
        self._emit("toast", text=toast_msg)
        self._emit("rumble", strength=0.25, ms=50)
        self.reset_context()

    def _global_buttons(self, pressed, released, buttons, now):
        consumed = set()
        if "LT" in pressed:
            self._set_modifier("alt", True)
        if "LT" in released:
            self._set_modifier("alt", False)

        if "LB" in pressed:
            self._set_modifier("ctrl", True)
        if "LB" in released:
            self._set_modifier("ctrl", False)

        if "RB" in pressed:
            self.shift_held = True
            self._rb_down_time = now
            self._rb_used_for_typing = False
            self._emit("changed")

        if "RB" in released:
            self.shift_held = False
            if not self._rb_used_for_typing and (now - self._rb_down_time < 0.35):
                self.sender.tap(VK_CAPITAL)
            self._emit("changed")

        # Mortal Kombat style chords while holding LB (Control)
        if "LB" in buttons:
            chords = {
                "X": (ord("C"), "📋 Copied (Ctrl+C)"),
                "Y": (ord("V"), "📄 Pasted (Ctrl+V)"),
                "A": (ord("Z"), "↩ Undo (Ctrl+Z)"),
                "B": (ord("X"), "✂ Cut (Ctrl+X)"),
                "DPAD_UP": (ord("A"), "☑ Select All (Ctrl+A)"),
                "DPAD_DOWN": (ord("S"), "💾 Saved (Ctrl+S)"),
                "DPAD_LEFT": (ord("W"), "✕ Closed Tab (Ctrl+W)"),
                "DPAD_RIGHT": (ord("F"), "🔍 Search (Ctrl+F)"),
            }
            for b, (vk, msg) in chords.items():
                if b in pressed:
                    self._send_shortcut(vk, msg)
                    consumed.add(b)

        if "RT" in pressed:
            if self.shift_held:
                self._rb_used_for_typing = True
                self.sender.key_down(VK_LSHIFT)
                self.sender.tap(VK_TAB)
                self.sender.key_up(VK_LSHIFT)
            else:
                self.sender.tap(VK_TAB)
            self.reset_context()
            consumed.add("RT")

        return consumed

    def _set_modifier(self, which, down):
        if which == "alt":
            attr, vk = "alt_held", VK_LMENU
        elif which == "ctrl":
            attr, vk = "ctrl_held", VK_LCONTROL
        else:
            attr, vk = "win_held", VK_LWIN

        if getattr(self, attr) == down:
            return
        setattr(self, attr, down)
        if down:
            self.sender.key_down(vk)
            self.reset_context()
        else:
            self.sender.key_up(vk)
        self._emit("changed")

    def _release_modifiers(self):
        self._set_modifier("alt", False)
        self._set_modifier("ctrl", False)
        self._set_modifier("win", False)
        if self.shift_held:
            self.shift_held = False
            self.sender.key_up(VK_LSHIFT)
            self._emit("changed")

    def _release_everything(self):
        self._release_modifiers()
        for b in list(self._mouse_held):
            self._mouse_button(b, False)
        self._repeat = None
        self._mouse_acc = [0.0, 0.0]
        self._scroll_acc = [0.0, 0.0]
        self.sender.release_all()

    # ------------------------------------------------------------ mouse
    def _mouse_button(self, button, down):
        if down:
            self._mouse_held.add(button)
        else:
            self._mouse_held.discard(button)
        self.sender.mouse_button(button, down)

    def _mouse_click(self, ctrl_button, mouse_button, pressed, released):
        if ctrl_button in pressed:
            self._mouse_button(mouse_button, True)
            self.reset_context()
        elif ctrl_button in released and mouse_button in self._mouse_held:
            self._mouse_button(mouse_button, False)

    def _move_mouse(self, x, y, dt):
        m = self.cfg["mouse"]
        v = _stick_vector(x, y, m["deadzone"], m["curve"])
        if v is None:
            self._mouse_acc = [0.0, 0.0]
            return
        nx, ny, amount = v
        speed = m["speed"] * amount
        self._mouse_acc[0] += nx * speed * dt
        self._mouse_acc[1] += -ny * speed * dt  # screen Y grows downwards
        dx, dy = int(self._mouse_acc[0]), int(self._mouse_acc[1])
        self._mouse_acc[0] -= dx
        self._mouse_acc[1] -= dy
        if dx or dy:
            self.sender.mouse_move(dx, dy)

    def _scroll(self, x, y, dt):
        m = self.cfg["mouse"]
        v = _stick_vector(x, y, max(0.25, m["deadzone"]), m["curve"])
        if v is None:
            self._scroll_acc = [0.0, 0.0]
            return
        nx, ny, amount = v
        if abs(ny) > abs(nx) * 2:      # mostly vertical -> ignore sideways drift
            nx = 0.0
        elif abs(nx) > abs(ny) * 2:
            ny = 0.0
        rate = m["scroll_speed"] * 120.0 * amount
        sign = -1.0 if m["invert_scroll"] else 1.0
        self._scroll_acc[0] += nx * rate * dt
        self._scroll_acc[1] += ny * rate * dt * sign
        for axis, horizontal in ((1, False), (0, True)):
            units = int(self._scroll_acc[axis] / 30) * 30
            if units:
                self.sender.wheel(units, horizontal)
                self._scroll_acc[axis] -= units

    # --------------------------------------------------------- key repeat
    def _start_repeat(self, button, fn, now):
        self._repeat = [button, fn, now + self.cfg["typing"]["repeat_delay"]]

    def _process_repeat(self, buttons, now):
        if not self._repeat:
            return
        button, fn, due = self._repeat
        if button not in buttons:
            self._repeat = None
        elif now >= due:
            fn()
            self._repeat[2] = now + 1.0 / max(1, self.cfg["typing"]["repeat_rate"])

    # ------------------------------------------------------- desktop mode
    def _desktop(self, st, pressed, now, dt):
        mapping = self.cfg["desktop_buttons"]
        for b in DESKTOP_BUTTONS:
            if b in pressed:
                vk = vk_from_name(mapping.get(b))
                if vk is None:
                    continue
                if self.shift_held:
                    self._rb_used_for_typing = True
                    self.sender.key_down(VK_LSHIFT)
                    self.sender.tap(vk)
                    self.sender.key_up(VK_LSHIFT)
                else:
                    self.sender.tap(vk)
                self.reset_context()
                if vk in REPEATABLE_VKS:
                    self._start_repeat(b, lambda vk=vk: self.sender.tap(vk), now)
        self._scroll(st.lx, st.ly, dt)

    # ------------------------------------------------------ settings mode
    def _settings(self, st, pressed, released, dt):
        if "A" in pressed:
            self._mouse_button("left", True)
        elif "A" in released and "left" in self._mouse_held:
            self._mouse_button("left", False)
        if "B" in pressed:
            self.close_settings()
            return
        self._scroll(st.lx, st.ly, dt)

    # ------------------------------------------------------ keyboard mode
    def _keyboard(self, st, pressed, now):
        cell = layout.stick_to_cell(st.lx, st.ly, self.cfg["hud"]["stick_threshold"], self.cell)
        if cell != self.cell:
            self.cell = cell
            self._emit("changed")
            self._emit("activity")
        for face in layout.FACES:
            if face in pressed:
                key = layout.key_at(self.layer, self.cell, face)
                self._emit("flash", cell=self.cell, face=face)
                self._emit("activity")
                self.press_key(key)
                if key == layout.BKSP:
                    self._start_repeat(face, lambda: self.press_key(layout.BKSP), now)
        for index, d in enumerate(DPAD_ORDER):
            if d in pressed:
                self._emit("activity")
                if self.alt_held or self.ctrl_held or self.win_held:
                    vk = DPAD_ARROWS[d]   # Win+Arrows snaps windows, Ctrl+Arrows navigates words
                    self.sender.tap(vk)
                    self._start_repeat(d, lambda vk=vk: self.sender.tap(vk), now)
                else:
                    self.accept_suggestion(index)

    def press_key(self, key):
        if self.shift_held:
            self._rb_used_for_typing = True
        modifiers = self.alt_held or self.ctrl_held or self.win_held
        if key == layout.LAYER:
            self.layer = "symbols" if self.layer == "letters" else "letters"
            self._emit("changed")
            return
        if key in (layout.ENTER, layout.SPACE, layout.BKSP):
            vk = {layout.ENTER: VK_RETURN, layout.SPACE: VK_SPACE, layout.BKSP: VK_BACK}[key]
            self.sender.tap(vk)
            if modifiers:
                self.reset_context()
            elif key == layout.BKSP:
                self.history = self.history[:-1]
                self._refresh_suggestions()
            else:
                self._append("\n" if key == layout.ENTER else " ")
            return
        if modifiers:
            # Real key press so shortcuts like Ctrl+C, Win+E, Alt+F work.
            self.sender.type_char_vk(key.lower())
            self.reset_context()
            return
        ch = key
        if ch.isalpha():
            upper = self.sender.caps_lock_on() or self.shift_held or (
                self.cfg["typing"]["auto_capitalize"] and is_sentence_start(self.history))
            ch = ch.upper() if upper else ch.lower()
        self.sender.type_text(ch)
        self._append(ch)

    # ---------------------------------------------------------- prediction
    def _apply_case(self, word, current, before):
        if word == "i" or word.startswith("i'"):
            word = "I" + word[1:]
        if self.sender.caps_lock_on() or self.shift_held:
            return word.upper()
        if current:
            if len(current) > 1 and current.isupper():
                return word.upper()
            if current[0].isupper():
                return word[0].upper() + word[1:]
            return word
        if self.cfg["typing"]["auto_capitalize"] and is_sentence_start(before):
            return word[0].upper() + word[1:]
        return word

    def accept_suggestion(self, index):
        if self.shift_held:
            self._rb_used_for_typing = True
        if index >= len(self.suggestions):
            return
        word = self.suggestions[index]
        current, _ = text_context(self.history)
        before = self.history[:len(self.history) - len(current)]
        text = self._apply_case(word, current, before)[len(current):] + " "
        if not current and before and before[-1] in ",.!?;:)":
            text = " " + text
        self.sender.type_text(text)
        self._append(text)

    def _append(self, text):
        for c in text:
            if not _is_word_char(c):
                current, prev = text_context(self.history)
                if current:
                    self.predictor.learn(current, prev)
            self.history += c
        if len(self.history) > 300:
            self.history = self.history[-200:]
        self._refresh_suggestions()

    def reset_context(self):
        """Forget typed text (caret probably moved: click, Tab, focus change...)."""
        if self.history:
            self.history = ""
            self._refresh_suggestions()

    def _refresh_suggestions(self):
        if self.cfg["typing"]["predictions"]:
            current, prev = text_context(self.history)
            self.suggestions = self.predictor.suggest(current, prev)
        else:
            self.suggestions = []
        self._emit("changed")
