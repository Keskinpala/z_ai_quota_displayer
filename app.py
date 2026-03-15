"""
app.py — Z.ai Monitor  
Always-on-top overlay with collapsible panel, settings tab, live quota display.
Run: python app.py
"""

import tkinter as tk
import threading
import time

from zai_client import ZaiClient, QuotaData
from config import AppConfig


THEMES = {
    "dark": {
        "bg":          "#0d0f14",
        "surface":     "#161a24",
        "surface2":    "#1e2333",
        "border":      "#2a3045",
        "accent":      "#4f8ef7",
        "accent2":     "#a78bfa",
        "text":        "#e8ecf4",
        "text_dim":    "#6b7694",
        "text_muted":  "#2250e9",
        "ok":          "#22d3a0",
        "warn":        "#f59e0b",
        "danger":      "#f4566a",
        "bar_bg":      "#1e2333",
        "title_bg":    "#0a0c12",
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
        "text_muted":  "#0f304b",
        "ok":          "#0ea572",
        "warn":        "#d97706",
        "danger":      "#e0334a",
        "bar_bg":      "#dde3f5",
        "title_bg":    "#dde3f5",
    },
}


def pct_color(pct: int, c) -> str:
    if pct < 50:
        return c["ok"]
    elif pct < 80:
        return c["warn"]
    return c["danger"]


