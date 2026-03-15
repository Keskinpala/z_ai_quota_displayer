"""
config.py — Persistent settings for Z.ai Monitor
Saves to %APPDATA%/ZaiMonitor/config.json on Windows,
~/.config/zai_monitor/config.json on Linux/Mac.
"""

import json
import os
import sys
from dataclasses import dataclass, asdict


def _config_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    folder = os.path.join(base, "ZaiMonitor")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "config.json")


@dataclass
class AppConfig:
    bearer_token: str = ""
    refresh_interval: int = 30       # seconds
    always_on_top: bool = True
    window_x: int = 100
    window_y: int = 100
    collapsed: bool = False
    opacity: float = 0.95
    theme: str = "dark"              # "dark" | "light"
    utc_offset: int = 3              # UTC+X, e.g. 3 for Turkey
    
    # New features v1.1.0
    minimize_to_tray: bool = True    # Minimize to system tray instead of closing
    notifications_enabled: bool = True   # Enable quota warning notifications
    warning_threshold: int = 80      # Show warning notification at X% usage
    critical_threshold: int = 95     # Show critical notification at X% usage
    auto_start: bool = False         # Auto-start with Windows

    # New features v1.3.0
    notify_interval_min: int = 0     # 0 = off; periodic reminder every N minutes while in tray
    notify_sound: bool = True        # Play system sound with notifications (Windows only)

    # New features v1.4.0
    language: str = "tr"             # UI language code (see i18n.LANGUAGES)
    chat_mode: str = "browser"       # "browser" | "builtin" — how to open chat.z.ai

    def save(self):
        try:
            with open(_config_path(), "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception:
            pass

    @classmethod
    def load(cls) -> "AppConfig":
        try:
            with open(_config_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = cls()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            return cfg
        except Exception:
            return cls()