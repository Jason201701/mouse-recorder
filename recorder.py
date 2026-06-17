"""录制模块 — 通过 pynput 捕获鼠标和键盘事件"""

import time
import threading
from pynput import mouse, keyboard


class Recorder:
    def __init__(self, mode="absolute"):
        self.mode = mode
        self._events = []
        self._lock = threading.Lock()
        self._recording = False
        self._start_time = None
        self._mouse_listener = None
        self._keyboard_listener = None
        self._paused = False
        self._window_title = ""

    # ---- 状态 ----
    @property
    def recording(self):
        return self._recording

    @property
    def paused(self):
        return self._paused

    # ---- 鼠标回调 ----
    def _on_move(self, x, y):
        if not self._recording or self._paused:
            return
        ms = int((time.time() - self._start_time) * 1000)
        with self._lock:
            self._events.append({
                "type": "mouse_move",
                "ms": ms,
                "x": int(x),
                "y": int(y),
            })

    def _on_click(self, x, y, button, pressed):
        if not self._recording or self._paused:
            return
        ms = int((time.time() - self._start_time) * 1000)
        btn_name = "left"
        if button == mouse.Button.right:
            btn_name = "right"
        elif button == mouse.Button.middle:
            btn_name = "middle"
        try:
            from pynput.mouse import Button
            if button == Button.x1:
                btn_name = "x1"
            elif button == Button.x2:
                btn_name = "x2"
        except Exception:
            pass
        with self._lock:
            self._events.append({
                "type": "mouse_click",
                "ms": ms,
                "x": int(x),
                "y": int(y),
                "btn": btn_name,
                "down": pressed,
            })

    def _on_scroll(self, x, y, dx, dy):
        if not self._recording or self._paused:
            return
        ms = int((time.time() - self._start_time) * 1000)
        with self._lock:
            self._events.append({
                "type": "mouse_scroll",
                "ms": ms,
                "x": int(x),
                "y": int(y),
                "dx": dx,
                "dy": dy,
            })

    # ---- 键盘回调 ----
    def _on_press(self, key):
        if not self._recording or self._paused:
            return
        ms = int((time.time() - self._start_time) * 1000)
        key_str = self._key_to_str(key)
        with self._lock:
            self._events.append({
                "type": "key_press",
                "ms": ms,
                "key": key_str,
                "down": True,
            })

    def _on_release(self, key):
        if not self._recording or self._paused:
            return
        ms = int((time.time() - self._start_time) * 1000)
        key_str = self._key_to_str(key)
        with self._lock:
            self._events.append({
                "type": "key_press",
                "ms": ms,
                "key": key_str,
                "down": False,
            })

    @staticmethod
    def _key_to_str(key):
        try:
            return key.char
        except AttributeError:
            return str(key)

    # ---- 控制 ----
    def start(self):
        if self._recording:
            return
        self._events = []
        self._recording = True
        self._start_time = time.time()

        # 尝试获取当前活动窗口标题
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            self._window_title = buf.value
        except Exception:
            self._window_title = ""

        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self):
        if not self._recording:
            return None
        self._recording = False
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

        with self._lock:
            events = list(self._events)
            self._events = []
        duration_ms = max((e.get("ms", 0) for e in events), default=0)

        return {
            "mode": self.mode,
            "window_title": self._window_title,
            "events": events,
            "duration_ms": duration_ms,
        }

    def set_mode(self, mode):
        self.mode = mode

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
