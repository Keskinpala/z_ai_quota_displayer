# Z.ai Monitor V1.4.1
![GitHub Stars](https://img.shields.io/github/stars/Keskinpala/z_ai_quota_displayer)
[![Github Download](https://img.shields.io/github/downloads/Keskinpala/z_ai_quota_displayer/total.svg)]()

<p align="center">

Always-on-top desktop overlay that shows your **Z.ai API quota and token usage in real time**.

Lightweight • Draggable • Fast • Minimal

</p>

<p align="center">

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success)

</p>

<p align="center">

<a href="https://github.com/Keskinpala/z_ai_quota_displayer/releases/latest">
<img src="https://img.shields.io/badge/Download-Latest%20Release-blue?style=for-the-badge">
</a>

</p>

---

# Overview

**Z.ai Monitor** is a lightweight desktop widget that displays your **Z.ai API quota usage in real time**.

It runs as a small floating overlay and stays visible while you work.

Perfect for developers using Z.ai APIs who want quick visibility into their usage without opening dashboards.

---

# Features

### Core Features
* Real-time quota monitoring
* Always-on-top overlay widget
* Draggable floating window
* Dark / Light theme
* Configurable refresh interval
* Lightweight resource usage
* Simple standalone API client
* Automatic bearer token handling

### New in V1.1.0
* 🔔 **Windows Notifications** — Get alerts when quota reaches warning/critical levels
* 📥 **System Tray** — Minimize to system tray instead of closing
* ⚙️ **Customizable Thresholds** — Set your own warning (default 80%) and critical (default 95%) levels
* ⌨️ **Keyboard Shortcuts**:
  * `Ctrl+R` — Refresh quota
  * `Ctrl+,` — Open settings
  * `Ctrl+Q` — Quit application
  * `Esc` — Minimize to tray

### New in V1.2.0
* 🤖 **Zeta Mascot** — Animated robot character shows roadmap & tips (click 🤖 in title bar)
* 🏗️ **Test Runner** — `python test_runner.py` to verify build health before shipping
* 🔧 **Refresh Timer fix** — Manual refresh now correctly resets the 30s countdown

### New in V1.4.1
* 🐛 **Bildirim düzeltmesi** — `notify_interval_min` ile periyodik bildirimler artık `remaining` değeri `None` olduğunda da düzgün çalışıyor (hata sessizce yutuluyordu)

### New in V1.4.0
* 🌐 **16-Language UI** — TR, EN, DE, FR, ES, PT, RU, ZH, JA, KO, AR, IT, NL, PL, UK, ID
* 💬 **Chat Launcher** — 💬 button opens `chat.z.ai` in your browser or built-in view (no auto-login)
* 🔄 **Restart** from Settings panel and tray right-click (`Ctrl+Shift+R`)
* Ⓜ️ **Author / About** section in Settings — Inokosha Yazılım • Atakan ÇELİKELLİ
* Scrollable Settings panel, clean quit/restart logic, no mascot
* 🔔 **Custom Toast Notifications** — Rebuilt from scratch (win10toast dropped — broken on Win11); zero external deps
* ⏰ **Interval Reminders** — Optional periodic quota reminder every N minutes while app runs
* 🔊 **Sound Toggle** — Enable/disable system beep with each notification
* 🚀 **Windows Auto-start** — Start with Windows via a single checkbox (registry-based)
* 🎚️ **Opacity Control** — Adjust window transparency (0.10 – 1.00)
* 📋 **Copy to Clipboard** — One-click quota snapshot with timestamp
* 📡 **Live Tray Tooltip** — Shows current quota % when you hover the tray icon
* 🍽️ **Kota Durumu tray menu** — Instant status notification from tray right-click

---

# Screenshot

<p align="center">
<img src="assets/image.png" width="420">
</p>

<p align="center">
<img src="assets/image-1.png" width="420">
</p>

---

# Installation

## Requirements

* Python **3.8+**
* pip

Install dependencies:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install requests pystray Pillow
```

> **Note:** `pystray` and `Pillow` are optional. The app works without them but the system tray minimize feature will be disabled. Notifications use the built-in `notifier.py` and require no extra packages.

---

# Run the Application

### Normal run

```bash
python app.py
```

### Windows background mode (no terminal)

```
launch.bat
```

---

# Usage

| Control | Description                       |
| ------- | --------------------------------- |
| Drag    | Move widget by dragging title bar |
| ▾ / ▸   | Expand or collapse panel          |
| ⚙       | Open settings                     |
| ✕       | Exit application                  |

---

# Settings

Inside the **Settings** tab you can configure:

### Bearer Token

Enter your Z.ai API token.

The prefix **Bearer** is automatically added if missing.

---

### Refresh Interval

Controls how often the quota updates.

Minimum value:

```
5 seconds
```

---

### Always On Top

Keeps the widget above all windows.

---

### System Tray (New)

When enabled, clicking ✕ minimizes to system tray instead of closing.

Right-click tray icon for options:
* Show — Restore window
* Refresh — Update quota
* Quit — Close application

---

### Notifications

Enable custom toast notifications for quota warnings.

**Threshold Levels:**
* **Warning** — Default 80%, shows yellow alert
* **Critical** — Default 95%, shows red alert

**Interval Reminder** — Set `Aralık [dk]` to a positive number to receive a periodic quota
snapshot notification every N minutes (0 = disabled).

**Sound** — Toggle the system beep that plays with each notification.

---

### Auto-start

Tick **Başlangıç** in Settings to launch Z.ai Monitor automatically when Windows starts.
Uses `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (current user only, no admin needed).

---

### Opacity

Adjust window transparency in Settings (`Opaklık`). Range 0.10 – 1.00.

---

### Copy to Clipboard

Click the **📋** button next to the refresh icon to copy a timestamped plain-text
quota snapshot to the clipboard, ready to paste into tickets or chat.

---

### Theme

Choose between:

* Dark Mode
* Light Mode

---

# Configuration Location

Settings are stored in:

```
%APPDATA%/ZaiMonitor/config.json
```

---

# Using the API Client

The project includes a lightweight standalone client:

```
zai_client.py
```

Example:

```python
from zai_client import ZaiClient

client = ZaiClient("your_api_token")

quota = client.get_quota()

print(quota.level)
print(quota.time_limit.remaining)
print(quota.time_limit.percentage)
print(quota.time_limit.next_reset_datetime)

for d in quota.time_limit.usage_details:
    print(d.model_code, d.usage)

if quota.error:
    print("Error:", quota.error)
```

Dependencies:

```
requests
```

---

# Project Structure

```
ZaiMonitor
│
├ app.py
├ launch.bat
├ zai_client.py
├ requirements.txt
│
├ assets
│   ├ image.png
│   └ image-1.png
│
├ README.md
├ INSTALL.md
├ USAGE.md
├ API.md
│
└ .github
   └ workflows
       build.yml
```

---

# Roadmap

### Completed ✅
* ✅ System tray integration
* ✅ Notification alerts for quota limits
* ✅ Customizable warning thresholds
* ✅ Keyboard shortcuts
* ✅ Animated mascot (Zeta) — roadmap guide built into the app
* ✅ Local build/test runner UI

### Planned 🚧
* MacOS support
* Linux support
* Auto update system
* Native installer
* Usage history/statistics
* Multi-account support

---

# Contributing

Contributions are welcome.

Steps:

```
1. Fork repository
2. Create feature branch
3. Commit changes
4. Submit pull request
```

---

# License

This project is released under the **MIT License**.

---

# Author

Created by **Inokosha Software**

If you find this project useful, consider giving it a ⭐ on GitHub.
