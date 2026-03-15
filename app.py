"""
app.py — Z.ai Monitor
Always-on-top overlay with collapsible panel, settings tab, live quota display.
Features: System tray, custom notifications, 16-language UI, chat launcher.

Author : Inokosha Yazılım — Atakan ÇELİKELLİ
Version: 1.4.0
Run    : python app.py
"""

import tkinter as tk
import threading
import time
import sys
import os
import webbrowser
import subprocess

from zai_client import ZaiClient
from config import AppConfig
from notifier import NotificationEngine
from i18n import t, LANGUAGES

APP_VERSION   = "1.4.1"
APP_AUTHOR    = "Atakan ÇELİKELLİ"
APP_AUTHOR_URL = "https://celikelli.com.tr"
APP_COMPANY   = "Inokosha Yazılım"
APP_COMPANY_URL = "https://inokosha.com.tr"
CHAT_URL      = "https://chat.z.ai"

# Optional imports
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


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
    SETTINGS_H  = 480   # scrollable settings panel (language + chat + about)
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
        
        # System tray
        self._tray_icon = None
        self._hidden = False

        # Notification engine (custom Tkinter toast, no external dep)
        self._notif_engine = NotificationEngine(None, self.cfg)  # root not yet built

        # Clipboard feedback timer
        self._clipboard_job = None

        self._build_window()
        self._notif_engine._root = self.root   # wire root after it's built
        self._draw_ui()
        self._start_auto_refresh()
        self._schedule_blink()
        self._setup_keyboard_shortcuts()
        self._notif_engine.start_interval_loop()

    def _t(self, key: str, **kw) -> str:
        """Shorthand for i18n.t using current language."""
        return t(key, self.cfg.language, **kw)

    def _rebuild_client(self):
        if self.cfg.bearer_token:
            self.client = ZaiClient(self.cfg.bearer_token)
        else:
            self.client = None
    
    # ── Keyboard Shortcuts ──────────────────────────────────────────────────
    
    def _setup_keyboard_shortcuts(self):
        """Bind global keyboard shortcuts."""
        self.root.bind("<Control-r>", lambda e: self._manual_refresh())
        self.root.bind("<Control-R>", lambda e: self._manual_refresh())
        self.root.bind("<Escape>", lambda e: self._minimize_to_tray() if self.cfg.minimize_to_tray else None)
        self.root.bind("<Control-q>", lambda e: self._force_close())
        self.root.bind("<Control-Q>", lambda e: self._force_close())
        self.root.bind("<Control-comma>", lambda e: self._toggle_settings())
        self.root.bind("<Control-w>", lambda e: self._open_chat())
        self.root.bind("<Control-W>", lambda e: self._open_chat())
        self.root.bind("<Control-Shift-r>", lambda e: self._restart_app())
        self.root.bind("<Control-Shift-R>", lambda e: self._restart_app())
    
    # ── System Tray ─────────────────────────────────────────────────────────
    
    def _create_tray_icon(self):
        """Create a simple tray icon image."""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a Z letter
        c = THEMES[self.cfg.theme]
        color = c["accent"]
        # Convert hex to RGB tuple
        if color.startswith("#"):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            color = (r, g, b, 255)
        
        # Draw background circle
        draw.ellipse([4, 4, size-4, size-4], fill=(26, 26, 46, 255))
        # Draw Z letter
        draw.text((20, 12), "Z", fill=color)
        return image
    
    def _setup_tray(self):
        """Initialize system tray icon."""
        if not TRAY_AVAILABLE:
            return

        def on_show(icon, item):
            self.root.after(0, self._show_from_tray)

        def on_refresh(icon, item):
            self.root.after(0, self._manual_refresh)

        def on_status(icon, item):
            self.root.after(0, lambda: self._notif_engine._maybe_interval_notify())

        def on_chat(icon, item):
            self.root.after(0, self._open_chat_browser)

        def on_restart(icon, item):
            icon.stop()
            self.root.after(0, self._restart_app)

        def on_quit(icon, item):
            icon.stop()
            self.root.after(0, self._force_close)

        lang = self.cfg.language
        menu = pystray.Menu(
            pystray.MenuItem(t("tray_show",   lang), on_show, default=True),
            pystray.MenuItem(t("tray_refresh", lang), on_refresh),
            pystray.MenuItem(t("tray_quota_status", lang), on_status),
            pystray.MenuItem(t("tray_open_chat", lang), on_chat),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray_restart", lang), on_restart),
            pystray.MenuItem(t("tray_quit",   lang), on_quit),
        )

        self._tray_icon = pystray.Icon(
            "zai_monitor",
            self._create_tray_icon(),
            "Z.ai Monitor",
            menu,
        )
    
    def _minimize_to_tray(self):
        """Hide window and show tray icon."""
        if not TRAY_AVAILABLE or not self.cfg.minimize_to_tray:
            return
        
        self._hidden = True
        self.root.withdraw()
        
        if not self._tray_icon:
            self._setup_tray()
        
        if self._tray_icon and not self._tray_icon.visible:
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
    
    def _show_from_tray(self):
        """Show window from tray."""
        self._hidden = False
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.cfg.always_on_top)
        if self._tray_icon:
            self._tray_icon.stop()
    
    def _force_close(self):
        """Save state and exit the application cleanly."""
        self._save_position()
        try:
            if self._tray_icon:
                self._tray_icon.stop()
        except Exception:
            pass
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def _restart_app(self):
        """Save state and restart the application."""
        self._save_position()
        try:
            if self._tray_icon:
                self._tray_icon.stop()
        except Exception:
            pass
        self.root.quit()
        self.root.destroy()
        # Re-launch same interpreter with same arguments
        executable = sys.executable
        args = sys.argv[:]
        os.execv(executable, [executable] + args)

    def _save_position(self):
        """Persist current window position."""
        try:
            self.cfg.window_x = self.root.winfo_x()
            self.cfg.window_y = self.root.winfo_y()
            self.cfg.save()
        except Exception:
            pass
    
    # ── Notifications ───────────────────────────────────────────────────────

    # Handled entirely by NotificationEngine in notifier.py

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

    def _current_h(self) -> int:
        """Return correct window height for current state."""
        if self.cfg.collapsed:
            return self.COLLAPSED_H
        if self._tab == "settings":
            return self.SETTINGS_H
        return self.EXPANDED_H

    # ── UI Draw ─────────────────────────────────────────────────────────────

    def _draw_ui(self):
        for w in self.root.winfo_children():
            w.destroy()
        c = THEMES[self.cfg.theme]
        self.root.configure(bg=c["bg"])
        # Resize to correct height for current view
        self.root.geometry(f"{self.WIDTH}x{self._current_h()}")

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
        tk.Button(bar, text="💬", fg=c["accent2"],
                  activeforeground=c["accent"], activebackground=c["title_bg"],
                  command=self._open_chat, **btn_cfg).pack(side="right")
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

        # Copy quota to clipboard
        if self.quota and not getattr(self.quota, "error", True):
            tk.Button(top, text="📋", font=("Segoe UI", 8),
                      fg=c["text_dim"], bg=c["bg"], relief="flat", bd=0,
                      activeforeground=c["accent"], activebackground=c["bg"],
                      padx=4, pady=0, cursor="hand2",
                      command=self._copy_to_clipboard).pack(side="right", padx=(0, 2))

        tk.Button(top, text=self._t("refresh"), font=("Segoe UI", 7),
                  fg=c["accent"], bg=c["surface2"], relief="flat", bd=0,
                  activeforeground=c["accent"], activebackground=c["border"],
                  padx=8, pady=2, cursor="hand2",
                  command=self._manual_refresh).pack(side="right")

        tk.Frame(parent, bg=c["border"], height=1).pack(fill="x", padx=14, pady=(8, 0))

        if not self.cfg.bearer_token:
            tk.Label(parent, text=self._t("no_token"),
                     font=("Segoe UI", 9), fg=c["text_dim"], bg=c["bg"],
                     justify="center").pack(expand=True)
            return

        if self.quota and self.quota.error:
            tk.Label(parent, text=f"⚠  {self.quota.error}",
                     font=("Segoe UI", 9), fg=c["danger"], bg=c["bg"],
                     justify="center").pack(expand=True, pady=20)
            return

        if not self.quota:
            tk.Label(parent, text=self._t("fetching"),
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
            tk.Label(parent, text=self._t("model_usage"), font=("Segoe UI", 6, "bold"),
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
        tk.Label(parent, text=self._t("last_update", ts=now_local),
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
        # Settings panel lives inside a scrollable canvas so no content is clipped
        canvas = tk.Canvas(parent, bg=c["bg"], highlightthickness=0, bd=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                          bg=c["surface2"], troughcolor=c["bg"],
                          activebackground=c["border"], width=8)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=c["bg"])
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _on_resize)

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_frame_configure)

        # Mousewheel scroll — unbind on destroy to prevent stale callback errors
        def _on_mousewheel(e):
            try:
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except tk.TclError:
                pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        p = inner  # shorthand alias

        # ── Helpers ──────────────────────────────────────────────────────────
        def flbl(txt):
            tk.Label(p, text=txt, font=("Segoe UI", 8),
                     fg=c["text_dim"], bg=c["bg"]).pack(anchor="w", padx=14)

        def fent(var, par=None, show=None, width=None, justify="left"):
            par = par or p
            kw = dict(textvariable=var, font=("Consolas", 8),
                      bg=c["surface2"], fg=c["text"], insertbackground=c["text"],
                      relief="flat", bd=0, justify=justify)
            if show:
                kw["show"] = show
            if width:
                kw["width"] = width
            return tk.Entry(par, **kw)

        def sep():
            tk.Frame(p, bg=c["border"], height=1).pack(fill="x", padx=14, pady=(6, 0))

        def section_hdr(key):
            tk.Label(p, text=self._t(key), font=("Segoe UI", 7, "bold"),
                     fg=c["text_dim"], bg=c["bg"]).pack(anchor="w", padx=14, pady=(8, 2))

        cb_kw = dict(font=("Segoe UI", 8), fg=c["text"], bg=c["bg"],
                     activebackground=c["bg"], selectcolor=c["surface2"],
                     relief="flat", bd=0, cursor="hand2")
        se_kw = dict(font=("Consolas", 8), bg=c["surface2"], fg=c["text"],
                     insertbackground=c["text"], relief="flat", bd=0, justify="center")
        lbl_kw = dict(font=("Segoe UI", 7), fg=c["text_dim"], bg=c["bg"])

        # ── Section: Settings ─────────────────────────────────────────────────
        section_hdr("settings_title")

        # Bearer Token
        flbl(self._t("bearer_token"))
        self.s_token = tk.StringVar(value=self.cfg.bearer_token)
        e = fent(self.s_token, show="•")
        e.configure(highlightthickness=1,
                    highlightbackground=c["border"], highlightcolor=c["accent"])
        e.pack(fill="x", padx=14, pady=(2, 6), ipady=3)

        # Refresh + UTC on same row
        ru = tk.Frame(p, bg=c["bg"])
        ru.pack(fill="x", padx=14, pady=(0, 4))
        tk.Label(ru, text=self._t("refresh_sn"), font=("Segoe UI", 8),
                 fg=c["text_dim"], bg=c["bg"]).pack(side="left")
        self.s_interval = tk.StringVar(value=str(self.cfg.refresh_interval))
        fent(self.s_interval, par=ru, width=4, justify="center").pack(
            side="left", padx=(3, 0), ipady=3)
        tk.Label(ru, text=self._t("sec") + "   " + self._t("utc"), font=("Segoe UI", 8),
                 fg=c["text_dim"], bg=c["bg"]).pack(side="left")
        self.s_utc = tk.StringVar(value=str(self.cfg.utc_offset))
        fent(self.s_utc, par=ru, width=3, justify="center").pack(
            side="left", padx=(3, 0), ipady=3)

        sep()

        # Checkbox row 1: window behaviour
        r1 = tk.Frame(p, bg=c["bg"])
        r1.pack(fill="x", padx=14, pady=(6, 2))
        self.s_ontop = tk.BooleanVar(value=self.cfg.always_on_top)
        tk.Checkbutton(r1, text=self._t("always_on_top"), variable=self.s_ontop,
                       **cb_kw).pack(side="left")
        self.s_tray = tk.BooleanVar(value=self.cfg.minimize_to_tray)
        tk.Checkbutton(r1, text=self._t("tray"), variable=self.s_tray,
                       state="normal" if TRAY_AVAILABLE else "disabled",
                       **cb_kw).pack(side="left", padx=(10, 0))
        self.s_autostart = tk.BooleanVar(value=self.cfg.auto_start)
        tk.Checkbutton(r1, text=self._t("autostart"), variable=self.s_autostart,
                       state="normal" if sys.platform == "win32" else "disabled",
                       **cb_kw).pack(side="left", padx=(10, 0))

        # Checkbox row 2: notifications
        r2 = tk.Frame(p, bg=c["bg"])
        r2.pack(fill="x", padx=14, pady=(0, 4))
        self.s_notify = tk.BooleanVar(value=self.cfg.notifications_enabled)
        tk.Checkbutton(r2, text=self._t("notifications"), variable=self.s_notify,
                       **cb_kw).pack(side="left")
        self.s_sound = tk.BooleanVar(value=self.cfg.notify_sound)
        tk.Checkbutton(r2, text=self._t("sound"), variable=self.s_sound,
                       state="normal" if sys.platform == "win32" else "disabled",
                       **cb_kw).pack(side="left", padx=(10, 0))

        # Warn / Crit / Interval thresholds
        thr = tk.Frame(p, bg=c["bg"])
        thr.pack(fill="x", padx=14, pady=(0, 4))
        tk.Label(thr, text=self._t("warn_threshold"), **lbl_kw).pack(side="left")
        self.s_warn = tk.StringVar(value=str(self.cfg.warning_threshold))
        tk.Entry(thr, textvariable=self.s_warn, width=3, **se_kw).pack(
            side="left", padx=(2, 0), ipady=2)
        tk.Label(thr, text="%  " + self._t("crit_threshold"), **lbl_kw).pack(side="left", padx=(4, 0))
        self.s_crit = tk.StringVar(value=str(self.cfg.critical_threshold))
        tk.Entry(thr, textvariable=self.s_crit, width=3, **se_kw).pack(
            side="left", padx=(2, 0), ipady=2)
        tk.Label(thr, text="%  " + self._t("interval_min"), **lbl_kw).pack(side="left", padx=(4, 0))
        self.s_notif_interval = tk.StringVar(value=str(self.cfg.notify_interval_min))
        tk.Entry(thr, textvariable=self.s_notif_interval, width=3, **se_kw).pack(
            side="left", padx=(2, 0), ipady=2)
        tk.Label(thr, text=self._t("interval_off"), **lbl_kw).pack(side="left", padx=(2, 0))

        sep()

        # Theme + Opacity + Language on same row
        ta = tk.Frame(p, bg=c["bg"])
        ta.pack(fill="x", padx=14, pady=(6, 4))
        tk.Label(ta, text=self._t("theme"), font=("Segoe UI", 8),
                 fg=c["text_dim"], bg=c["bg"]).pack(side="left")
        self.s_theme = tk.StringVar(value=self.cfg.theme)
        for th in ("dark", "light"):
            tk.Radiobutton(ta, text=th.capitalize(), variable=self.s_theme, value=th,
                           font=("Segoe UI", 8), fg=c["text"], bg=c["bg"],
                           activebackground=c["bg"], selectcolor=c["surface2"],
                           relief="flat", bd=0, cursor="hand2").pack(side="left", padx=(4, 0))
        tk.Label(ta, text="  " + self._t("opacity"), font=("Segoe UI", 8),
                 fg=c["text_dim"], bg=c["bg"]).pack(side="left")
        self.s_opacity = tk.StringVar(value=str(self.cfg.opacity))
        tk.Entry(ta, textvariable=self.s_opacity, width=4, **se_kw).pack(
            side="left", padx=(3, 0), ipady=2)

        # Language selector row
        lr = tk.Frame(p, bg=c["bg"])
        lr.pack(fill="x", padx=14, pady=(4, 4))
        tk.Label(lr, text=self._t("language"), font=("Segoe UI", 8),
                 fg=c["text_dim"], bg=c["bg"]).pack(side="left")
        self.s_lang = tk.StringVar(value=self.cfg.language)
        lang_names = [f"{code} – {name}" for code, name in LANGUAGES.items()]
        lang_codes = list(LANGUAGES.keys())
        cur_idx    = lang_codes.index(self.cfg.language) if self.cfg.language in lang_codes else 0

        lang_om = tk.OptionMenu(lr, self.s_lang, *lang_codes)
        lang_om.configure(font=("Segoe UI", 8), bg=c["surface2"], fg=c["text"],
                          activebackground=c["border"], activeforeground=c["text"],
                          relief="flat", bd=0, cursor="hand2",
                          highlightthickness=0, indicatoron=True)
        lang_om["menu"].configure(font=("Segoe UI", 8), bg=c["surface2"], fg=c["text"])
        lang_om.pack(side="left", padx=(6, 0))

        # Show language native name next to code
        lang_name_lbl = tk.Label(lr, text=LANGUAGES.get(self.cfg.language, ""),
                                 font=("Segoe UI", 8), fg=c["accent"], bg=c["bg"])
        lang_name_lbl.pack(side="left", padx=(6, 0))

        def _update_lang_name(*_):
            lang_name_lbl.configure(text=LANGUAGES.get(self.s_lang.get(), ""))
        self.s_lang.trace_add("write", _update_lang_name)

        sep()

        # ── Section: Chat ─────────────────────────────────────────────────────
        section_hdr("chat_section")

        cr = tk.Frame(p, bg=c["bg"])
        cr.pack(fill="x", padx=14, pady=(2, 2))
        self.s_chat_mode = tk.StringVar(value=self.cfg.chat_mode)
        tk.Radiobutton(cr, text=self._t("chat_browser"), variable=self.s_chat_mode,
                       value="browser", **dict(font=("Segoe UI", 8), fg=c["text"],
                       bg=c["bg"], activebackground=c["bg"], selectcolor=c["surface2"],
                       relief="flat", bd=0, cursor="hand2")).pack(side="left")
        tk.Radiobutton(cr, text=self._t("chat_local"), variable=self.s_chat_mode,
                       value="builtin", **dict(font=("Segoe UI", 8), fg=c["text"],
                       bg=c["bg"], activebackground=c["bg"], selectcolor=c["surface2"],
                       relief="flat", bd=0, cursor="hand2")).pack(side="left", padx=(12, 0))

        tk.Label(p, text=self._t("chat_note"), font=("Segoe UI", 7),
                 fg=c["text_dim"], bg=c["bg"], wraplength=self.WIDTH - 40,
                 justify="left").pack(anchor="w", padx=14, pady=(2, 0))

        cb_row = tk.Frame(p, bg=c["bg"])
        cb_row.pack(fill="x", padx=14, pady=(6, 2))
        tk.Button(cb_row, text=self._t("chat_browser"), font=("Segoe UI", 8),
                  fg=c["bg"], bg=c["accent2"], activebackground=c["accent"],
                  relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                  command=self._open_chat_browser).pack(side="left")
        tk.Button(cb_row, text=self._t("chat_local"), font=("Segoe UI", 8),
                  fg=c["bg"], bg=c["accent"], activebackground=c["accent2"],
                  relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                  command=self._open_chat_builtin).pack(side="left", padx=(8, 0))

        sep()

        # ── Section: About ────────────────────────────────────────────────────
        section_hdr("about_section")

        def _link(text, url, font=("Segoe UI", 8), fg=None):
            lbl = tk.Label(p, text=text, font=font, fg=fg or c["accent"],
                           bg=c["bg"], cursor="hand2")
            lbl.pack(anchor="w", padx=14)
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
            # Subtle underline on hover
            lbl.bind("<Enter>", lambda e: lbl.configure(
                font=(font[0], font[1], "underline")))
            lbl.bind("<Leave>", lambda e: lbl.configure(font=font))

        tk.Label(p, text="Z.ai Monitor", font=("Segoe UI Semibold", 11),
                 fg=c["accent"], bg=c["bg"]).pack(anchor="w", padx=14)
        tk.Label(p, text=f"v{APP_VERSION}", font=("Segoe UI", 8),
                 fg=c["text_dim"], bg=c["bg"]).pack(anchor="w", padx=14)

        tk.Frame(p, bg=c["bg"], height=4).pack()

        tk.Label(p, text=APP_AUTHOR, font=("Segoe UI", 9, "bold"),
                 fg=c["text"], bg=c["bg"]).pack(anchor="w", padx=14)
        _link("celikelli.com.tr", "https://celikelli.com.tr",
              font=("Segoe UI", 8), fg=c["accent"])

        tk.Frame(p, bg=c["bg"], height=4).pack()

        tk.Label(p, text=APP_COMPANY, font=("Segoe UI", 8, "bold"),
                 fg=c["accent2"], bg=c["bg"]).pack(anchor="w", padx=14)
        _link("inokosha.com.tr", "https://inokosha.com.tr",
              font=("Segoe UI", 8), fg=c["accent2"])

        tk.Frame(p, bg=c["bg"], height=4).pack()
        _link(CHAT_URL, CHAT_URL, font=("Segoe UI", 7), fg=c["text_muted"])

        sep()

        # ── Save button ───────────────────────────────────────────────────────
        btn_row = tk.Frame(p, bg=c["bg"])
        btn_row.pack(fill="x", padx=14, pady=(8, 12))
        tk.Button(btn_row, text=self._t("tray_restart"), font=("Segoe UI", 8),
                  fg=c["text"], bg=c["surface2"], activebackground=c["border"],
                  relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
                  command=self._restart_app).pack(side="left")
        tk.Button(btn_row, text=self._t("save"), font=("Segoe UI", 9, "bold"),
                  fg=c["bg"], bg=c["accent"], activebackground=c["accent2"],
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                  command=self._save_settings).pack(side="right")

    # ── Actions ─────────────────────────────────────────────────────────────

    def _copy_to_clipboard(self):
        """Copy a quota snapshot as plain text to the clipboard."""
        if not self.quota or self.quota.error:
            return
        ts   = time.strftime('%Y-%m-%d %H:%M:%S',
                              time.gmtime(time.time() + self.cfg.utc_offset * 3600))
        lines = [f"Z.ai Quota Snapshot – {ts}"]
        tl = self.quota.time_limit
        tok = self.quota.token_limit
        if tl:
            rem = f"{tl.remaining:,}" if tl.remaining is not None else "?"
            lines.append(f"5h: %{tl.percentage} | {rem} remaining")
        if tok:
            rem = f"{tok.remaining:,}" if tok.remaining is not None else "?"
            lines.append(f"Monthly: %{tok.percentage} | {rem} remaining")
        lines.append(f"Level: {self.quota.level}")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        # Brief status feedback
        old = self._last_status
        self._last_status = self._t("copied")
        try:
            self.status_lbl.configure(text=self._last_status)
        except Exception:
            pass
        if self._clipboard_job:
            self.root.after_cancel(self._clipboard_job)
        def _restore():
            self._last_status = old
            try:
                self.status_lbl.configure(text=self._last_status)
            except Exception:
                pass
        self._clipboard_job = self.root.after(2200, _restore)

    @staticmethod
    def _apply_autostart(enabled: bool) -> None:
        """Add or remove the app from Windows startup registry."""
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "ZaiMonitor"
            access   = winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, access)
            if enabled:
                if getattr(sys, "frozen", False):
                    path = f'"{sys.executable}"'
                else:
                    path = f'"{sys.executable}" "{os.path.abspath("app.py")}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass

    def _toggle_collapse(self):
        self.cfg.collapsed = not self.cfg.collapsed
        h = self._current_h()
        self.root.geometry(f"{self.WIDTH}x{h}")
        self._draw_ui()
        self.cfg.save()

    def _toggle_settings(self):
        if self.cfg.collapsed:
            self.cfg.collapsed = False
        self._tab = "settings" if self._tab != "settings" else "monitor"
        h = self._current_h()
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
        try:
            self.cfg.opacity = max(0.1, min(1.0, float(self.s_opacity.get().strip())))
        except ValueError:
            self.cfg.opacity = 0.95
        try:
            self.cfg.warning_threshold  = max(1, min(99,  int(self.s_warn.get().strip())))
        except ValueError:
            self.cfg.warning_threshold  = 80
        try:
            self.cfg.critical_threshold = max(1, min(100, int(self.s_crit.get().strip())))
        except ValueError:
            self.cfg.critical_threshold = 95
        try:
            self.cfg.notify_interval_min = max(0, int(self.s_notif_interval.get().strip()))
        except ValueError:
            self.cfg.notify_interval_min = 0

        self.cfg.always_on_top         = self.s_ontop.get()
        self.cfg.minimize_to_tray      = self.s_tray.get()
        self.cfg.auto_start            = self.s_autostart.get()
        self.cfg.notifications_enabled = self.s_notify.get()
        self.cfg.notify_sound          = self.s_sound.get()
        self.cfg.theme                 = self.s_theme.get()
        self.cfg.language              = self.s_lang.get()
        self.cfg.chat_mode             = self.s_chat_mode.get()

        # Apply Windows autostart
        self._apply_autostart(self.cfg.auto_start)

        self.cfg.save()
        self._rebuild_client()
        self._notif_engine.update_cfg(self.cfg)
        self.root.attributes("-topmost", self.cfg.always_on_top)
        self.root.attributes("-alpha",   self.cfg.opacity)
        self._tab = "monitor"
        self._draw_ui()
        self._manual_refresh()

    def _manual_refresh(self):
        """Trigger immediate API fetch and reset the auto-refresh timer."""
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        self._schedule_next()  # Always restart the countdown from now

    def _fetch_and_update(self):
        if not self.client:
            return
        data = self.client.get_quota()
        self.root.after(0, lambda: self._on_data(data))

    def _on_data(self, data):
        self.quota = data
        local_ts = time.strftime('%H:%M:%S',
                                 time.gmtime(time.time() + self.cfg.utc_offset * 3600))
        self._last_status = self._t("updated_status", ts=local_ts)
        self._draw_ui()
        # Check notifications
        self._notif_engine.check_quota_thresholds(data)
        # Update tray tooltip with current quota
        if self._tray_icon and self._tray_icon.visible:
            try:
                tl = data.time_limit
                if tl and not data.error:
                    self._tray_icon.title = f"Z.ai Monitor — 5h: %{tl.percentage}"
            except Exception:
                pass

    def _start_auto_refresh(self):
        # _manual_refresh now calls _schedule_next internally
        self._manual_refresh()

    def _schedule_next(self):
        self._refresh_job = self.root.after(
            self.cfg.refresh_interval * 1000, self._auto_tick)

    def _auto_tick(self):
        """Called by scheduler — fetch data and schedule next tick."""
        self._refresh_job = None
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
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
        self._save_position()

    def _on_close(self):
        """Handle window close button: minimize to tray or quit."""
        if TRAY_AVAILABLE and self.cfg.minimize_to_tray:
            self._minimize_to_tray()
        else:
            self._force_close()

    # ── Chat Launcher ────────────────────────────────────────────────────────

    def _open_chat_browser(self):
        """Open chat.z.ai in the system default browser (no auto-login)."""
        webbrowser.open(CHAT_URL)

    def _open_chat_builtin(self):
        """Open chat.z.ai in Chrome/Edge --app mode (no tabs, no address bar).

        This is the "built-in feel" option: a clean, frameless browser window
        scoped to chat.z.ai.  No token is injected; the user logs in manually.
        Falls back to the system default browser if Chrome/Edge is not found.
        """
        candidates = [
            # Chrome (user install)
            os.path.expandvars(
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            # Chrome (system install)
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            # Edge (usually pre-installed on Windows 10/11)
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(
                r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for exe in candidates:
            if os.path.isfile(exe):
                try:
                    subprocess.Popen(
                        [exe, f"--app={CHAT_URL}", "--disable-extensions"],
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    return
                except Exception:
                    pass
        # No Chromium-based browser found → fallback
        self._open_chat_browser()

    def _open_chat(self):
        """Route to builtin or browser based on config."""
        if self.cfg.chat_mode == "builtin":
            self._open_chat_builtin()
        else:
            self._open_chat_browser()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ZaiMonitorApp().run()