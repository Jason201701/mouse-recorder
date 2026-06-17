"""系统托盘图标模块 — 录制/回放状态显示，支持原生窗口"""

import ctypes
import os
import struct
import threading
import time
from ctypes import wintypes

# ---- Windows API 常量 ----
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 0x01
NIF_ICON = 0x02
NIF_TIP = 0x04
WM_USER_TRAY = 0x0401 + 100
SW_MINIMIZE = 6
SW_RESTORE = 9

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wintypes.DWORD),
    ]


@ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
def _window_proc(hwnd, msg, wparam, lparam):
    try:
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
    except Exception:
        return 0


def _generate_ico(filepath, size=32, color=(255, 59, 48)):
    center = size // 2
    radius = size // 2 - 2
    r, g, b = color

    pixels_rgba = []
    for y in range(size):
        for x in range(size):
            dx, dy = x - center, y - center
            if dx * dx + dy * dy <= radius * radius:
                pixels_rgba.append((r, g, b, 255))
            else:
                pixels_rgba.append((0, 0, 0, 0))

    dib = struct.pack("<IiiHHIIiiII",
        40, size, size * 2, 1, 32, 0, size * size * 4, 0, 0, 0, 0)
    pixel_data = b""
    for y in range(size - 1, -1, -1):
        for x in range(size):
            pr, pg, pb, pa = pixels_rgba[y * size + x]
            pixel_data += struct.pack("BBBB", pb, pg, pr, pa)
    and_mask = b"\x00" * (size * ((size + 7) // 8))
    bmp_data = dib + pixel_data + and_mask

    offset = 6 + 16
    ico = struct.pack("<HHH", 0, 1, 1)
    ico += struct.pack("<BBBBHHII",
        size if size < 256 else 0, size if size < 256 else 0,
        0, 0, 1, 32, len(bmp_data), offset)
    ico += bmp_data

    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(ico)
    return filepath


class TrayIcon:
    def __init__(self, get_hwnd=None):
        base = os.path.dirname(os.path.abspath(__file__))
        self._ico_red = os.path.join(base, "icon_rec.ico")
        self._ico_green = os.path.join(base, "icon_play.ico")
        self._get_hwnd = get_hwnd  # callback: () -> int | None
        self._nid = None
        self._active = False
        self._mode = None
        self._start_time = None
        self._timer_thread = None
        self._timer_running = False
        self._hwnd = None
        self._app_hwnd = None  # cached app window handle

    # ---- 录制 ----
    def start_recording(self):
        if self._active:
            return
        self._mode = "record"
        self._active = True
        self._start_time = time.time()

        _generate_ico(self._ico_red, color=(255, 59, 48))
        self._show_tray("录制中... 00:00")
        self._hide_window()
        self._start_timer()

    # ---- 回放 ----
    def start_playback(self):
        if self._active:
            return
        self._mode = "play"
        self._active = True
        self._start_time = time.time()

        _generate_ico(self._ico_green, color=(80, 200, 120))
        self._show_tray("回放中... Ctrl+Shift+F11 停止")
        self._start_timer()

    # ---- 停止 ----
    def stop(self):
        if not self._active:
            return
        was_record = self._mode == "record"
        self._active = False
        self._mode = None
        self._timer_running = False

        self._remove_tray()

        if was_record:
            self._restore_window()

    stop_recording = stop
    stop_playback = stop

    # ---- 内部 ----
    def _show_tray(self, tip):
        ico_path = self._ico_red if self._mode == "record" else self._ico_green
        hicon = user32.LoadImageW(0, ico_path, 1, 0, 0, 0x00000010)
        if not hicon:
            return

        self._create_message_window()

        self._nid = NOTIFYICONDATA()
        self._nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        self._nid.hWnd = self._hwnd
        self._nid.uID = 1
        self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self._nid.uCallbackMessage = WM_USER_TRAY
        self._nid.hIcon = hicon
        self._nid.szTip = tip
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid))

    def _remove_tray(self):
        if self._nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None

    def _create_message_window(self):
        if self._hwnd:
            return
        class_name = "MouseRecorderTray"
        wc = WNDCLASSW()
        wc.lpfnWndProc = ctypes.cast(_window_proc, ctypes.c_void_p)
        wc.hInstance = kernel32.GetModuleHandleW(0)
        wc.lpszClassName = class_name
        user32.RegisterClassW(ctypes.byref(wc))
        self._hwnd = user32.CreateWindowExW(0, class_name, "", 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def _start_timer(self):
        self._timer_running = True
        self._timer_thread = threading.Thread(target=self._update_timer, daemon=True)
        self._timer_thread.start()

    def _update_timer(self):
        while self._timer_running:
            elapsed = int(time.time() - self._start_time)
            mins, secs = divmod(elapsed, 60)
            if self._mode == "record":
                tip = f"录制中... {mins:02d}:{secs:02d}"
            else:
                tip = f"回放中... {mins:02d}:{secs:02d}  (Ctrl+Shift+F11 停止)"
            if self._nid:
                self._nid.szTip = tip
                self._nid.uFlags = NIF_TIP
                try:
                    shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))
                except Exception:
                    pass
            time.sleep(1)

    def _get_app_window(self):
        """获取原生窗口句柄"""
        if self._get_hwnd:
            try:
                hwnd = self._get_hwnd()
                if hwnd:
                    self._app_hwnd = hwnd
                    return hwnd
            except Exception:
                pass
        # 回退：搜索窗口标题
        if self._app_hwnd and user32.IsWindow(self._app_hwnd):
            return self._app_hwnd
        return self._find_window_by_title()

    def _find_window_by_title(self):
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if "Mouse Recorder" in buf.value:
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(enum_callback, 0)
        return found[0] if found else None

    def _hide_window(self):
        hwnd = self._get_app_window()
        if hwnd:
            user32.ShowWindow(hwnd, SW_MINIMIZE)

    def _restore_window(self):
        hwnd = self._get_app_window()
        if hwnd:
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)

    @property
    def recording(self):
        return self._active and self._mode == "record"

    @property
    def active(self):
        return self._active
