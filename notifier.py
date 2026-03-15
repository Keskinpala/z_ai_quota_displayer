"""
notifier.py — Z.ai Monitor · Notification Engine v1.3.0

Custom Tkinter toast popup.  Zero external dependencies — only stdlib + tkinter.
Replaces win10toast which is broken on Windows 11.

Features:
  - Fade-in / fade-out animation
  - Drain bar (shows time remaining, pauses on hover)
  - Stacked positioning (no overlap)
  - System sound via winsound (stdlib, Windows only)
  - Click to dismiss
  - Quota threshold alerts (warn / critical with hysteresis)
  - Periodic interval reminders while in tray
"""

import tkinter as tk
import time
import sys

# ── Colour palette (mirrors app.py THEMES) ───────────────────────────────────

_TC = {
    "dark": {
        "surface": "#1e2333",
        "text":    "#e8ecf4",
        "subdued": "#6b7694",
        "trk_bg":  "#2a3045",
    },
    "light": {
        "surface": "#ffffff",
        "text":    "#1a1e2e",
        "subdued": "#5a6485",
        "trk_bg":  "#c8d0e8",
    },
}

_SEV_COLOR = {
    "info":     "#4f8ef7",
    "warn":     "#f59e0b",
    "critical": "#f4566a",
    "ok":       "#22d3a0",
}

# Module-level stack so toasts don't overlap
_stack: list = []


def _live_count() -> int:
    global _stack
    _stack = [t for t in _stack if getattr(t, "_alive", False)]
    return len(_stack)


# ── Toast Window ──────────────────────────────────────────────────────────────

class ToastWindow:
    W      = 310
    H      = 90
    MARGIN = 16
    TBAR   = 52    # reserve for Windows taskbar
    GAP    = 8
    LIFE   = 5.5   # seconds until auto-dismiss

    def __init__(self, root: tk.Tk, title: str, message: str,
                 severity: str = "info", theme: str = "dark",
                 sound: bool = True):
        self._root   = root
        self._alive  = True
        self._slot   = _live_count()
        _stack.append(self)

        c    = _TC.get(theme, _TC["dark"])
        scol = _SEV_COLOR.get(severity, _SEV_COLOR["info"])

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = sw - self.W - self.MARGIN
        y  = sh - self.TBAR - self.H - self._slot * (self.H + self.GAP)

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.0)
        self.win.geometry(f"{self.W}x{self.H}+{x}+{y}")
        self.win.configure(bg=scol)

        # 3 px coloured left stripe + body
        inner = tk.Frame(self.win, bg=c["surface"], padx=10, pady=8)
        inner.place(x=3, y=0, width=self.W - 3, height=self.H)

        tk.Label(inner, text=title, font=("Segoe UI Semibold", 9),
                 fg=scol, bg=c["surface"], anchor="w").pack(fill="x")

        tk.Label(inner, text=message, font=("Segoe UI", 8),
                 fg=c["text"], bg=c["surface"], anchor="w",
                 wraplength=self.W - 32, justify="left").pack(fill="x", pady=(1, 0))

        # Drain bar (time-remaining indicator)
        self._bar = tk.Canvas(inner, height=3, bg=c["surface"],
                              highlightthickness=0, bd=0)
        self._bar.pack(fill="x", pady=(5, 0))
        self._bar_fg  = scol
        self._bar_bg  = c["trk_bg"]

        self.win.bind("<Button-1>", lambda _e: self._dismiss())
        self.win.bind("<Enter>",    self._on_enter)
        self.win.bind("<Leave>",    self._on_leave)

        self._paused   = False
        self._elapsed  = 0.0
        self._last_t   = time.time()

        if sound:
            self._beep(severity)

        self._fade_in()

    # ── Sound ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _beep(severity: str) -> None:
        if sys.platform != "win32":
            return
        try:
            import winsound
            _map = {
                "critical": winsound.MB_ICONHAND,
                "warn":     winsound.MB_ICONEXCLAMATION,
                "ok":       winsound.MB_ICONASTERISK,
            }
            winsound.MessageBeep(_map.get(severity, winsound.MB_OK))
        except Exception:
            pass

    # ── Animation lifecycle ───────────────────────────────────────────────────

    def _fade_in(self, a: float = 0.0) -> None:
        if not self._safe():
            return
        a = min(a + 0.12, 0.95)
        self.win.attributes("-alpha", a)
        if a < 0.95:
            self.win.after(18, lambda: self._fade_in(a))
        else:
            self._last_t = time.time()
            self._tick()

    def _tick(self) -> None:
        if not self._safe():
            return
        now = time.time()
        if not self._paused:
            self._elapsed += now - self._last_t
        self._last_t = now
        remaining = max(0.0, self.LIFE - self._elapsed)

        # Update drain bar
        try:
            self._bar.delete("all")
            self._bar.update_idletasks()
            bw = max(self._bar.winfo_width(), self.W - 36)
            fw = max(1, int(bw * remaining / self.LIFE))
            self._bar.create_rectangle(0, 0, bw, 3, fill=self._bar_bg, outline="")
            self._bar.create_rectangle(0, 0, fw, 3, fill=self._bar_fg, outline="")
        except Exception:
            pass

        if remaining <= 0:
            self._fade_out()
        else:
            self.win.after(50, self._tick)

    def _fade_out(self, a: float = 0.95) -> None:
        if not self._safe():
            return
        a = max(a - 0.14, 0.0)
        self.win.attributes("-alpha", a)
        if a > 0:
            self.win.after(22, lambda: self._fade_out(a))
        else:
            self._dismiss()

    def _dismiss(self) -> None:
        self._alive = False
        try:
            if self.win.winfo_exists():
                self.win.destroy()
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _safe(self) -> bool:
        return self._alive and self.win.winfo_exists()

    def _on_enter(self, _e) -> None:
        self._paused = True

    def _on_leave(self, _e) -> None:
        self._paused = False
        self._last_t = time.time()


