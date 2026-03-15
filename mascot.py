"""
mascot.py  —  Zeta: Z.ai Monitor animated mascot & roadmap guide
Zeta is a small robot character that talks through features and the roadmap.

Usage (from app.py):
    from mascot import ZetaMascot
    m = ZetaMascot(self.root, theme_name=self.cfg.theme)
"""

import tkinter as tk
import math

# ── Roadmap messages  (title, body) ──────────────────────────────────────────

MESSAGES = [
    ("Selam! 👋",       "Ben Zeta!\nZ.ai Monitor'ün rehber robotu."),
    ("Ne yapıyorum?",   "Z.ai API'ni izleyerek\nkota kullanımını gösteriyorum."),
    ("V1.1.0 ✅",       "Sistem tepsisi desteği eklendi!\n✕ → tepside gizlen."),
    ("V1.1.0 ✅",       "Kota uyarıları artık\nWindows bildirimi gönderiyor!"),
    ("V1.1.0 ✅",       "Warn/Crit eşiklerini\nayarlardan özelleştirebilirsin!"),
    ("İpucu ⌨️",        "Ctrl+R  →  Anlık yenile\nCtrl+Q  →  Uygulamadan çık"),
    ("İpucu ⌨️",        "Esc  →  Sistem tepsisine gizle\nCtrl+,  →  Ayarları aç"),
    ("Yolda... 🚧",     "Kullanım geçmişi grafiği\nyakında geliyor!"),
    ("Yolda... 🚧",     "Çoklu hesap desteği\nplanlanıyor!"),
    ("Yolda... 🚧",     "Otomatik güncelleme sistemi\ngeliştirme aşamasında!"),
    ("Yolda... 🚧",     "MacOS & Linux desteği\nbir sonraki sürümde!"),
    ("Teşekkürler ⭐",  "Beğendiysen GitHub'da\nyıldız atmayı unutma!"),
]

# ── Color palettes ────────────────────────────────────────────────────────────

_THEMES = {
    "dark": {
        "bg":          "#0d0f14",
        "surface":     "#161a24",
        "surface2":    "#1e2333",
        "border":      "#2a3045",
        "accent":      "#4f8ef7",
        "accent2":     "#a78bfa",
        "text":        "#e8ecf4",
        "text_dim":    "#6b7694",
        "ok":          "#22d3a0",
        "warn":        "#f59e0b",
        "danger":      "#f4566a",
        "r_body":      "#1e2a4a",
        "r_head":      "#253660",
        "r_eye":       "#22d3a0",
        "r_detail":    "#4f8ef7",
        "bar_bg":      "#1e2333",
    },
    "light": {
        "bg":          "#f0f4ff",
        "surface":     "#ffffff",
        "surface2":    "#e8edf8",
        "border":      "#c8d0e8",
        "accent":      "#3b6ff0",
        "accent2":     "#7c5cdb",
        "text":        "#1a1e2e",
        "text_dim":    "#5a6485",
        "ok":          "#0ea572",
        "warn":        "#d97706",
        "danger":      "#e0334a",
        "r_body":      "#b0c4f0",
        "r_head":      "#8aaae8",
        "r_eye":       "#0ea572",
        "r_detail":    "#3b6ff0",
        "bar_bg":      "#dde3f5",
    },
}


# ── Mascot window ─────────────────────────────────────────────────────────────

