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