# ── Notification Engine ───────────────────────────────────────────────────────

class NotificationEngine:
    """
    Central notification controller.

    Usage:
        engine = NotificationEngine(root, cfg)
        engine.start_interval_loop()        # call once after app init
        engine.check_quota_thresholds(quota) # call after every API fetch
        engine.update_cfg(new_cfg)           # call after settings change
        engine.send(title, msg, severity)    # manual send from anywhere
    """

    def __init__(self, root: tk.Tk, cfg):
        self._root  = root
        self._cfg   = cfg

        # Per-refresh threshold state (reset with hysteresis when quota drops)
        self._warn_fired = False
        self._crit_fired = False

        # Interval reminder state
        self._last_interval_ts = 0.0
        self._interval_job     = None
        self._last_quota       = None   # most recent quota for interval msgs

    # ── Config live update ────────────────────────────────────────────────────

    def update_cfg(self, cfg) -> None:
        self._cfg = cfg

    # ── Unified send ─────────────────────────────────────────────────────────

    def send(self, title: str, message: str, severity: str = "info") -> None:
        """Show a toast notification.  Respects notifications_enabled flag."""
        if not getattr(self._cfg, "notifications_enabled", True):
            return
        sound = getattr(self._cfg, "notify_sound", True)
        theme = getattr(self._cfg, "theme", "dark")
        try:
            ToastWindow(self._root, title, message, severity, theme, sound)
        except Exception:
            pass

    # ── Quota threshold logic ─────────────────────────────────────────────────

    def check_quota_thresholds(self, quota) -> None:
        """Call this after every successful quota fetch."""
        self._last_quota = quota

        if not getattr(self._cfg, "notifications_enabled", True):
            return
        if not quota or quota.error:
            return

        tl = quota.time_limit
        if not tl:
            return

        pct    = tl.percentage
        warn_t = getattr(self._cfg, "warning_threshold",  80)
        crit_t = getattr(self._cfg, "critical_threshold", 95)

        if pct >= crit_t and not self._crit_fired:
            remaining = getattr(tl, "remaining", "?")
            self.send(
                "🔴 Kritik Kota Uyarısı",
                f"5 saatlik kota %{pct} doldu!\n{remaining:,} token kaldı." if isinstance(remaining, int)
                else f"5 saatlik kota %{pct} doldu!",
                "critical",
            )
            self._crit_fired = True
            self._warn_fired = True   # suppress redundant warn toast

        elif pct >= warn_t and not self._warn_fired:
            remaining = getattr(tl, "remaining", "?")
            self.send(
                "⚠ Kota Uyarısı",
                f"5 saatlik kota %{pct} kullanıldı.\n{remaining:,} token kaldı." if isinstance(remaining, int)
                else f"5 saatlik kota %{pct} kullanıldı.",
                "warn",
            )
            self._warn_fired = True

        # Hysteresis: re-arm only when quota drops well below warning
        if pct < max(0, warn_t - 10):
            self._warn_fired = False
            self._crit_fired = False

    # ── Periodic interval reminder ────────────────────────────────────────────

    def start_interval_loop(self) -> None:
        """Start 60-second background ticker for periodic notifications."""
        if self._interval_job:
            try:
                self._root.after_cancel(self._interval_job)
            except Exception:
                pass
        self._reschedule_tick(delay_ms=60_000)

    def _reschedule_tick(self, delay_ms: int = 60_000) -> None:
        try:
            if self._root.winfo_exists():
                self._interval_job = self._root.after(delay_ms, self._tick)
        except Exception:
            pass

    def _tick(self) -> None:
        try:
            self._maybe_interval_notify()
        except Exception:
            pass
        self._reschedule_tick()

    def _maybe_interval_notify(self) -> None:
        interval_min = getattr(self._cfg, "notify_interval_min", 0)
        if interval_min <= 0:
            return

        now = time.time()
        if now - self._last_interval_ts < interval_min * 60:
            return

        self._last_interval_ts = now
        quota = self._last_quota
        lines: list[str] = []

        if quota and not quota.error:
            tl  = quota.time_limit
            tok = quota.token_limit
            if tl:
                rem = f"{tl.remaining:,}" if tl.remaining is not None else "?"
                lines.append(f"5 Saatlik: %{tl.percentage}  •  {rem} kaldı")
            if tok:
                rem = f"{tok.remaining:,}" if tok.remaining is not None else "?"
                lines.append(f"Aylık Token: %{tok.percentage}  •  {rem} kaldı")

        msg = "\n".join(lines) if lines else "Kota bilgisi bekleniyor…"
        self.send("📊 Z.ai Kota Durumu", msg, "info")
