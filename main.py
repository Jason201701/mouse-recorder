"""主入口 — 协调录制、回放、热键、托盘、原生窗口"""

import os
import sys
import time
import threading
import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recorder import Recorder
from player import Player
from hotkey_manager import HotkeyManager
from storage import (
    list_recordings, load_recording, save_recording,
    delete_recording, rename_recording, trim_recording,
)
from web_server import WebServer
from tray import TrayIcon
import config as cfg


class App:
    def __init__(self):
        self.config = cfg.load_config()
        self._recorder = Recorder(mode=self.config.get("record_mode", "absolute"))
        self._player = Player()
        self._hotkeys = HotkeyManager()
        self._tray = TrayIcon(get_hwnd=self._get_window_hwnd)
        self._server = WebServer(self, port=8765)
        self._last_selected_id = None
        self._window = None

    # ---- 录制 ----
    def start_recording(self, mode=None):
        if self._player and self._player.playing:
            self._player.stop()
        if mode:
            self._recorder.set_mode(mode)
        self._recorder.start()
        self._tray.start_recording()

    def stop_recording(self):
        data = self._recorder.stop()
        self._tray.stop()
        if data:
            rec_id = save_recording(data)
            return rec_id
        return None

    # ---- 回放 ----
    def play_recording(self, recording_id, speed=1.0, loop_count=1):
        if self._recorder and self._recorder.recording:
            self.stop_recording()
        data = load_recording(recording_id)
        if data is None:
            return
        self._last_selected_id = recording_id
        self._tray.start_playback()
        self._player.play(data, speed=speed, loop_count=loop_count, on_status=None)

        def _monitor():
            while self._player.playing:
                time.sleep(0.2)
            self._tray.stop()
        threading.Thread(target=_monitor, daemon=True).start()

    def stop_playback(self):
        if self._player:
            self._player.stop()
        self._tray.stop()

    # ---- 录制管理 ----
    def list_recordings(self):
        return list_recordings()

    def delete_recording(self, rec_id):
        delete_recording(rec_id)

    def rename_recording(self, rec_id, new_name):
        rename_recording(rec_id, new_name)

    def trim_recording(self, rec_id, start_ms, end_ms):
        trim_recording(rec_id, start_ms, end_ms)

    # ---- 热键 ----
    def set_hotkey(self, which, combo):
        key_list = HotkeyManager.combo_to_key_list(combo)
        key_map = {"record": "hotkey_record", "play": "hotkey_play", "stop": "hotkey_stop"}
        cfg_key = key_map.get(which, "hotkey_record")
        cfg.set_(cfg_key, key_list)
        self._update_hotkey_listeners()

    def _update_hotkey_listeners(self):
        record_combo = HotkeyManager.key_list_to_combo(
            self.config.get("hotkey_record", ["ctrl", "shift", "f9"]))
        play_combo = HotkeyManager.key_list_to_combo(
            self.config.get("hotkey_play", ["ctrl", "shift", "f10"]))
        stop_combo = HotkeyManager.key_list_to_combo(
            self.config.get("hotkey_stop", ["ctrl", "shift", "f11"]))
        self._hotkeys.update_hotkeys(record_combo, play_combo, stop_combo,
                                     self._on_hotkey_record,
                                     self._on_hotkey_play,
                                     self._on_hotkey_stop)

    def _on_hotkey_record(self):
        if self._recorder and self._recorder.recording:
            self.stop_recording()
        else:
            mode = self.config.get("record_mode", "absolute")
            self.start_recording(mode)

    def _on_hotkey_stop(self):
        if self._recorder and self._recorder.recording:
            self.stop_recording()
        if self._player and self._player.playing:
            self.stop_playback()

    def _on_hotkey_play(self):
        if self._player and self._player.playing:
            self.stop_playback()
            return
        recordings = list_recordings()
        if not recordings:
            return
        rec_id = self._last_selected_id or recordings[0]["id"]
        speed = float(self.config.get("default_speed", 1.0))
        self.play_recording(rec_id, speed=speed, loop_count=1)

    def refresh_config(self):
        self.config = cfg.load_config()

    # ---- 原生窗口 ----
    def _get_window_hwnd(self):
        """供 tray 模块获取窗口句柄"""
        try:
            if self._window:
                return int(self._window.native.handle)
        except Exception:
            pass
        return None

    # ---- 生命周期 ----
    def shutdown(self):
        if self._recorder and self._recorder.recording:
            self._recorder.stop()
        self._tray.stop()
        if self._player:
            self._player.stop()
        self._hotkeys.stop()
        self._server.stop()
        # 关闭 pywebview 窗口
        try:
            if self._window:
                self._window.destroy()
        except Exception:
            pass

    def run(self):
        self._update_hotkey_listeners()
        self._hotkeys.start()
        url = self._server.start()

        print(f"Mouse Recorder 已启动")
        print(f"录制热键: Ctrl+Shift+F9")
        print(f"回放热键: Ctrl+Shift+F10")
        print(f"停止热键: Ctrl+Shift+F11")

        # 创建原生窗口
        self._window = webview.create_window(
            title="Mouse Recorder",
            url=url,
            width=720,
            height=540,
            min_size=(600, 400),
            resizable=True,
            easy_drag=False,
        )

        # 启动窗口事件循环（阻塞）
        webview.start(gui="edgechromium", debug=False)

        # 窗口关闭后清理
        self.shutdown()


if __name__ == "__main__":
    app = App()
    app.run()

