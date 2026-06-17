"""热键管理模块 — 全局热键注册与动态切换"""

import threading
from pynput import keyboard
from pynput.keyboard import Key, KeyCode


class HotkeyManager:
    def __init__(self):
        self._listener = None
        self._thread = None
        self._callbacks = {}
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._listener:
            self._listener.stop()

    def _run(self):
        while self._running:
            try:
                # 构建当前热键映射
                hotkeys = self._build_hotkeys()
                if hotkeys:
                    self._listener = keyboard.GlobalHotKeys(hotkeys)
                    self._listener.start()
                    self._listener.join()
                else:
                    import time
                    time.sleep(0.5)
            except Exception:
                import time
                time.sleep(0.5)

    def _build_hotkeys(self):
        result = {}
        for combo, cb in self._callbacks.items():
            if combo:
                result[combo] = cb
        return result

    def register(self, combo, callback):
        """注册热键，combo 格式如 '<ctrl>+<shift>+r'"""
        self._callbacks[combo] = callback
        self._restart_listener()

    def unregister(self, combo):
        self._callbacks.pop(combo, None)
        self._restart_listener()

    def update_hotkeys(self, record_combo, play_combo, on_record, on_play):
        """批量更新录制/回放热键"""
        self._callbacks.clear()
        if record_combo:
            self._callbacks[record_combo] = on_record
        if play_combo:
            self._callbacks[play_combo] = on_play
        self._restart_listener()

    def _restart_listener(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        # 重新 join 旧的会自然结束，新的 run 循环会创建新 listener
        if self._running:
            try:
                self._listener = keyboard.GlobalHotKeys(self._build_hotkeys())
                self._listener.start()
            except Exception:
                pass

    @staticmethod
    def key_list_to_combo(keys):
        """将按键列表转为 pynput 热键字符串，如 ['ctrl', 'shift', 'r'] -> '<ctrl>+<shift>+r'"""
        parts = []
        for k in keys:
            k = k.strip().lower()
            if not k.startswith("<"):
                k = f"<{k}>"
            parts.append(k)
        return "+".join(parts)

    @staticmethod
    def combo_to_key_list(combo):
        """反向：'<ctrl>+<shift>+r' -> ['ctrl', 'shift', 'r']"""
        parts = combo.split("+")
        result = []
        for p in parts:
            p = p.strip().strip("<>")
            if p:
                result.append(p)
        return result