class ZetaMascot:
    """
    Floating animated mascot window.
    Double-click anywhere on it to close.
    Single-click drag to reposition.
    """

    W = 300
    H = 430
    CX = 150            # canvas horizontal center
    CHAR_BASE = 350     # character "floor" Y (before bob offset)

    # Animation timing
    FPS         = 30    # frames per second
    TYPE_SPEED  = 2     # frames per character typed
    PAUSE_AFTER = 110   # frames to wait after full message (≈3.6s at 30fps)
    BLINK_MIN   = 100   # min frames between blinks
    BLINK_MAX   = 160   # max frames between blinks
    BLINK_DUR   = 5     # frames a blink lasts

    def __init__(self, parent: tk.Misc, theme_name: str = "dark",
                 position: tuple | None = None):
        self.c = _THEMES.get(theme_name, _THEMES["dark"])

        self.win = tk.Toplevel(parent)
        self.win.title("Zeta — Z.ai Assistant")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.97)
        self.win.resizable(False, False)

        # Placement
        if position:
            x, y = position
        else:
            sw = parent.winfo_screenwidth()
            sh = parent.winfo_screenheight()
            x  = sw - self.W - 30
            y  = sh - self.H - 70
        self.win.geometry(f"{self.W}x{self.H}+{x}+{y}")

        # Canvas
        self.cv = tk.Canvas(
            self.win, width=self.W, height=self.H,
            bg=self.c["bg"], highlightthickness=0, bd=0,
        )
        self.cv.pack(fill="both", expand=True)

        # Drag
        self._drag_x = self._drag_y = 0
        self.cv.bind("<ButtonPress-1>",   self._drag_start)
        self.cv.bind("<B1-Motion>",        self._drag_motion)
        self.cv.bind("<Double-Button-1>",  lambda e: self.close())

        # ── Animation state ───────────────────────────────────────────────────
        self._frame        = 0
        self._bob_phase    = 0.0

        # Blink
        self._eye_open     = True
        self._blink_timer  = 0
        self._next_blink   = self.BLINK_MIN

        # Mouth / talk
        self._talking      = False
        self._talk_timer   = 0

        # Message
        self._msg_idx      = 0
        self._msg_char     = 0
        self._type_tick    = 0
        self._pause_timer  = 0

        self._animate()

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.win.winfo_x()
        self._drag_y = e.y_root - self.win.winfo_y()

    def _drag_motion(self, e):
        self.win.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── Animation loop ────────────────────────────────────────────────────────

    def _animate(self):
        if not self.win.winfo_exists():
            return

        self._frame     += 1
        self._bob_phase += 0.06
        bob_y = int(math.sin(self._bob_phase) * 4)

        # Blink logic
        self._next_blink -= 1
        if self._next_blink <= 0:
            self._eye_open    = False
            self._blink_timer = 0
            self._next_blink  = self.BLINK_MIN + (
                (self._frame * 37) % (self.BLINK_MAX - self.BLINK_MIN)
            )
        if not self._eye_open:
            self._blink_timer += 1
            if self._blink_timer >= self.BLINK_DUR:
                self._eye_open = True

        # Typing
        title, full_text = MESSAGES[self._msg_idx]
        if self._msg_char < len(full_text):
            self._type_tick += 1
            if self._type_tick >= self.TYPE_SPEED:
                self._type_tick  = 0
                self._msg_char  += 1
                self._talking    = True
                self._talk_timer = 10
        else:
            # Full message shown — pause before advancing
            self._pause_timer += 1
            if self._pause_timer >= self.PAUSE_AFTER:
                self._pause_timer = 0
                self._msg_char    = 0
                self._type_tick   = 0
                self._msg_idx     = (self._msg_idx + 1) % len(MESSAGES)

        # Talking state
        if self._talk_timer > 0:
            self._talk_timer -= 1
        self._talking = self._talk_timer > 0

        # Draw
        self._draw(bob_y)
        self.win.after(1000 // self.FPS, self._animate)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def _draw(self, bob_y: int = 0):
        cv = self.cv
        c  = self.c
        cv.delete("all")

        # Background
        cv.create_rectangle(0, 0, self.W, self.H, fill=c["bg"], outline="")

        # Close hint
        cv.create_text(self.W - 8, 8,
                       text="dbl-click: kapat",
                       font=("Segoe UI", 6), fill=c["text_dim"], anchor="ne")

        self._draw_bubble(cv, c)
        self._draw_character(cv, c, self.CX, self.CHAR_BASE + bob_y)

    # ── Speech bubble ─────────────────────────────────────────────────────────

    def _draw_bubble(self, cv: tk.Canvas, c: dict):
        bx1, by1, bx2, by2 = 14, 10, self.W - 14, 170
        r = 12

        def rr(x1, y1, x2, y2, fill):
            """Draw a filled rounded rectangle."""
            cv.create_rectangle(x1 + r, y1,     x2 - r, y2,     fill=fill, outline="")
            cv.create_rectangle(x1,     y1 + r,  x2,     y2 - r, fill=fill, outline="")
            cv.create_oval(x1,       y1,       x1+2*r, y1+2*r, fill=fill, outline="")
            cv.create_oval(x2 - 2*r, y1,       x2,     y1+2*r, fill=fill, outline="")
            cv.create_oval(x1,       y2 - 2*r, x1+2*r, y2,     fill=fill, outline="")
            cv.create_oval(x2 - 2*r, y2 - 2*r, x2,     y2,     fill=fill, outline="")

        rr(bx1, by1, bx2, by2, c["surface"])

        # Border outline (cheap: just outer rectangle lines)
        cv.create_rectangle(bx1 + r, by1, bx2 - r, by1, outline=c["border"])
        cv.create_rectangle(bx1 + r, by2, bx2 - r, by2, outline=c["border"])
        cv.create_rectangle(bx1, by1 + r, bx1, by2 - r, outline=c["border"])
        cv.create_rectangle(bx2, by1 + r, bx2, by2 - r, outline=c["border"])

        # Tail (triangle pointing toward character head)
        mid = self.CX
        cv.create_polygon(mid - 10, by2, mid + 10, by2, mid, by2 + 16,
                          fill=c["surface"], outline="")

        # Title
        title, full_text = MESSAGES[self._msg_idx]
        cv.create_text(self.CX, by1 + 20, text=title,
                       font=("Segoe UI Semibold", 11), fill=c["accent"],
                       anchor="center")

        # Divider
        cv.create_line(bx1 + 14, by1 + 36, bx2 - 14, by1 + 36, fill=c["border"])

        # Typed text
        visible_text = full_text[:self._msg_char]
        cv.create_text(self.CX, by1 + 85,
                       text=visible_text,
                       font=("Segoe UI", 9), fill=c["text"],
                       anchor="center", justify="center",
                       width=bx2 - bx1 - 28)

        # Cursor blink while typing
        if self._msg_char < len(full_text) and (self._frame // 8) % 2 == 0:
            cv.create_text(self.CX, by1 + 110,
                           text="▋", font=("Segoe UI", 8),
                           fill=c["accent"], anchor="center")

        # Progress dots
        n = len(MESSAGES)
        dot_start = self.CX - (n * 7) // 2
        for i in range(n):
            dx   = dot_start + i * 7 + 3
            dy   = by2 - 8
            fill = c["accent"] if i == self._msg_idx else c["border"]
            cv.create_oval(dx - 2, dy - 2, dx + 2, dy + 2, fill=fill, outline="")

    # ── Character drawing ─────────────────────────────────────────────────────

    def _draw_character(self, cv: tk.Canvas, c: dict, cx: int, base: int):
        rb = c["r_body"]
        rh = c["r_head"]
        re = c["r_eye"]
        rd = c["r_detail"]

        # ── Antenna ──────────────────────────────────────────────────────────
        cv.create_line(cx, base - 108, cx, base - 84, fill=rd, width=2)
        blink_col = c["accent"] if (self._frame // 14) % 2 == 0 else c["danger"]
        cv.create_oval(cx - 6, base - 120, cx + 6, base - 108,
                       fill=blink_col, outline=rd, width=1)

        # ── Head ─────────────────────────────────────────────────────────────
        cv.create_oval(cx - 40, base - 84, cx + 40, base - 28,
                       fill=rh, outline=rd, width=2)

        # ── Left eye ─────────────────────────────────────────────────────────
        lex1, ley1, lex2, ley2 = cx - 30, base - 70, cx - 12, base - 50
        if self._eye_open:
            cv.create_oval(lex1, ley1, lex2, ley2,
                           fill=c["surface2"], outline=rd, width=1)
            cv.create_oval(lex1 + 4, ley1 + 3, lex2 - 2, ley2 - 2,
                           fill=re, outline="")
            cv.create_oval(lex1 + 4, ley1 + 3, lex1 + 8, ley1 + 7,
                           fill="white", outline="")
        else:
            ey_mid = (ley1 + ley2) // 2
            cv.create_line(lex1 + 2, ey_mid, lex2 - 2, ey_mid, fill=rd, width=2)

        # ── Right eye ────────────────────────────────────────────────────────
        rex1, rey1, rex2, rey2 = cx + 12, base - 70, cx + 30, base - 50
        if self._eye_open:
            cv.create_oval(rex1, rey1, rex2, rey2,
                           fill=c["surface2"], outline=rd, width=1)
            cv.create_oval(rex1 + 2, rey1 + 3, rex2 - 4, rey2 - 2,
                           fill=re, outline="")
            cv.create_oval(rex1 + 2, rey1 + 3, rex1 + 6, rey1 + 7,
                           fill="white", outline="")
        else:
            ey_mid = (rey1 + rey2) // 2
            cv.create_line(rex1 + 2, ey_mid, rex2 - 2, ey_mid, fill=rd, width=2)

        # ── Nose chip ────────────────────────────────────────────────────────
        cv.create_rectangle(cx - 4, base - 46, cx + 4, base - 40,
                            fill=rd, outline="")

        # ── Mouth ────────────────────────────────────────────────────────────
        if self._talking:
            mh = 6 + int(5 * abs(math.sin(self._frame * 0.5)))
            cv.create_oval(cx - 12, base - 38, cx + 12, base - 38 + mh,
                           fill=c["bg"], outline=rd, width=2)
        else:
            cv.create_arc(cx - 14, base - 40, cx + 14, base - 26,
                          start=200, extent=140, style="arc",
                          outline=rd, width=2)

        # ── Neck ─────────────────────────────────────────────────────────────
        cv.create_rectangle(cx - 8, base - 28, cx + 8, base - 20,
                            fill=rb, outline=rd, width=1)

        # ── Body ─────────────────────────────────────────────────────────────
        cv.create_rectangle(cx - 36, base - 20, cx + 36, base + 44,
                            fill=rb, outline=rd, width=2)

        # Chest screen
        cv.create_rectangle(cx - 24, base - 12, cx + 24, base + 18,
                            fill=c["surface2"], outline=rd, width=1)

        # Animated quota bar inside chest screen
        bar_pct = 0.45 + 0.38 * abs(math.sin(self._frame * 0.025))
        bar_w   = int(42 * bar_pct)
        cv.create_rectangle(cx - 21, base - 2, cx + 21, base + 5,
                            fill=c["bar_bg"], outline="")
        bar_col = c["ok"] if bar_pct < 0.5 else (c["warn"] if bar_pct < 0.8 else c["danger"])
        cv.create_rectangle(cx - 21, base - 2, cx - 21 + bar_w, base + 5,
                            fill=bar_col, outline="")
        cv.create_text(cx, base + 12, text="Z.ai",
                       font=("Segoe UI", 6, "bold"), fill=rd, anchor="center")

        # Body side bolts
        cv.create_oval(cx - 33, base - 15, cx - 25, base - 7,
                       fill=c["surface2"], outline=rd, width=1)
        cv.create_oval(cx + 25, base - 15, cx + 33, base - 7,
                       fill=c["surface2"], outline=rd, width=1)

        # ── Arms ─────────────────────────────────────────────────────────────
        # Left arm slightly raised when talking
        arm_offset = -4 if self._talking else 0
        cv.create_rectangle(cx - 54, base - 16 + arm_offset,
                             cx - 36, base + 14 + arm_offset,
                             fill=rb, outline=rd, width=1)
        cv.create_oval(cx - 57, base + 10 + arm_offset,
                       cx - 39, base + 24 + arm_offset,
                       fill=rb, outline=rd, width=1)

        # Right arm
        cv.create_rectangle(cx + 36, base - 16, cx + 54, base + 14,
                            fill=rb, outline=rd, width=1)
        cv.create_oval(cx + 39, base + 10, cx + 57, base + 24,
                       fill=rb, outline=rd, width=1)

        # ── Legs ─────────────────────────────────────────────────────────────
        cv.create_rectangle(cx - 28, base + 44, cx - 12, base + 80,
                            fill=rb, outline=rd, width=1)
        cv.create_rectangle(cx + 12, base + 44, cx + 28, base + 80,
                            fill=rb, outline=rd, width=1)

        # ── Feet ─────────────────────────────────────────────────────────────
        cv.create_oval(cx - 34, base + 74,  cx - 8,  base + 90,
                       fill=rb, outline=rd, width=1)
        cv.create_oval(cx +  8, base + 74,  cx + 34, base + 90,
                       fill=rb, outline=rd, width=1)

        # Ground shadow (contracts/expands with bob)
        sw = 44 + int(4 * math.cos(self._bob_phase))
        cv.create_oval(cx - sw, base + 87, cx + sw, base + 97,
                       fill=c["surface2"], outline="")

    # ── Public interface ──────────────────────────────────────────────────────

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()

    def is_open(self) -> bool:
        try:
            return self.win.winfo_exists()
        except Exception:
            return False
