"""回放模块 — 按时间线重放录制事件"""

import time
import threading
import ctypes
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController, KeyCode


class Player:
    def __init__(self):
        self._controller_mouse = MouseController()
        self._controller_keyboard = KeyboardController()
        self._playing = False
        self._paused = False
        self._stop_flag = threading.Event()
        self._thread = None
        self._loop_count = 1
        self._current_loop = 0
        self._speed = 1.0
        self._on_status = None

    @property
    def playing(self):
        return self._playing

    @property
    def paused(self):
        return self._paused

    # ---- 回放核心 ----
    def play(self, recording_data, speed=1.0, loop_count=1, on_status=None):
        if self._playing:
            return False
        self._speed = speed
        self._loop_count = loop_count
        self._current_loop = 0
        self._on_status = on_status
        self._stop_flag.clear()
        self._thread = threading.Thread(
            target=self._play_thread, args=(recording_data,), daemon=False
        )
        self._thread.start()
        return True

    def stop(self):
        self._playing = False
        self._stop_flag.set()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def _play_thread(self, recording_data):
        self._playing = True
        events = recording_data.get("events", [])
        mode = recording_data.get("mode", "absolute")

        loop = 0
        while self._loop_count <= 0 or loop < self._loop_count:
            if self._stop_flag.is_set():
                break
            loop += 1
            self._current_loop = loop
            if self._on_status:
                total = "∞" if self._loop_count <= 0 else self._loop_count
                self._on_status(f"回放中 ({self._current_loop}/{total})...")

            if not self._play_events(events, mode):
                break

        self._playing = False
        self._current_loop = 0
        if self._on_status:
            self._on_status("回放完成")

    def _play_events(self, events, mode):
        if not events:
            return True
        prev_ms = 0
        for event in events:
            if self._stop_flag.is_set():
                return False
            # pause 等待
            while self._paused and not self._stop_flag.is_set():
                time.sleep(0.05)
            if self._stop_flag.is_set():
                return False

            event_ms = event.get("ms", 0)
            delay = (event_ms - prev_ms) / 1000.0 / self._speed
            if delay > 0:
                # 分段 sleep 便于快速响应 stop
                slept = 0.0
                while slept < delay:
                    if self._stop_flag.is_set():
                        return False
                    chunk = min(0.02, delay - slept)
                    time.sleep(chunk)
                    slept += chunk
            prev_ms = event_ms

            try:
                self._execute_event(event)
            except Exception:
                pass
        return True

    def _execute_event(self, event):
        etype = event.get("type")
        if etype == "mouse_move":
            x, y = event.get("x", 0), event.get("y", 0)
            self._controller_mouse.position = (x, y)
        elif etype == "mouse_click":
            x, y = event.get("x", 0), event.get("y", 0)
            self._controller_mouse.position = (x, y)
            btn = self._parse_button(event.get("btn", "left"))
            if event.get("down", True):
                self._controller_mouse.press(btn)
            else:
                self._controller_mouse.release(btn)
        elif etype == "mouse_scroll":
            dx, dy = event.get("dx", 0), event.get("dy", 0)
            self._controller_mouse.scroll(dx, dy)
        elif etype == "key_press":
            key = self._parse_key(event.get("key", ""))
            if key is None:
                return
            if event.get("down", True):
                self._controller_keyboard.press(key)
            else:
                self._controller_keyboard.release(key)

    @staticmethod
    def _parse_button(name):
        mapping = {
            "left": Button.left,
            "right": Button.right,
            "middle": Button.middle,
        }
        btn = mapping.get(name, Button.left)
        try:
            if name == "x1":
                btn = Button.x1
            elif name == "x2":
                btn = Button.x2
        except Exception:
            pass
        return btn

    @staticmethod
    def _parse_key(key_str):
        """将录制时的 key 字符串还原为 pynput Key 或 KeyCode"""
        try:
            import pynput.keyboard
        except ImportError:
            pass

        # 特殊键映射
        special = {
            "Key.alt_l": Key.alt_l, "Key.alt_r": Key.alt_r,
            "Key.alt_gr": Key.alt_gr,
            "Key.backspace": Key.backspace,
            "Key.caps_lock": Key.caps_lock,
            "Key.cmd": Key.cmd, "Key.cmd_l": Key.cmd, "Key.cmd_r": Key.cmd_r,
            "Key.ctrl_l": Key.ctrl_l, "Key.ctrl_r": Key.ctrl_r,
            "Key.delete": Key.delete,
            "Key.down": Key.down, "Key.up": Key.up,
            "Key.left": Key.left, "Key.right": Key.right,
            "Key.end": Key.end, "Key.home": Key.home,
            "Key.enter": Key.enter,
            "Key.esc": Key.esc,
            "Key.f1": Key.f1, "Key.f2": Key.f2, "Key.f3": Key.f3,
            "Key.f4": Key.f4, "Key.f5": Key.f5, "Key.f6": Key.f6,
            "Key.f7": Key.f7, "Key.f8": Key.f8, "Key.f9": Key.f9,
            "Key.f10": Key.f10, "Key.f11": Key.f11, "Key.f12": Key.f12,
            "Key.insert": Key.insert,
            "Key.media_next": Key.media_next,
            "Key.media_play_pause": Key.media_play_pause,
            "Key.media_previous": Key.media_previous,
            "Key.media_volume_down": Key.media_volume_down,
            "Key.media_volume_mute": Key.media_volume_mute,
            "Key.media_volume_up": Key.media_volume_up,
            "Key.num_lock": Key.num_lock,
            "Key.page_down": Key.page_down, "Key.page_up": Key.page_up,
            "Key.pause": Key.pause,
            "Key.print_screen": Key.print_screen,
            "Key.scroll_lock": Key.scroll_lock,
            "Key.shift_l": Key.shift_l, "Key.shift_r": Key.shift_r,
            "Key.space": Key.space,
            "Key.tab": Key.tab,
        }
        if key_str in special:
            return special[key_str]

        # 普通字符
        if len(key_str) == 1:
            return KeyCode.from_char(key_str)

        return None
