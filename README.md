# Mouse Recorder

A lightweight Windows tool for recording and replaying mouse movements, clicks, and keyboard input via global hotkeys.

## Features

- **Record** mouse moves, clicks, scrolls, and all keyboard input
- **Replay** recordings with adjustable speed (0.5x ~ 5x) and loop count
- **Global hotkeys** — works in any window, not just the app
- **System tray icon** shows recording/playback status with timer
- **Auto-hide browser** when recording starts, restore when done
- **Web UI** for managing recordings, editing hotkeys, and configuring settings
- Two coordinate modes: absolute screen coordinates or window-relative

## Hotkeys (Default)

| Action | Hotkey |
|--------|--------|
| Start / Stop recording | `Ctrl + Shift + F9` |
| Play selected recording | `Ctrl + Shift + F10` |
| Stop everything | `Ctrl + Shift + F11` |

> All hotkeys can be changed in the web UI.

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Install & Run

```bash
pip install pynput
python main.py`n`nThe app opens in its own native window (no browser needed).
```

The app opens in its own native window.

## Project Structure

```
MouseRecorder/
├── main.py              # Entry point
├── recorder.py          # Mouse/keyboard capture engine
├── player.py            # Playback engine
├── hotkey_manager.py    # Global hotkey registration
├── tray.py              # System tray icon (pure Win32)
├── storage.py           # Recording file persistence
├── web_server.py          # Built-in HTTP API server
├── config.py            # User configuration
├── static/index.html    # Web management UI
├── recordings/          # Saved recordings (gitignored)
└── requirements.txt     # pynput
```

## Recording File Format

```json
{
  "id": "a1b2c3d4",
  "name": "demo",
  "mode": "absolute",
  "window_title": "Notepad",
  "duration_ms": 5200,
  "events": [
    {"type": "mouse_move",  "ms": 0,    "x": 500, "y": 300},
    {"type": "mouse_click", "ms": 234,  "x": 500, "y": 300, "btn": "left", "down": true},
    {"type": "mouse_click", "ms": 310,  "x": 500, "y": 300, "btn": "left", "down": false},
    {"type": "key_press",   "ms": 520,  "key": "a", "down": true},
    {"type": "key_press",   "ms": 620,  "key": "a", "down": false}
  ]
}
```

## License

MIT

## Build EXE

```bash
pip install pyinstaller
python -m PyInstaller MouseRecorder.spec --clean --noconfirm
```

Or simply run `build.bat`.

The output is at `dist/MouseRecorder.exe` (~7.5 MB, no Python required).


