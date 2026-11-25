# timer-app
# Pomodoro Timer (`pomodoro-tk`)

A minimal, dark-themed Pomodoro timer built in pure Python using `tkinter` with **zero third-party dependencies**.

## Features

- **Three Timer Modes**
  - **Focus**: 25 minutes
  - **Short Break**: 5 minutes
  - **Long Break**: 15 minutes (automatically triggered every 4 completed focus sessions)
- **Animated Progress Ring**: Smooth circular arc with subtle glow layers and a moving head indicator
- **Session Tracking**: Visual progress dots for the current 4-session cycle and a total completed-sessions counter
- **Completion Alerts**: Visual pulse animation, system bell notification, and window title status update
- **Live Window Title**: Displays the remaining time and active mode while running
- **Keyboard Shortcuts**: Control the timer without leaving your keyboard

## Requirements

- Python 3.x with `tkinter` (included in standard Python installations on Windows and macOS; on some Linux distros install via `sudo apt install python3-tk`)

No `pip install` or external packages required.

## Usage

Run the script directly:

```bash
python pomodoro.py
```

### Controls

| Key / Button | Action |
| --- | --- |
| `Space` / **Start / Pause** | Start, pause, or resume the timer |
| `R` / **Reset** | Reset the current session timer |
| `S` / **Skip** | Skip to the next mode (`Focus` ↔ `Short Break` / `Long Break`) |

## Customization

Edit the configuration constants at the top of `pomodoro.py` to adjust durations, cycle length, or theme colors:

```python
MODES = {
    "focus": {"label": "Focus",       "minutes": 25, "color": "#FF6B81"},
    "short": {"label": "Short Break", "minutes": 5,  "color": "#2EE6C5"},
    "long":  {"label": "Long Break",  "minutes": 15, "color": "#8E9BFF"},
}
SESSIONS_BEFORE_LONG_BREAK = 4
```
