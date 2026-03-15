# Usage Guide

The Z.ai Monitor widget provides a small overlay panel showing quota information.

## Controls

| Control | Description                               |
| ------- | ----------------------------------------- |
| Drag    | Move the widget by dragging the title bar |
| ▾ / ▸   | Collapse or expand the panel              |
| ⚙       | Open settings                             |
| ✕       | Exit / Minimize to tray                   |

## Keyboard Shortcuts

| Shortcut   | Action                    |
| ---------- | ------------------------- |
| `Ctrl+R`   | Refresh quota             |
| `Ctrl+,`   | Open settings             |
| `Ctrl+Q`   | Quit application          |
| `Esc`      | Minimize to system tray   |

## System Tray

When **Tray** option is enabled:

* Clicking ✕ minimizes to system tray instead of closing
* Right-click tray icon for options:
  * **Show** — Restore the window
  * **Refresh** — Update quota immediately
  * **Quit** — Close the application

## Notifications

When **Notify** option is enabled:

* Windows toast notifications appear when quota limits are reached
* **Warning** notification at configurable threshold (default: 80%)
* **Critical** notification at configurable threshold (default: 95%)

## Settings

Inside the **Settings** tab you can configure:

### Bearer Token

Enter your Z.ai API token.

The `Bearer ` prefix is automatically added if it is missing.

### Refresh Interval

Defines how often the quota information refreshes.

Minimum value: **5 seconds**

### Always on Top

Toggle whether the widget stays above other windows.

### Tray (System Tray)

When enabled, closing the window minimizes to system tray.

### Notify (Notifications)

When enabled, shows Windows notifications for quota warnings.

### Warn / Crit (Thresholds)

Set custom threshold percentages:
* **Warn** — Warning notification level (default: 80%)
* **Crit** — Critical notification level (default: 95%)

### Theme

Switch between:

* Dark mode
* Light mode
