import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from controller_keyboard import layout  # noqa: E402
from controller_keyboard.config import Config  # noqa: E402
from controller_keyboard.engine import (DESKTOP, KEYBOARD, SETTINGS, Engine,  # noqa: E402
                                        is_sentence_start, text_context)
from controller_keyboard.keys import (VK_BACK, VK_CAPITAL, VK_LCONTROL, VK_LMENU,  # noqa: E402
                                    VK_LSHIFT, VK_LWIN, VK_RETURN, VK_TAB, VK_UP)
from controller_keyboard.predictor import Predictor  # noqa: E402
from controller_keyboard.xinput import ControllerState  # noqa: E402

WORDS = os.path.join(os.path.dirname(__file__), "..", "controller_keyboard", "data", "words.txt")


class FakeSender:
    def __init__(self):
        self.log = []
        self.text = ""
        self.caps = False

    def key_down(self, vk): self.log.append(("down", vk))
    def key_up(self, vk): self.log.append(("up", vk))

    def tap(self, vk):
        self.log.append(("tap", vk))
        if vk == VK_CAPITAL:
            self.caps = not self.caps
        elif vk == VK_BACK:
            self.text = self.text[:-1]
        elif vk == VK_RETURN:
            self.text += "\n"
        elif vk == 0x20:
            self.text += " "

    def type_text(self, t):
        self.log.append(("text", t))
        self.text += t

    def type_char_vk(self, ch): self.log.append(("vkchar", ch))
    def caps_lock_on(self): return self.caps
    def mouse_move(self, dx, dy): self.log.append(("move", dx, dy))
    def mouse_button(self, b, down): self.log.append(("mouse", b, down))
    def wheel(self, d, horizontal=False): self.log.append(("wheel", d, horizontal))
    def release_all(self): pass


class Harness:
    def __init__(self):
        self.sender = FakeSender()
        self.events = []
        self.predictor = Predictor(WORDS, None)
        self.engine = Engine(self.sender, self.predictor, Config(path=None),
                             notify=lambda e, kw: self.events.append((e, kw)))
        self.t = 0.0

    def frame(self, buttons=(), lx=0.0, ly=0.0, rx=0.0, ry=0.0, lt=0.0, rt=0.0, dt=0.008):
        self.t += dt
        self.engine.update(ControllerState(frozenset(buttons), lx, ly, rx, ry, lt, rt), self.t, dt)

    def press(self, *buttons, **stick):
        self.frame(buttons, **stick)
        self.frame((), **stick)

    def keyboard_mode(self):
        self.press("VIEW")
        assert self.engine.mode == KEYBOARD

    def type_key(self, char):
        """Find char in the letters layer and press it with the right stick direction."""
        for cell, faces in layout.LETTERS.items():
            for face, k in faces.items():
                if k == char:
                    stick = _cell_stick(cell)
                    self.frame((), **stick)
                    self.frame((face,), **stick)
                    self.frame((), **stick)
                    self.frame(())
                    return
        raise KeyError(char)


def _cell_stick(cell):
    v = {"C": (0, 0), "U": (0, 1), "D": (0, -1), "L": (-1, 0), "R": (1, 0),
         "UL": (-.7, .7), "UR": (.7, .7), "DL": (-.7, -.7), "DR": (.7, -.7)}[cell]
    return {"lx": v[0], "ly": v[1]}


class TextContextTests(unittest.TestCase):
    def test_context(self):
        self.assertEqual(text_context("hello wor"), ("wor", "hello"))
        self.assertEqual(text_context("hello "), ("", "hello"))
        self.assertEqual(text_context("end. new"), ("new", None))
        self.assertEqual(text_context("don'"), ("don'", None))
        self.assertEqual(text_context(""), ("", None))

    def test_sentence_start(self):
        self.assertTrue(is_sentence_start("Hi. "))
        self.assertTrue(is_sentence_start("line\n"))
        self.assertFalse(is_sentence_start("Hi."))
        self.assertFalse(is_sentence_start(""))
        self.assertFalse(is_sentence_start("hi "))


