# Changelog

All notable changes to this project will be documented in this file.

---

## v1.4.1 — 2026-03-16

### Fixed
* **Periyodik bildirim çöküyordu** — `notifier.py` → `_maybe_interval_notify()` içinde
  `tl.remaining` veya `tok.remaining` `None` geldiğinde `{:,}` format hatası
  (`TypeError: NoneType.__format__`) oluşuyor, `_tick()` tarafından sessizce yutularak
  bildirim hiç gönderilmiyordu. `None` kontrolü eklenerek düzeltildi.

---

## v1.4.0 — 2026-03-16

### Added
* **16-language UI** (`i18n.py`) — TR, EN, DE, FR, ES, PT, RU, ZH, JA, KO, AR, IT, NL, PL, UK, ID;
  selectable from Settings → Language dropdown; applied instantly on save
* **Chat launcher** — 💬 button in title bar + tray menu item; opens `chat.z.ai` in
  the system browser or a built-in Tkinter WebView (falls back to browser if
  `tkinterweb` not installed); user logs in manually — no token is injected
  (keeps the app lightweight and the choice belongs to the user)
* **Restart** from Settings panel and tray right-click menu (`Ctrl+Shift+R`)
* **Author / About section** in Settings — Inokosha Yazılım • Atakan ÇELİKELLİ
* `APP_VERSION`, `APP_AUTHOR`, `APP_COMPANY`, `CHAT_URL` constants in `app.py`

### Changed
* Settings panel is now **scrollable** (Canvas + Scrollbar) — all sections visible
  regardless of screen size or font scaling
* Mascot (🤖) removed from title bar; replaced with Chat (💬) button
* `_on_close` always routes through `_force_close` (no tray) or `_minimize_to_tray`;
  no silent destroy
* `_drag_end` and close/restart share `_save_position()` helper — position
  is saved reliably in all exit paths
* `Ctrl+Q` → `_force_close` (was `_on_close`); added `Ctrl+W` for chat,
  `Ctrl+Shift+R` for restart
* Tray menu translated via i18n; added Restart and Open Chat items
* Config gains `language: str = "tr"` and `chat_mode: str = "browser"` fields

### Fixed
* `SETTINGS_H` increased to 480 to accommodate new scrollable content

---

## v1.3.0 — 2026-03-16

### Fixed
* **win10toast replaced** with custom Tkinter toast (`notifier.py`) — `win10toast`
  is fatally broken on Windows 11 (`WNDPROC return value cannot be converted to
  LRESULT`). The new engine has **zero extra dependencies** (stdlib only).

### Added
* **Custom toast engine** (`notifier.py`)
  * `ToastWindow` — bottom-right animated popup; fade in/out, drain-bar timer,
    hover to pause, stack-safe (multiple toasts don't overlap)
  * `NotificationEngine` — threshold checks with hysteresis, periodic interval mode
  * Severity colours: info `#4f8ef7`, warn `#f59e0b`, critical `#f4566a`, ok `#22d3a0`
* **Periodic interval notifications** — configurable in Settings (`Aralık [dk]`);
  fires every N minutes while the app is running or minimised to tray
* **System sound toggle** (`notify_sound` setting) — uses `winsound.MessageBeep` (stdlib)
* **Windows auto-start** (`Başlangıç` checkbox) — adds/removes app from
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` via `winreg` (stdlib)
* **Opacity control** in Settings (0.10 – 1.00)
* **Copy to clipboard** (📋 button in monitor view) — pastes timestamped
  quota snapshot as plain text
* **Tray tooltip** updated live with current quota percentages
* **"Kota Durumu" tray menu item** — fires an instant status notification from
  the system-tray right-click menu
* `SETTINGS_H = 430` — settings panel auto-resizes the window so nothing is clipped

### Changed
* Settings panel fully redesigned — compact two-column layout, all options visible
  without scrolling (Bearer Token → Refresh+UTC → checkboxes → thresholds → theme)
* `app.spec` — `notifier.py` added to bundle; `win10toast` removed from hiddenimports
* `requirements.txt` — `win10toast` dependency removed
* `test_runner.py` — win10toast test replaced with `notifier.py` import test

---

## v1.2.0 — 2026-03-16

### Added
* **Zeta Mascot** (`mascot.py`) — animated robot character on floating window
  * Talks through roadmap items, tips, and features
  * 30 FPS canvas animation (blink, bob, talking mouth)
  * Accessible via 🤖 button in title bar
  * Messages cycle with typewriter effect + progress dots
* **Test Runner** (`test_runner.py`) — local build verification UI
  * Run with `python test_runner.py`
  * Checks all imports, config round-trip, API client, syntax, PyInstaller
  * One-click **Build EXE** with live log output
  * One-click **Launch App** for quick smoke test

### Fixed
* **Auto-refresh timer reset bug** — manual refresh (`⟳`) was cancelling the
  30-second countdown without rescheduling it, causing auto-update to stop.
  Now `_manual_refresh()` always restarts the timer.

### Changed
* `app.spec` — output renamed `ZaiMonitor.exe`, `console=False` (no cmd window),
  `mascot.py` and `assets/` bundled, optional hidden imports added.

---

## v1.1.0 — 2026-03-16

### Added
* **System Tray Integration** — Minimize to tray instead of closing, with right-click menu
* **Windows Notifications** — Toast notifications when quota reaches warning/critical levels
* **Customizable Thresholds** — Set warning (default 80%) and critical (default 95%) levels
* **Keyboard Shortcuts**:
  * `Ctrl+R` — Refresh quota
  * `Ctrl+,` — Open settings
  * `Ctrl+Q` — Quit application
  * `Esc` — Minimize to tray

### Changed
* Settings panel reorganized to fit new options
* Added optional dependencies: `pystray`, `Pillow`, `win10toast`

---

## v1.0.0

Initial release

Features:

* Always-on-top quota widget
* Dark / Light theme
* Configurable refresh interval
* API client (`zai_client.py`)


### Added
* **System Tray Integration** — Minimize to tray instead of closing, with right-click menu
* **Windows Notifications** — Toast notifications when quota reaches warning/critical levels
* **Customizable Thresholds** — Set warning (default 80%) and critical (default 95%) levels
* **Keyboard Shortcuts**:
  * `Ctrl+R` — Refresh quota
  * `Ctrl+,` — Open settings
  * `Ctrl+Q` — Quit application
  * `Esc` — Minimize to tray

### Changed
* Settings panel reorganized to fit new options
* Added optional dependencies: `pystray`, `Pillow`, `win10toast`

### Technical
* Graceful fallback when optional dependencies are not installed
* Added `.claude.md` agent instructions file for AI assistance

---

## v1.0.0

Initial release

Features:

* Always-on-top quota widget
* Dark / Light theme
* Configurable refresh interval
* API client (`zai_client.py`)
