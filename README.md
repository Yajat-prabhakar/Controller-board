# Controller Keyboard (Xbox One S Desktop & Typing Overlay)

Control Windows and type seamlessly using an Xbox One S (or any XInput) controller—featuring an **Alphabetical 3×3 ABCD Matrix**, **Live Typing Preview Bar**, **80,000-Word Bilingual English + Hinglish Auto-Completion**, **Hold Chords (`Alt+Tab`, `Win`, `Caps Lock`)**, **Right-Stick Mouse Emulation**, and an **Xbox Game Bar-style Settings Overlay**.

---

## Quick Start

### 1. Launching the App

Double-click **[`run.bat`](run.bat)** to launch the overlay in the background without a console window, or run from a terminal:

```powershell
.\.venv\Scripts\python.exe main.py
```

Look for the green controller icon in your **Windows System Tray** (bottom-right taskbar). Clicking the tray icon opens the **Xbox Game Bar Settings Overlay** at any time.

---

## Controller Layout & Key Binds

| Controller Input | Mode | Action / Key Bind |
| :--- | :--- | :--- |
| **View (`⧉`)** | Global | Toggle floating **3×3 Keyboard HUD** on/off |
| **Menu (`☰`)** | Global | Open / close the **Xbox Game Bar Settings Overlay** |
| **View + Menu (`⧉ + ☰`)** | Global | **Pause / Resume** all controller mapping (e.g., when launching a game) |
| **`RB` (Hold)** | Global | Hold **`Control (Ctrl)`** *(Hold `RB` + any key/chord; `RB + RT` = `Ctrl + Tab`)* |
| **`LB` (Hold)** | Global | Hold **`Shift`** *(types uppercase, highlights text; quick tap toggles **`Caps Lock`**)* |
| **`LT` (Hold)** | Global | Hold **`Alt`** *(Hold `LT` + tap `RT` for `Alt + Tab` window switching)* |
| **`RT` (Tap)** | Global | Tap **`Tab`** *(or `Shift + Tab` when holding `LB`)* |
| **Right Stick** | Global | Move **Mouse Cursor** (smooth acceleration curve with deadzone) |
| **`R3` (Right Stick Click)** | Global | **Left Mouse Click** |
| **`L3` (Left Stick Click)** | Global | **Right Mouse Click** |
| **Left Stick** | Keyboard | Select 1 of 9 cells in the 3×3 matrix |
| **Left Stick** | Desktop | Smooth 2D document / webpage scrolling |
| **`Y` / `X` / `B` / `A`** | Keyboard | Type corresponding letter in highlighted cell |
| **`Y` / `X` / `B` / `A`** | Desktop | `Space` (`Y`), `Backspace` (`X`), `Esc` (`B`), `Enter` (`A`) |
| **D-Pad (`▲ ◀ ▶ ▼`)** | Keyboard | Auto-complete top 4 predicted words |
| **D-Pad (`▲ ◀ ▶ ▼`)** | Desktop | Arrow keys (`Up`, `Left`, `Right`, `Down`) |

---

## ⚡ Mortal Kombat Style Quick Chords (Copy / Paste / Undo / Cut)

Hold **`LB`** and instantly press any face button or D-pad direction—**no need to aim the joystick**:

* **`LB + X`** → **Copy (`Ctrl + C`)**
* **`LB + Y`** → **Paste (`Ctrl + V`)**
* **`LB + A`** → **Undo (`Ctrl + Z`)**
* **`LB + B`** → **Cut (`Ctrl + X`)**
* **`LB + D-Pad ▲`** → **Select All (`Ctrl + A`)**
* **`LB + D-Pad ▼`** → **Save (`Ctrl + S`)**
* **`LB + D-Pad ◀`** → **Close Tab (`Ctrl + W`)**
* **`LB + D-Pad ▶`** → **Find / Search (`Ctrl + F`)**

### 🎮 EvoFox One S Universal Back Buttons (`ML` & `MR`)
On your EvoFox One S controller, the back macro buttons can be programmed on hardware:
1. Hold the **Macro/Setting (M)** button on the back until the indicator flashes.
2. Press the back paddle (**`ML`** or **`MR`**).
3. Press **`LB + X`** (for Copy) or **`LB + Y`** (for Paste).
4. Press **`M`** again to save. Now your back paddles instantly Copy and Paste with a single click!

## 3×3 Clustered ABCD Matrix

Tilt the **Left Stick** in any of the 8 directions to highlight an outer cell, or release the stick to return to the **Center (`●`)** cell. Inside each cell, buttons follow standard reading order: **`Y` (Top)** → **`X` (Left)** → **`B` (Right)** → **`A` (Bottom)**.

