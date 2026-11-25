"""
Pomodoro Timer - built with pure tkinter (no third-party packages).

Run:  python pomodoro.py
Keys: Space = start/pause   R = reset   S = skip
"""

import math
import time
import tkinter as tk
from tkinter import font as tkfont

# ───────────────────────── Configuration ─────────────────────────
MODES = {
    "focus": {"label": "Focus",       "minutes": 25, "color": "#FF6B81"},
    "short": {"label": "Short Break", "minutes": 5,  "color": "#2EE6C5"},
    "long":  {"label": "Long Break",  "minutes": 15, "color": "#8E9BFF"},
}
SESSIONS_BEFORE_LONG_BREAK = 4

BG = "#12121C"
CARD = "#1B1B2B"
TRACK = "#2A2A40"
TEXT = "#F2F2F7"
MUTED = "#7C7C98"


# ───────────────────────── Helpers ─────────────────────────
def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle using a smoothed polygon."""
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


def blend(c1, c2, t):
    """Blend two hex colors. t=0 -> c1, t=1 -> c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class PillButton(tk.Canvas):
    """A flat, rounded, hoverable button drawn on a canvas."""

    def __init__(self, parent, text, command, width=110, height=44,
                 fill=TRACK, fg=TEXT, font=None, parent_bg=BG):

        
        super().__init__(parent, width=width, height=height,
                         bg=parent_bg, highlightthickness=0, bd=0, cursor="hand2")
        self.w, self.h = width, height
        self.command = command
        self.fill, self.fg = fill, fg
        self.font = font
        self.text = text
        self._hover = False
        self._draw()
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self.command())

    def _draw(self):
        self.delete("all")
        color = blend(self.fill, "#FFFFFF", 0.12) if self._hover else self.fill
        rounded_rect(self, 2, 2, self.w - 2, self.h - 2, self.h // 2 - 2, fill=color, outline="")
        self.create_text(self.w / 2, self.h / 2, text=self.text, fill=self.fg, font=self.font)

    def _set_hover(self, state):
        self._hover = state
        self._draw()

    def configure_button(self, text=None, fill=None, fg=None):
        if text is not None:
            self.text = text
        if fill is not None:
            self.fill = fill
        if fg is not None:
            self.fg = fg
        self._draw()


# ───────────────────────── Application ─────────────────────────
class PomodoroApp:
    RING_SIZE = 320
    RING_R = 128
    RING_W = 14

    def __init__(self, root):
        self.root = root
        root.title("Pomodoro")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Fonts
        fam = self._pick_font(["SF Pro Display", "Segoe UI", "Helvetica Neue", "Helvetica", "Arial"])
        self.f_time = tkfont.Font(family=fam, size=58, weight="bold")
        self.f_label = tkfont.Font(family=fam, size=13, weight="bold")
        self.f_small = tkfont.Font(family=fam, size=11)
        self.f_btn = tkfont.Font(family=fam, size=12, weight="bold")
        self.f_title = tkfont.Font(family=fam, size=18, weight="bold")

        # State
        self.mode = "focus"
        self.total = MODES[self.mode]["minutes"] * 60
        self.remaining = float(self.total)
        self.running = False
        self.end_time = 0.0
        self.completed = 0
        self._job = None

        self._build_ui()
        self._apply_mode(self.mode)

        root.bind("<space>", lambda e: self.toggle())
        root.bind("<r>", lambda e: self.reset())
        root.bind("<s>", lambda e: self.skip())

        # Center window
        root.update_idletasks()
        w, h = root.winfo_width(), root.winfo_height()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 3
        root.geometry(f"+{x}+{y}")

    # ── UI construction ──
    @staticmethod
    def _pick_font(candidates):
        available = set(tkfont.families())
        for c in candidates:
            if c in available:
                return c
        return "TkDefaultFont"

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=BG, padx=28, pady=24)
        outer.pack()

        tk.Label(outer, text="🍅  Pomodoro", bg=BG, fg=TEXT, font=self.f_title).pack(anchor="w")
        tk.Label(outer, text="Stay focused. Take breaks. Repeat.",
                 bg=BG, fg=MUTED, font=self.f_small).pack(anchor="w", pady=(0, 16))

        # Mode tabs
        tabs = tk.Frame(outer, bg=BG)
        tabs.pack(pady=(0, 14))
        self.tabs = {}
        for key, m in MODES.items():
            btn = PillButton(tabs, m["label"], lambda k=key: self.set_mode(k),
                             width=112, height=36, font=self.f_small, fill=CARD, fg=MUTED)
            btn.pack(side="left", padx=4)
            self.tabs[key] = btn

        # Card with ring
        card = tk.Canvas(outer, width=self.RING_SIZE + 40, height=self.RING_SIZE + 40,
                         bg=BG, highlightthickness=0)
        card.pack()
        rounded_rect(card, 2, 2, self.RING_SIZE + 38, self.RING_SIZE + 38, 36, fill=CARD, outline="")
        self.card = card

        cx = cy = (self.RING_SIZE + 40) / 2
        self.cx, self.cy = cx, cy
        r = self.RING_R

        # Soft glow layers behind the arc
        self.glow = [
            card.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=0,
                            style="arc", width=self.RING_W + 12 - i * 4, outline=CARD)
            for i in range(2)
        ]
        # Track
        card.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TRACK, width=self.RING_W)
        # Progress arc
        self.arc = card.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=0,
                                   style="arc", width=self.RING_W, outline=MODES["focus"]["color"])
        # Knob at arc head
        self.knob = card.create_oval(0, 0, 0, 0, fill="#FFFFFF", outline="", state="hidden")

        # Texts
        self.time_text = card.create_text(cx, cy - 8, text="25:00", fill=TEXT, font=self.f_time)
        self.mode_text = card.create_text(cx, cy + 46, text="FOCUS", fill=MODES["focus"]["color"],
                                          font=self.f_label)

        # Session dots
        dots = tk.Canvas(outer, width=200, height=30, bg=BG, highlightthickness=0)
        dots.pack(pady=(16, 0))
        self.dots = dots
        self.dot_ids = []
        for i in range(SESSIONS_BEFORE_LONG_BREAK):
            x = 100 + (i - (SESSIONS_BEFORE_LONG_BREAK - 1) / 2) * 30
            self.dot_ids.append(dots.create_oval(x - 7, 8, x + 7, 22, fill=TRACK, outline=""))

        self.count_label = tk.Label(outer, text="0 sessions completed", bg=BG, fg=MUTED, font=self.f_small)
        self.count_label.pack(pady=(2, 14))

        # Controls
        ctrl = tk.Frame(outer, bg=BG)
        ctrl.pack()
        self.btn_reset = PillButton(ctrl, "Reset", self.reset, width=90, height=48,
                                    font=self.f_btn, fill=CARD, fg=TEXT)
        self.btn_reset.pack(side="left", padx=6)
        self.btn_main = PillButton(ctrl, "Start", self.toggle, width=130, height=48,
                                   font=self.f_btn, fill=MODES["focus"]["color"], fg="#12121C")
        self.btn_main.pack(side="left", padx=6)
        self.btn_skip = PillButton(ctrl, "Skip", self.skip, width=90, height=48,
                                   font=self.f_btn, fill=CARD, fg=TEXT)
        self.btn_skip.pack(side="left", padx=6)

        tk.Label(outer, text="Space: start/pause  ·  R: reset  ·  S: skip",
                 bg=BG, fg=MUTED, font=self.f_small).pack(pady=(14, 0))

    # ── Mode handling ──
    def set_mode(self, mode):
        self._stop()
        self._apply_mode(mode)

    def _apply_mode(self, mode):
        self.mode = mode
        self.total = MODES[mode]["minutes"] * 60
        self.remaining = float(self.total)
        color = MODES[mode]["color"]

        self.card.itemconfigure(self.arc, outline=color)
        for i, g in enumerate(self.glow):
            self.card.itemconfigure(g, outline=blend(CARD, color, 0.10 + 0.06 * i))
        self.card.itemconfigure(self.mode_text, text=MODES[mode]["label"].upper(), fill=color)
        self.btn_main.configure_button(text="Start", fill=color)

        for key, btn in self.tabs.items():
            if key == mode:
                btn.configure_button(fill=color, fg="#12121C")
            else:
                btn.configure_button(fill=CARD, fg=MUTED)

        self._update_display()
        self._update_dots()
        self.root.title(f"{MODES[mode]['label']} · Pomodoro")

    def _next_mode(self):
        if self.mode == "focus":
            return "long" if self.completed % SESSIONS_BEFORE_LONG_BREAK == 0 else "short"
        return "focus"

    # ── Timer control ──
    def toggle(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.end_time = time.monotonic() + self.remaining
        self.btn_main.configure_button(text="Pause")
        self._tick()

    def _stop(self):
        self.running = False
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None
        self.btn_main.configure_button(text="Resume" if 0 < self.remaining < self.total else "Start")

    def reset(self):
        self._stop()
        self.remaining = float(self.total)
        self.btn_main.configure_button(text="Start")
        self._update_display()

    def skip(self):
        self._stop()
        if self.mode == "focus":
            self.completed += 1
        self._apply_mode(self._next_mode())

    def _tick(self):
        if not self.running:
            return
        self.remaining = max(0.0, self.end_time - time.monotonic())
        self._update_display()
        if self.remaining <= 0:
            self._finish()
            return
        self._job = self.root.after(50, self._tick)

    def _finish(self):
        self.running = False
        self._job = None
        if self.mode == "focus":
            self.completed += 1
        finished_mode = self.mode
        self.root.bell()
        self._flash(6)
        self._apply_mode(self._next_mode())
        self.root.title(f"{MODES[finished_mode]['label']} done! · Pomodoro")

    def _flash(self, times):
        """Briefly pulse the card to signal completion."""
        if times <= 0:
            return
        color = MODES[self.mode]["color"]
        self.card.itemconfigure(self.time_text, fill=color if times % 2 else TEXT)
        self.root.after(180, lambda: self._flash(times - 1))
        if times == 1:
            self.root.after(200, lambda: self.card.itemconfigure(self.time_text, fill=TEXT))

    # ── Rendering ──
    def _update_display(self):
        secs = int(math.ceil(self.remaining))
        self.card.itemconfigure(self.time_text, text=f"{secs // 60:02d}:{secs % 60:02d}")

        progress = 1 - (self.remaining / self.total if self.total else 0)
        extent = -min(359.99, 360 * progress)
        self.card.itemconfigure(self.arc, extent=extent)
        for g in self.glow:
            self.card.itemconfigure(g, extent=extent)

        # Knob position at arc head
        if progress > 0.002:
            ang = math.radians(90 + extent)
            kx = self.cx + self.RING_R * math.cos(ang)
            ky = self.cy - self.RING_R * math.sin(ang)
            k = 5
            self.card.coords(self.knob, kx - k, ky - k, kx + k, ky + k)
            self.card.itemconfigure(self.knob, state="normal")
        else:
            self.card.itemconfigure(self.knob, state="hidden")

        if self.running:
            self.root.title(f"{secs // 60:02d}:{secs % 60:02d} · {MODES[self.mode]['label']}")

    def _update_dots(self):
        if self.mode == "long":
            filled = SESSIONS_BEFORE_LONG_BREAK
        else:
            filled = self.completed % SESSIONS_BEFORE_LONG_BREAK
        for i, d in enumerate(self.dot_ids):
            self.dots.itemconfigure(d, fill=MODES["focus"]["color"] if i < filled else TRACK)
        n = self.completed
        self.count_label.configure(text=f"{n} session{'s' if n != 1 else ''} completed")


def main():
    root = tk.Tk()
    PomodoroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