class ZaiMonitorApp:
    COLLAPSED_H = 38
    EXPANDED_H  = 380
    WIDTH       = 330

    # Title bar blink: seconds to show quota info vs app name
    BLINK_QUOTA_SEC  = 30   # quota göster
    BLINK_TITLE_SEC  = 5  # sonra "Z.ai Monitor" göster

    def __init__(self):
        self.cfg = AppConfig.load()
        self.client = None
        self._rebuild_client()

        self.quota = None
        self._refresh_job = None
        self._dragging = False
        self._drag_x = self._drag_y = 0
        self._tab = "monitor"
        self._last_status = ""

        # collapsed titlebar blink state
        self._blink_show_title = False
        self._blink_job = None

        self._build_window()
        self._draw_ui()
        self._start_auto_refresh()
        self._schedule_blink()

    def _rebuild_client(self):
        if self.cfg.bearer_token:
            self.client = ZaiClient(self.cfg.bearer_token)
        else:
            self.client = None

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("Z.ai Monitor")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.cfg.always_on_top)
        self.root.attributes("-alpha", self.cfg.opacity)
        self.root.resizable(False, False)

        h = self.COLLAPSED_H if self.cfg.collapsed else self.EXPANDED_H
        self.root.geometry(f"{self.WIDTH}x{h}+{self.cfg.window_x}+{self.cfg.window_y}")
        self.root.configure(bg=self._c("bg"))

        self.root.bind("<ButtonPress-1>",  self._drag_start)
        self.root.bind("<B1-Motion>",       self._drag_motion)
        self.root.bind("<ButtonRelease-1>", self._drag_end)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _c(self, key):
        return THEMES[self.cfg.theme][key]

    # ── Collapsed blink ─────────────────────────────────────────────────────

    def _schedule_blink(self):
        """Alternate between quota % and app name when collapsed."""
        ##z.ai montior ise 5 saniye göster değilse 30 saniye göster
        if self._blink_job:
            self.root.after_cancel(self._blink_job)
        delay = self.BLINK_TITLE_SEC * 1000 if self._blink_show_title else self.BLINK_QUOTA_SEC * 1000
        self._blink_job = self.root.after(delay, self._do_blink)

    def _do_blink(self):
        self._blink_show_title = not self._blink_show_title
        if self.cfg.collapsed:
            self._draw_ui()
        self._schedule_blink()

    def _collapsed_center_text(self) -> tuple:
        """Returns (text, color) to show in collapsed center area."""
        c = THEMES[self.cfg.theme]
        if self._blink_show_title:
            return "Z.ai Monitor", c["text_dim"]
        # Show monthly token quota %
        if self.quota and not self.quota.error:
            tok = self.quota.token_limit
            if tok:
                pct = tok.percentage
                col = pct_color(pct, c)
                return f"{pct}% 5 Saatlik Kullanım", col
        return "Z.ai Monitor", c["text_dim"]

    # ── UI Draw ─────────────────────────────────────────────────────────────

    def _draw_ui(self):
        for w in self.root.winfo_children():
            w.destroy()
        c = THEMES[self.cfg.theme]
        self.root.configure(bg=c["bg"])

        # ── Title bar ───────────────────────────────────────────────────────
        bar = tk.Frame(self.root, bg=c["title_bg"], height=self.COLLAPSED_H)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="●", font=("Segoe UI", 9),
                 fg=c["accent"], bg=c["title_bg"]).pack(side="left", padx=(10, 4))

        if self.cfg.collapsed:
            # Center: blink between quota info and title
            txt, col = self._collapsed_center_text()
            tk.Label(bar, text=txt, font=("Segoe UI Semibold", 10),
                     fg=col, bg=c["title_bg"]).pack(side="left")

            # Level badge
            level_txt = self.quota.level.upper() if self.quota and not self.quota.error else "—"
            badge_bg  = c["accent2"] if self.quota and not self.quota.error else c["border"]
            tk.Label(bar, text=f" {level_txt} ", font=("Segoe UI", 7, "bold"),
                     fg=c["bg"], bg=badge_bg, padx=4, pady=1).pack(side="left", padx=6)
        else:
            tk.Label(bar, text="Z.ai Monitor", font=("Segoe UI Semibold", 10),
                     fg=c["text"], bg=c["title_bg"]).pack(side="left")
            level_txt = self.quota.level.upper() if self.quota and not self.quota.error else "—"
            badge_bg  = c["accent2"] if self.quota and not self.quota.error else c["border"]
            tk.Label(bar, text=f" {level_txt} ", font=("Segoe UI", 7, "bold"),
                     fg=c["bg"], bg=badge_bg, padx=4, pady=1).pack(side="left", padx=6)

        btn_cfg = dict(font=("Segoe UI", 9), bg=c["title_bg"], relief="flat",
                       bd=0, padx=6, pady=4, cursor="hand2")
        tk.Button(bar, text="✕", fg=c["danger"],
                  activeforeground=c["danger"], activebackground=c["title_bg"],
                  command=self._on_close, **btn_cfg).pack(side="right", padx=(0, 4))
        tk.Button(bar, text="⚙", fg=c["text_dim"],
                  activeforeground=c["text"], activebackground=c["title_bg"],
                  command=self._toggle_settings, **btn_cfg).pack(side="right")
        icon = "▸" if self.cfg.collapsed else "▾"
        tk.Button(bar, text=icon, fg=c["text_dim"],
                  activeforeground=c["text"], activebackground=c["title_bg"],
                  command=self._toggle_collapse, **btn_cfg).pack(side="right")

        if self.cfg.collapsed:
            return

        body = tk.Frame(self.root, bg=c["bg"])
        body.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        if self._tab == "settings":
            self._draw_settings(body, c)
        else:
            self._draw_monitor(body, c)

    def _draw_monitor(self, parent, c):
        top = tk.Frame(parent, bg=c["bg"])
        top.pack(fill="x", padx=14, pady=(10, 0))

        self.status_lbl = tk.Label(top, text=self._last_status,
                                   font=("Segoe UI", 7), fg=c["text_dim"], bg=c["bg"])
        self.status_lbl.pack(side="left")

        tk.Button(top, text="⟳ Yenile", font=("Segoe UI", 7),
                  fg=c["accent"], bg=c["surface2"], relief="flat", bd=0,
                  activeforeground=c["accent"], activebackground=c["border"],
                  padx=8, pady=2, cursor="hand2",
                  command=self._manual_refresh).pack(side="right")

        tk.Frame(parent, bg=c["border"], height=1).pack(fill="x", padx=14, pady=(8, 0))

        if not self.cfg.bearer_token:
            tk.Label(parent, text="No token set.\nOpen ⚙ Settings to add your Bearer token.",
                     font=("Segoe UI", 9), fg=c["text_dim"], bg=c["bg"],
                     justify="center").pack(expand=True)
            return

        if self.quota and self.quota.error:
            tk.Label(parent, text=f"⚠  {self.quota.error}",
                     font=("Segoe UI", 9), fg=c["danger"], bg=c["bg"],
                     justify="center").pack(expand=True, pady=20)
            return

        if not self.quota:
            tk.Label(parent, text="Fetching…",
                     font=("Segoe UI", 9), fg=c["text_dim"], bg=c["bg"]).pack(expand=True)
            return

        # ── Sıralama: önce TOKENS (aylık), sonra TIME (5 saatlik) ──────────
        # API'den gelen listeyi TOKENS önce gelecek şekilde sıralıyoruz
        sorted_limits = sorted(
            self.quota.limits,
            key=lambda l: 0 if l.type == "TOKENS_LIMIT" else 1
        )
        for limit in sorted_limits:
            self._draw_limit_card(parent, c, limit)

        # Model breakdown
        tl = self.quota.time_limit
        if tl and tl.usage_details:
            tk.Frame(parent, bg=c["border"], height=1).pack(fill="x", padx=14, pady=(10, 4))
            tk.Label(parent, text="MODEL Kullanımları", font=("Segoe UI", 6, "bold"),
                     fg=c["text_muted"], bg=c["bg"]).pack(anchor="w", padx=14)
            for d in tl.usage_details:
                row = tk.Frame(parent, bg=c["bg"])
                row.pack(fill="x", padx=14, pady=1)
                tk.Label(row, text=d.model_code, font=("Segoe UI", 8),
                         fg=c["text_dim"], bg=c["bg"]).pack(side="left")
                tk.Label(row, text=str(d.usage), font=("Segoe UI", 8, "bold"),
                         fg=c["text"], bg=c["bg"]).pack(side="right")

        # Footer
        tk.Frame(parent, bg=c["border"], height=1).pack(fill="x", padx=14, pady=(10, 4))
        now_local = time.strftime('%Y-%m-%d %H:%M:%S',
                                  time.gmtime(time.time() + self.cfg.utc_offset * 3600))
        tk.Label(parent, text=f"Son Güncelleme: {now_local}",
                 font=("Segoe UI", 7), fg=c["text_muted"], bg=c["bg"]).pack(
                 anchor="w", padx=14, pady=(0, 8))

    def _draw_limit_card(self, parent, c, limit):
        card = tk.Frame(parent, bg=c["surface"], bd=0)
        card.pack(fill="x", padx=14, pady=(10, 0))

        hdr = tk.Frame(card, bg=c["surface"])
        hdr.pack(fill="x", padx=10, pady=(8, 2))

        tk.Label(hdr, text=limit.label.upper(), font=("Segoe UI", 7, "bold"),
                 fg=c["text_muted"], bg=c["surface"]).pack(side="left")

        reset_str = limit.next_reset_datetime(self.cfg.utc_offset)
        if reset_str != "—":
            tk.Label(hdr, text=f"Reset: {reset_str}", font=("Segoe UI", 7),
                     fg=c["text_muted"], bg=c["surface"]).pack(side="right")

        pct = limit.percentage
        col = pct_color(pct, c)

        if limit.usage is not None:
            nums = tk.Frame(card, bg=c["surface"])
            nums.pack(fill="x", padx=10, pady=(4, 4))
            tk.Label(nums, text=str(limit.remaining), font=("Segoe UI", 20, "bold"),
                     fg=col, bg=c["surface"]).pack(side="left")
            tk.Label(nums, text=f"/ {limit.usage}", font=("Segoe UI", 10),
                     fg=c["text_dim"], bg=c["surface"]).pack(side="left", padx=(4, 0), pady=4)
            tk.Label(nums, text=f"{pct}% Used", font=("Segoe UI", 8),
                     fg=c["text_dim"], bg=c["surface"]).pack(side="right", pady=4)
        else:
            pct_row = tk.Frame(card, bg=c["surface"])
            pct_row.pack(fill="x", padx=10, pady=(4, 4))
            tk.Label(pct_row, text=f"{pct}% Used", font=("Segoe UI", 9, "bold"),
                     fg=col, bg=c["surface"]).pack(side="left")
            tk.Label(pct_row, text=f"{100 - pct}% Kalan",
                     font=("Segoe UI", 8), fg=c["text_dim"],
                     bg=c["surface"]).pack(side="right")

        bar_c = tk.Canvas(card, height=5, bg=c["surface"], highlightthickness=0, bd=0)
        bar_c.pack(fill="x", padx=10, pady=(0, 10))
        bar_c.update_idletasks()
        w = bar_c.winfo_width() or (self.WIDTH - 52)
        bar_c.create_rectangle(0, 0, w, 5, fill=c["bar_bg"], outline="")
        bar_c.create_rectangle(0, 0, max(1, int(w * pct / 100)), 5, fill=col, outline="")

    def _draw_settings(self, parent, c):
        tk.Label(parent, text="SETTINGS", font=("Segoe UI", 7, "bold"),
                 fg=c["text_muted"], bg=c["bg"]).pack(anchor="w", padx=14, pady=(12, 4))

        def flabel(text):
            tk.Label(parent, text=text, font=("Segoe UI", 8),
                     fg=c["text_dim"], bg=c["bg"]).pack(anchor="w", padx=14)

        def fentry(default, show=None):
            v = tk.StringVar(value=default)
            tk.Entry(parent, textvariable=v, font=("Consolas", 8),
                     bg=c["surface2"], fg=c["text"], insertbackground=c["text"],
                     relief="flat", bd=0, highlightthickness=1,
                     highlightbackground=c["border"], highlightcolor=c["accent"],
                     show=show).pack(fill="x", padx=14, pady=(2, 8), ipady=5)
            return v

        flabel("Bearer Token")
        self.s_token = fentry(self.cfg.bearer_token, show="•")

        flabel("Auto-refresh (seconds, min 5)")
        self.s_interval = fentry(str(self.cfg.refresh_interval))

        flabel("UTC Offset  (e.g. 3 → UTC+3 Turkey)")
        self.s_utc = fentry(str(self.cfg.utc_offset))

        self.s_ontop = tk.BooleanVar(value=self.cfg.always_on_top)
        cb = tk.Frame(parent, bg=c["bg"])
        cb.pack(fill="x", padx=14, pady=(0, 6))
        tk.Checkbutton(cb, text="Always on top", variable=self.s_ontop,
                       font=("Segoe UI", 8), fg=c["text"], bg=c["bg"],
                       activebackground=c["bg"], selectcolor=c["surface2"],
                       relief="flat", bd=0, cursor="hand2").pack(side="left")

        self.s_theme = tk.StringVar(value=self.cfg.theme)
        th = tk.Frame(parent, bg=c["bg"])
        th.pack(fill="x", padx=14, pady=(0, 10))
        tk.Label(th, text="Theme:", font=("Segoe UI", 8),
                 fg=c["text_dim"], bg=c["bg"]).pack(side="left")
        for t in ("dark", "light"):
            tk.Radiobutton(th, text=t.capitalize(), variable=self.s_theme, value=t,
                           font=("Segoe UI", 8), fg=c["text"], bg=c["bg"],
                           activebackground=c["bg"], selectcolor=c["surface2"],
                           relief="flat", bd=0, cursor="hand2").pack(side="left", padx=6)

        tk.Button(parent, text="Save & Apply", font=("Segoe UI", 9, "bold"),
                  fg=c["bg"], bg=c["accent"], activebackground=c["accent2"],
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                  command=self._save_settings).pack(padx=14, pady=(4, 0), anchor="e")

    # ── Actions ─────────────────────────────────────────────────────────────

    def _toggle_collapse(self):
        self.cfg.collapsed = not self.cfg.collapsed
        h = self.COLLAPSED_H if self.cfg.collapsed else self.EXPANDED_H
        self.root.geometry(f"{self.WIDTH}x{h}")
        self._draw_ui()
        self.cfg.save()

    def _toggle_settings(self):
        if self.cfg.collapsed:
            self.cfg.collapsed = False
        self._tab = "settings" if self._tab != "settings" else "monitor"
        h = self.COLLAPSED_H if self.cfg.collapsed else self.EXPANDED_H
        self.root.geometry(f"{self.WIDTH}x{h}")
        self._draw_ui()

    def _save_settings(self):
        self.cfg.bearer_token = self.s_token.get().strip()
        try:
            self.cfg.refresh_interval = max(5, int(self.s_interval.get().strip()))
        except ValueError:
            self.cfg.refresh_interval = 30
        try:
            self.cfg.utc_offset = int(self.s_utc.get().strip())
        except ValueError:
            self.cfg.utc_offset = 0
        self.cfg.always_on_top = self.s_ontop.get()
        self.cfg.theme = self.s_theme.get()
        self.cfg.save()
        self._rebuild_client()
        self.root.attributes("-topmost", self.cfg.always_on_top)
        self._tab = "monitor"
        self._draw_ui()
        self._manual_refresh()

    def _manual_refresh(self):
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _fetch_and_update(self):
        if not self.client:
            return
        data = self.client.get_quota()
        self.root.after(0, lambda: self._on_data(data))

    def _on_data(self, data):
        self.quota = data
        local_ts = time.strftime('%H:%M:%S',
                                 time.gmtime(time.time() + self.cfg.utc_offset * 3600))
        self._last_status = f"Güncel: {local_ts}"
        self._draw_ui()

    def _start_auto_refresh(self):
        self._manual_refresh()
        self._schedule_next()

    def _schedule_next(self):
        self._refresh_job = self.root.after(
            self.cfg.refresh_interval * 1000, self._auto_tick)

    def _auto_tick(self):
        self._manual_refresh()
        self._schedule_next()

    def _drag_start(self, e):
        self._dragging = True
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_motion(self, e):
        if self._dragging:
            self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def _drag_end(self, e):
        self._dragging = False
        self.cfg.window_x = self.root.winfo_x()
        self.cfg.window_y = self.root.winfo_y()
        self.cfg.save()

    def _on_close(self):
        self.cfg.window_x = self.root.winfo_x()
        self.cfg.window_y = self.root.winfo_y()
        self.cfg.save()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ZaiMonitorApp().run()