```text
      LEFT COLUMN                MIDDLE COLUMN               RIGHT COLUMN
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│       ↖ UP-LEFT       │  │         ↑ UP          │  │      ↗ UP-RIGHT       │
│        [Y: A]         │  │        [Y: E]         │  │        [Y: I]         │
│    [X: B]   [B: C]    │  │    [X: F]   [B: G]    │  │    [X: J]   [B: K]    │
│        [A: D]         │  │        [A: H]         │  │        [A: L]         │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│        ← LEFT         │  │       • CENTER        │  │        → RIGHT        │
│        [Y: M]         │  │      [Y: Enter]       │  │        [Y: Q]         │
│    [X: N]   [B: O]    │  │ [X: Bksp]  [B: Space] │  │    [X: R]   [B: S]    │
│        [A: P]         │  │       [A: 123]        │  │        [A: T]         │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│     ↙ DOWN-LEFT       │  │        ↓ DOWN         │  │     ↘ DOWN-RIGHT      │
│        [Y: U]         │  │        [Y: Y]         │  │        [Y: ?]         │
│    [X: V]   [B: W]    │  │    [X: Z]   [B: .]    │  │    [X: !]   [B: ']    │
│        [A: X]         │  │        [A: ,]         │  │        [A: -]         │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

* **Center Cell (`●` Neutral Stick):**
  * **`Y`** → `Enter (↵)`
  * **`X`** → `Backspace (⌫)`
  * **`B`** → `Space (␣)`
  * **`A`** → `123 / ABC` (Toggles between letters and numbers/symbols)
* **Live Typing Preview Bar:**
  * Sits at the top of the HUD (`✎ Live typing preview…`) with an active green caret.
  * Shows the sentence you are typing in real time—even if the overlay sits directly over an app's text input box (e.g., WhatsApp, Discord, or web browsers).
  * Automatically clears as soon as you press **`Enter`** to send a message.

---

## Bilingual Auto-Completion & Prediction Engine

The typing prediction engine is powered by an **~80,000-word bilingual dictionary** and a **30,000-phrase bigram context graph**:

* **English Vocabulary (50,000+ words):** Conversational subtitle frequency list covering everyday words, contractions (`don't`, `i'll`, `can't`), and tech terminology.
* **Hinglish / Roman Hindi (20,000+ words):** Conversational Roman Hindi chat corpus:
  * Pronouns & basics: *aap, tum, mai, mera, meri, mujhe, hum, yeh, woh, uska, kisi, etc.*
  * Verbs & tenses: *kya, kyu, kaise, kab, kaha, kar, raha, rahe, rahi, hoga, hogi, hua, hue, gaya, gayi, etc.*
  * Chat slang: *bhai, yaar, dost, achha, theek, bilkul, sahi, pata, bohot, abhi, ajeeb, badiya, bawal, tabahi, tabrtod, etc.*
* **Contextual Next-Word (Bigram) Prediction:**
  * After typing **`kya`** → D-Pad shows: **`▲ hai`**, **`◀ baat`**, **`▶ hua`**, **`▼ kar`**
  * After typing **`thank`** → D-Pad shows: **`▲ you`**, **`◀ so`**, **`▶ very`**
  * After typing **`how`** → D-Pad shows: **`▲ are`**, **`◀ is`**, **`▶ can`**, **`▼ was`**
  * After typing **`bahut`** → D-Pad shows: **`▲ achha`**, **`◀ badiya`**, **`▶ sahi`**, **`▼ zyada`**
* **Self-Learning Personal Memory:**
  * Custom slang, friends' names, and unique phrases are automatically saved to `%APPDATA%\ControllerKeyboard\user_words.json`. Every time you use a word, its rank climbs so it appears first.

---

## Xbox Game Bar Settings Overlay

Press **Menu (`☰`)** on your controller or click the system tray icon to summon the **Settings Overlay**:

* **Live Input Visualizer:** Displays real-time controller stick axes, trigger values, and button presses.
* **Mouse Tuning:** Adjust pointer speed, precision curve, stick deadzone, and scroll rate.
* **Keyboard HUD Customization:** Change HUD position (Bottom-Center, Bottom-Left, Bottom-Right, Top-Center), scale, idle fade delay, and opacity.
* **Auto-Pause for Fullscreen Games:** Automatically suspends controller mapping when a fullscreen game has focus.
* **Start with Windows:** Toggle automatic launch upon Windows sign-in.

---

## Project Structure

```text
controller-keyborad/
├── main.py                       # Application entry point with single-instance mutex
├── run.bat                       # Windows launcher (runs pythonw without terminal window)
├── requirements.txt              # Dependencies (PyQt6)
├── tools/
│   └── build_dictionary.py       # Script to rebuild 80k bilingual English + Hinglish dictionary
├── controller_keyboard/
│   ├── app.py                    # 120Hz polling loop, overlay coordination & tray icon
│   ├── engine.py                 # Core input engine, chords, typing buffer & mouse emulation
│   ├── layout.py                 # 3x3 ABCD & Symbol matrix definitions & stick sector mapper
│   ├── predictor.py              # Prefix Trie + Bigram scoring + user learning engine
│   ├── sendinput.py              # Native Win32 SendInput keyboard & mouse backend
│   ├── winutil.py                # WS_EX_NOACTIVATE, fullscreen detection & autostart registry
│   ├── xinput.py                 # Direct ctypes XInput 1.4 wrapper (buttons, sticks, rumble)
│   ├── data/
│   │   ├── dictionary.json       # 80k unigrams & 30k bigrams
│   │   └── words.txt             # Frequency-sorted word list
│   └── ui/
│       ├── hud.py                # Transparent 3x3 keyboard HUD with live preview bar & toasts
│       ├── settings.py           # Fullscreen dimmed Game Bar settings overlay
│       └── theme.py              # Xbox green dark theme & stylesheet
└── tests/
    ├── test_engine.py            # Unit tests for engine, chords, typing, and predictions
    └── test_ui.py                # UI rendering & smoke tests
```

---

## Running Tests

To run the complete test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
