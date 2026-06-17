"""系统托盘图标模块 — 纯 Win32 API，录制时显示计时"""

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


# ---- WNDCLASS 结构 ----
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


# ---- NOTIFYICONDATA 结构 ----
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


# ---- 窗口过程 ----
_WND_PROC = None

@ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
def _window_proc(hwnd, msg, wparam, lparam):
    try:
        if msg == WM_USER_TRAY:
            pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
    except Exception:
        return 0


# ---- ICO 生成 ----
def _generate_ico(filepath, size=32):
    """生成一个录制指示图标（红点）"""
    center = size // 2
    radius = size // 2 - 2

    pixels_rgba = []
    for y in range(size):
        for x in range(size):
            dx, dy = x - center, y - center
            if dx * dx + dy * dy <= radius * radius:
                pixels_rgba.append((255, 59, 48, 255))  # 红色
            else:
                pixels_rgba.append((0, 0, 0, 0))

    # DIB header (40 bytes)
    dib = struct.pack("<IiiHHIIiiII",
        40, size, size * 2, 1, 32, 0, size * size * 4, 0, 0, 0, 0)

    # Pixel data (bottom-up, BGRA)
    pixel_data = b""
    for y in range(size - 1, -1, -1):
        for x in range(size):
            r, g, b, a = pixels_rgba[y * size + x]
            pixel_data += struct.pack("BBBB", b, g, r, a)

    and_mask = b"\x00" * (size * ((size + 7) // 8))
    bmp_data = dib + pixel_data + and_mask

    # ICO header + directory
    offset = 6 + 16
    ico = struct.pack("<HHH", 0, 1, 1)  # reserved, type=ICO, count=1
    ico += struct.pack("<BBBBHHII",
        size if size < 256 else 0, size if size < 256 else 0,
        0, 0, 1, 32, len(bmp_data), offset)
    ico += bmp_data

    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(ico)
    return filepath


# ---- 托盘类 ----
class TrayIcon:
    def __init__(self):
        self._ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        self._nid = None
        self._recording = False
        self._start_time = None
        self._timer_thread = None
        self._timer_running = False
        self._hwnd = None
        self._browser_hwnd = None

    def start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._start_time = time.time()

        _generate_ico(self._ico_path)
        hicon = user32.LoadImageW(0, self._ico_path, 1, 0, 0, 0x00000010)
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
        self._nid.szTip = "录制中... 00:00"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid))

        self._hide_browser()

        self._timer_running = True
        self._timer_thread = threading.Thread(target=self._update_timer, daemon=True)
        self._timer_thread.start()

    def stop_recording(self):
        if not self._recording:
            return
        self._recording = False
        self._timer_running = False

        if self._nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None

        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None

        self._restore_browser()

    def _create_message_window(self):
        class_name = "MouseRecorderTray"
        wc = WNDCLASSW()
        wc.lpfnWndProc = ctypes.cast(_window_proc, ctypes.c_void_p)
        wc.hInstance = kernel32.GetModuleHandleW(0)
        wc.lpszClassName = class_name

        user32.RegisterClassW(ctypes.byref(wc))
        self._hwnd = user32.CreateWindowExW(0, class_name, "", 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def _hide_browser(self):
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
        if found:
            self._browser_hwnd = found[0]
            user32.ShowWindow(self._browser_hwnd, SW_MINIMIZE)

    def _restore_browser(self):
        if self._browser_hwnd:
            user32.ShowWindow(self._browser_hwnd, SW_RESTORE)
            user32.SetForegroundWindow(self._browser_hwnd)
            self._browser_hwnd = None

    def _update_timer(self):
        while self._timer_running:
            elapsed = int(time.time() - self._start_time)
            mins, secs = divmod(elapsed, 60)
            tip = f"录制中... {mins:02d}:{secs:02d}"
            if self._nid:
                self._nid.szTip = tip
                self._nid.uFlags = NIF_TIP
                try:
                    shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))
                except Exception:
                    pass
            time.sleep(1)

    @property
    def recording(self):
        return self._recording


