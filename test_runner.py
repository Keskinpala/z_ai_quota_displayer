"""
test_runner.py  —  Z.ai Monitor · Local Build & Test Verification UI
Run this before doing a PyInstaller build to verify everything is healthy.

Usage:
    python test_runner.py
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess
import sys
import os
import time
import py_compile

# ── Theme ────────────────────────────────────────────────────────────────────

CLR = {
    "bg":       "#0d0f14",
    "surface":  "#161a24",
    "surface2": "#1e2333",
    "border":   "#2a3045",
    "accent":   "#4f8ef7",
    "accent2":  "#a78bfa",
    "text":     "#e8ecf4",
    "text_dim": "#6b7694",
    "ok":       "#22d3a0",
    "warn":     "#f59e0b",
    "danger":   "#f4566a",
    "title_bg": "#0a0c12",
}

# ── Test registry ─────────────────────────────────────────────────────────────

TESTS: list = []


def test(label: str):
    """Decorator to register a test function."""
    def decorator(fn):
        TESTS.append((label, fn))
        return fn
    return decorator


# ── Individual tests ──────────────────────────────────────────────────────────

@test("Python version ≥ 3.8")
def _t_python():
    v = sys.version_info
    if v < (3, 8):
        raise RuntimeError(f"Python {v.major}.{v.minor} < 3.8")
    return f"Python {v.major}.{v.minor}.{v.micro}"


@test("requests import")
def _t_requests():
    import requests  # noqa: F401
    return requests.__version__


@test("tkinter import")
def _t_tkinter():
    import tkinter as tk_  # noqa: F401
    return f"Tk {tk_.TkVersion}"


@test("zai_client import")
def _t_zai_client():
    from zai_client import ZaiClient, QuotaData, LimitInfo  # noqa: F401
    return "OK"


@test("config import")
def _t_config():
    from config import AppConfig  # noqa: F401
    return "OK"


@test("AppConfig round-trip (save/load)")
def _t_config_rw():
    from config import AppConfig
    sentinel = "test_runner_sentinel_42"
    cfg = AppConfig.load()
    original_token = cfg.bearer_token
    cfg.bearer_token = sentinel
    cfg.refresh_interval = 99
    cfg.save()
    loaded = AppConfig.load()
    assert loaded.bearer_token == sentinel, "bearer_token mismatch"
    assert loaded.refresh_interval == 99, "refresh_interval mismatch"
    # Restore
    cfg.bearer_token = original_token
    cfg.refresh_interval = 30
    cfg.save()
    return "Read/Write OK"


@test("ZaiClient init (empty token)")
def _t_client_empty():
    from zai_client import ZaiClient
    ZaiClient("")
    return "Init OK"


@test("ZaiClient invalid-token → graceful error")
def _t_client_invalid():
    from zai_client import ZaiClient
    quota = ZaiClient("invalid_test_token_runner").get_quota()
    if quota.error:
        return f"Error handled: {quota.error[:35]}"
    return "No error (token may actually be valid)"


@test("pystray + Pillow  (optional, tray feature)")
def _t_pystray():
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
        return f"pystray {pystray.__version__}  +  Pillow OK"
    except ImportError as e:
        return f"SKIP – not installed  ({e})"


@test("notifier.py  — import (custom toast)")
def _t_notifier():
    from notifier import NotificationEngine, ToastWindow  # noqa: F401
    return "notifier.py OK"


@test("i18n.py  — 16 languages present")
def _t_i18n():
    from i18n import LANGUAGES, t
    assert len(LANGUAGES) == 16, f"Expected 16 langs, got {len(LANGUAGES)}"
    sample = t("app_title", "tr")
    assert sample, "Empty translation"
    return f"i18n OK ({len(LANGUAGES)} langs)"


@test("app.py  — syntax")
def _t_syntax_app():
    py_compile.compile("app.py", doraise=True)
    return "Syntax OK"


@test("mascot.py  — syntax")
def _t_syntax_mascot():
    if not os.path.exists("mascot.py"):
        return "SKIP (mascot.py not found)"
    py_compile.compile("mascot.py", doraise=True)
    return "Syntax OK"


@test("config.py  — syntax")
def _t_syntax_config():
    py_compile.compile("config.py", doraise=True)
    return "Syntax OK"


@test("zai_client.py  — syntax")
def _t_syntax_client():
    py_compile.compile("zai_client.py", doraise=True)
    return "Syntax OK"


@test("PyInstaller available")
def _t_pyinstaller():
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        capture_output=True, text=True, timeout=15,
    )
    if r.returncode == 0:
        return f"PyInstaller {r.stdout.strip()}"
    raise RuntimeError("Not found — run: pip install pyinstaller")


@test("app.spec exists")
def _t_spec():
    if not os.path.exists("app.spec"):
        raise FileNotFoundError("app.spec missing")
    return "Found"


# ── GUI Application ───────────────────────────────────────────────────────────

class TestRunnerApp:
    _W, _H = 640, 680

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Z.ai Monitor  —  Build Test Runner")
        self.root.configure(bg=CLR["bg"])
        self.root.geometry(f"{self._W}x{self._H}")
        self.root.resizable(True, True)
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        c = CLR

        # Header
        hdr = tk.Frame(self.root, bg=c["title_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="●  Z.ai Monitor — Build Verification",
                 font=("Segoe UI Semibold", 12), fg=c["accent"],
                 bg=c["title_bg"], padx=14, pady=10).pack(side="left")

        # Button row
        btn_f = tk.Frame(self.root, bg=c["bg"])
        btn_f.pack(fill="x", padx=14, pady=10)

        def mkbtn(parent, label, bg, cmd):
            tk.Button(parent, text=label, font=("Segoe UI", 9, "bold"),
                      fg=c["bg"], bg=bg, relief="flat", bd=0,
                      padx=16, pady=6, cursor="hand2",
                      command=cmd).pack(side="left", padx=(0, 8))

        mkbtn(btn_f, "▶  Run All Tests", c["accent"], self._run_tests)
        mkbtn(btn_f, "🏗  Build EXE",     c["warn"],   self._run_build)
        mkbtn(btn_f, "🚀  Launch App",    c["ok"],     self._launch_app)

        self._status_lbl = tk.Label(btn_f, text="Ready",
                                    font=("Segoe UI", 8), fg=c["text_dim"],
                                    bg=c["bg"])
        self._status_lbl.pack(side="right")

        tk.Frame(self.root, bg=c["border"], height=1).pack(fill="x", padx=14)

        # ── Test result rows ─────────────────────────────────────────────────
        results_frame = tk.Frame(self.root, bg=c["bg"])
        results_frame.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(results_frame, text="TEST RESULTS",
                 font=("Segoe UI", 7, "bold"), fg=c["text_dim"],
                 bg=c["bg"]).pack(anchor="w")

        rows_container = tk.Frame(results_frame, bg=c["bg"])
        rows_container.pack(fill="x", pady=(4, 0))

        self._rows: dict[str, tuple] = {}
        for label, _ in TESTS:
            row = tk.Frame(rows_container, bg=c["surface"], pady=1)
            row.pack(fill="x", pady=1)

            dot = tk.Label(row, text="○", font=("Segoe UI", 10),
                           fg=c["text_dim"], bg=c["surface"], width=2)
            dot.pack(side="left", padx=(8, 4))

            name_lbl = tk.Label(row, text=label, font=("Segoe UI", 8),
                                fg=c["text_dim"], bg=c["surface"],
                                width=34, anchor="w")
            name_lbl.pack(side="left")

            result_lbl = tk.Label(row, text="—", font=("Segoe UI", 7),
                                  fg=c["text_dim"], bg=c["surface"], anchor="w")
            result_lbl.pack(side="left", padx=4)

            self._rows[label] = (dot, name_lbl, result_lbl)

        # ── Log area ─────────────────────────────────────────────────────────
        tk.Frame(self.root, bg=c["border"], height=1).pack(fill="x", padx=14, pady=(10, 0))
        log_frame = tk.Frame(self.root, bg=c["bg"])
        log_frame.pack(fill="both", expand=True, padx=14, pady=(6, 10))

        tk.Label(log_frame, text="BUILD LOG",
                 font=("Segoe UI", 7, "bold"), fg=c["text_dim"],
                 bg=c["bg"]).pack(anchor="w")

        self._log = scrolledtext.ScrolledText(
            log_frame, height=10,
            font=("Consolas", 8),
            bg=c["surface"], fg=c["text"],
            insertbackground=c["text"],
            relief="flat", bd=0, state="disabled",
        )
        self._log.pack(fill="both", expand=True, pady=(4, 0))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _log_write(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_status(self, text: str, color: str | None = None):
        self._status_lbl.configure(text=text, fg=color or CLR["text_dim"])

    # ── Actions ──────────────────────────────────────────────────────────────

    def _run_tests(self):
        self._set_status("Running…", CLR["warn"])
        threading.Thread(target=self._exec_tests, daemon=True).start()

    def _exec_tests(self):
        c = CLR
        passed = failed = 0
        self._log_write("=" * 52)
        self._log_write(f"Test run  {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log_write("=" * 52)

        for label, fn in TESTS:
            dot, name_lbl, result_lbl = self._rows[label]

            # Mark as running
            self.root.after(0, lambda d=dot, n=name_lbl: (
                d.configure(text="◌", fg=c["warn"]),
                n.configure(fg=c["text"]),
            ))

            try:
                result_str = fn()
                passed += 1
                self.root.after(0, lambda d=dot, n=name_lbl, r=result_lbl, res=result_str: (
                    d.configure(text="●", fg=c["ok"]),
                    n.configure(fg=c["text"]),
                    r.configure(text=str(res)[:46], fg=c["ok"]),
                ))
                self._log_write(f"  ✓  {label}: {result_str}")
            except Exception as exc:
                failed += 1
                err = str(exc)[:60]
                self.root.after(0, lambda d=dot, n=name_lbl, r=result_lbl, e=err: (
                    d.configure(text="✗", fg=c["danger"]),
                    n.configure(fg=c["danger"]),
                    r.configure(text=e, fg=c["danger"]),
                ))
                self._log_write(f"  ✗  {label}: {err}")

        self._log_write("=" * 52)
        self._log_write(f"Results: {passed} passed, {failed} failed")
        if failed == 0:
            self.root.after(0, lambda: self._set_status(f"✓ All {passed} tests passed", c["ok"]))
        else:
            self.root.after(0, lambda: self._set_status(f"✗ {failed} failed,  {passed} passed", c["danger"]))

    def _run_build(self):
        self._log_write("\n" + "=" * 52)
        self._log_write(f"PyInstaller build  {time.strftime('%H:%M:%S')}")
        self._set_status("Building…", CLR["warn"])
        threading.Thread(target=self._exec_build, daemon=True).start()

    def _exec_build(self):
        c = CLR
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "PyInstaller", "app.spec", "--noconfirm"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=os.getcwd(),
            )
            for line in proc.stdout:
                self._log_write(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                self._log_write("✓ Build complete!  →  dist/app.exe")
                self.root.after(0, lambda: self._set_status("✓ Build successful", c["ok"]))
            else:
                self._log_write(f"✗ Build failed  (exit code {proc.returncode})")
                self.root.after(0, lambda: self._set_status("✗ Build failed", c["danger"]))
        except Exception as exc:
            self._log_write(f"✗ Error: {exc}")
            self.root.after(0, lambda: self._set_status(f"✗ {exc}", c["danger"]))

    def _launch_app(self):
        threading.Thread(
            target=lambda: subprocess.Popen([sys.executable, "app.py"]),
            daemon=True,
        ).start()
        self._set_status("App launched!", CLR["ok"])

    # ── Main ─────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TestRunnerApp().run()