class StickTests(unittest.TestCase):
    def test_sectors(self):
        self.assertEqual(layout.stick_to_cell(0, 0), "C")
        self.assertEqual(layout.stick_to_cell(0, 1), "U")
        self.assertEqual(layout.stick_to_cell(-0.7, 0.7), "UL")
        self.assertEqual(layout.stick_to_cell(1, 0), "R")
        self.assertEqual(layout.stick_to_cell(0.7, -0.7), "DR")

    def test_hysteresis(self):
        import math
        # 72.5 deg is just inside the U sector (67.5..112.5) but within the
        # hysteresis margin of UR, so a stick already on UR should stay on UR.
        a = math.radians(72.5)
        self.assertEqual(layout.stick_to_cell(math.cos(a), math.sin(a), previous="UR"), "UR")
        self.assertEqual(layout.stick_to_cell(0.45, 0, previous="R"), "R")   # radius hysteresis
        self.assertEqual(layout.stick_to_cell(0.45, 0, previous="C"), "C")

    def test_all_letters_present(self):
        letters = [k for c in layout.LETTERS.values() for k in c.values() if k.isalpha() and len(k) == 1]
        self.assertEqual(sorted(letters), [chr(c) for c in range(ord("a"), ord("z") + 1)])


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def test_view_toggles_keyboard_and_menu_settings(self):
        e = self.h.engine
        self.h.press("VIEW")
        self.assertEqual(e.mode, KEYBOARD)
        self.h.press("MENU")
        self.assertEqual(e.mode, SETTINGS)
        self.h.press("B")
        self.assertEqual(e.mode, KEYBOARD)
        self.h.press("VIEW")
        self.assertEqual(e.mode, DESKTOP)

    def test_view_menu_combo_pauses_without_single_actions(self):
        e = self.h.engine
        self.h.frame(("VIEW",))
        self.h.frame(("VIEW", "MENU"))
        self.h.frame(("MENU",))
        self.h.frame(())
        self.assertTrue(e.paused)
        self.assertEqual(e.mode, DESKTOP)
        self.h.press("A")  # ignored while paused
        self.assertNotIn(("tap", VK_RETURN), self.h.sender.log)
        self.h.frame(("VIEW", "MENU"))
        self.h.frame(())
        self.assertFalse(e.paused)

    def test_alt_tab_chord(self):
        s = self.h.sender
        self.h.frame((), lt=1.0)
        self.h.frame((), lt=1.0, rt=1.0)
        self.h.frame((), lt=1.0)
        self.h.frame((), lt=1.0, rt=1.0)
        self.h.frame(())
        self.assertEqual(s.log, [("down", VK_LMENU), ("tap", VK_TAB), ("tap", VK_TAB), ("up", VK_LMENU)])

    def test_ctrl_and_caps(self):
        s = self.h.sender
        self.h.press("LB")
        self.assertEqual(s.log, [("down", VK_LCONTROL), ("up", VK_LCONTROL)])
        s.log.clear()
        self.h.press("RB")  # quick tap < 350ms
        self.assertEqual(s.log, [("tap", VK_CAPITAL)])

    def test_mortal_kombat_chords(self):
        h = self.h
        s = h.sender
        # Hold LB + press X -> Copy (Ctrl + C)
        h.frame(("LB",))
        h.frame(("LB", "X"))
        h.frame(("LB",))
        h.frame(())
        self.assertIn(("down", VK_LCONTROL), s.log)
        self.assertIn(("tap", ord("C")), s.log)
        self.assertIn(("up", VK_LCONTROL), s.log)
        s.log.clear()

        # Hold LB + press Y -> Paste (Ctrl + V)
        h.frame(("LB",))
        h.frame(("LB", "Y"))
        h.frame(("LB",))
        h.frame(())
        self.assertIn(("down", VK_LCONTROL), s.log)
        self.assertIn(("tap", ord("V")), s.log)
        self.assertIn(("up", VK_LCONTROL), s.log)
        s.log.clear()

        # Hold LB + press A -> Undo (Ctrl + Z)
        h.frame(("LB",))
        h.frame(("LB", "A"))
        h.frame(("LB",))
        h.frame(())
        self.assertIn(("tap", ord("Z")), s.log)
        s.log.clear()

        # Hold LB + press B -> Cut (Ctrl + X)
        h.frame(("LB",))
        h.frame(("LB", "B"))
        h.frame(("LB",))
        h.frame(())
        self.assertIn(("tap", ord("X")), s.log)
        s.log.clear()

        # Hold LB + D-Pad Up -> Select All (Ctrl + A)
        h.frame(("LB",))
        h.frame(("LB", "DPAD_UP"))
        h.frame(("LB",))
        h.frame(())
        self.assertIn(("tap", ord("A")), s.log)

    def test_typing_letters_and_center_keys(self):
        h = self.h
        h.keyboard_mode()
        for c in "hi":
            h.type_key(c)
        h.press("B")   # centre B = space
        h.press("X")   # centre X = backspace
        h.press("X")
        self.assertEqual(h.sender.text, "h")
        self.assertEqual(h.engine.history, "h")

    def test_caps_lock_types_uppercase(self):
        h = self.h
        h.keyboard_mode()
        h.press("RB")
        h.type_key("q")
        self.assertEqual(h.sender.text, "Q")

    def test_auto_capitalize_after_sentence(self):
        h = self.h
        h.keyboard_mode()
        h.type_key("o")
        h.type_key("k")
        h.type_key(".")
        h.press("B")
        h.type_key("s")
        self.assertEqual(h.sender.text, "ok. S")

    def test_symbol_layer_toggle(self):
        h = self.h
        h.keyboard_mode()
        h.press("A")  # centre A = layer toggle
        self.assertEqual(h.engine.layer, "symbols")
        h.frame((), lx=-.7, ly=.7)
        h.frame(("Y",), lx=-.7, ly=.7)
        self.assertEqual(h.sender.text, "1")

    def test_dpad_completes_word(self):
        h = self.h
        h.keyboard_mode()
        h.type_key("t")
        h.type_key("h")
        self.assertIn("the", h.engine.suggestions)
        idx = h.engine.suggestions.index("the")
        from controller_keyboard.engine import DPAD_ORDER
        h.press(DPAD_ORDER[idx])
        self.assertEqual(h.sender.text, "the ")
        # next-word suggestions are available after the space
        self.assertEqual(len(h.engine.suggestions), 4)

    def test_completion_matches_capitalisation(self):
        h = self.h
        h.keyboard_mode()
        h.press("RB")
        h.type_key("t")
        h.press("RB")
        h.type_key("h")
        h.engine.suggestions = ["the"]
        h.press("DPAD_UP")
        self.assertEqual(h.sender.text, "The ")

    def test_learning_promotes_words(self):
        h = self.h
        h.keyboard_mode()
        for _ in range(3):
            for c in "zebra":
                h.type_key(c)
            h.press("B")
        h.type_key("z")
        self.assertEqual(h.engine.suggestions[0], "zebra")

    def test_modifier_held_sends_real_keys(self):
        h = self.h
        h.keyboard_mode()
        h.frame((), lt=1.0)
        stick = _cell_stick("U")
        h.frame((), lt=1.0, **stick)
        h.frame(("Y",), lt=1.0, **stick)   # U + Y = 'e'  -> Alt+E
        h.frame(("DPAD_UP",), lt=1.0)      # Alt+Up, not a prediction
        h.frame(())
        self.assertIn(("vkchar", "e"), h.sender.log)
        self.assertIn(("tap", VK_UP), h.sender.log)
        self.assertEqual(h.sender.text, "")

    def test_backspace_repeat(self):
        h = self.h
        h.keyboard_mode()
        for c in "hello":
            h.type_key(c)
        for _ in range(100):           # hold centre X for ~0.8 s
            h.frame(("X",))
        h.frame(())
        self.assertEqual(h.sender.text, "")

    def test_mouse_and_clicks(self):
        h = self.h
        for _ in range(10):
            h.frame((), rx=1.0)
        moves = [l for l in h.sender.log if l[0] == "move"]
        self.assertTrue(moves and all(m[1] > 0 and m[2] == 0 for m in moves))
        h.press("R3")
        self.assertIn(("mouse", "left", True), h.sender.log)
        self.assertIn(("mouse", "left", False), h.sender.log)

    def test_desktop_scroll(self):
        h = self.h
        for _ in range(30):
            h.frame((), ly=1.0)
        wheels = [l for l in h.sender.log if l[0] == "wheel"]
        self.assertTrue(wheels and all(w[1] > 0 and not w[2] for w in wheels))

    def test_pause_releases_held_modifier(self):
        h = self.h
        h.frame(("LB",))
        h.frame(("LB", "VIEW", "MENU"))
        self.assertIn(("up", VK_LCONTROL), h.sender.log)
        self.assertFalse(h.engine.ctrl_held)


class PredictorTests(unittest.TestCase):
    def test_prefix_and_next_word(self):
        p = Predictor(WORDS, None)
        self.assertIn("the", p.suggest("th"))
        self.assertEqual(len(p.suggest("")), 4)
        self.assertIn("hai", p.suggest("", "kya"))
        for _ in range(3):
            p.learn("you", "thank")
        self.assertEqual(p.suggest("", "thank")[0], "you")

    def test_persistence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "u.json")
            p = Predictor(WORDS, path)
            p.learn("antigravity", "hello")
            p.save()
            p2 = Predictor(WORDS, path)
            self.assertEqual(p2.suggest("antig")[0], "antigravity")


if __name__ == "__main__":
    unittest.main()
