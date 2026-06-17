"""Web 界面服务器 — 内置 HTTP 服务 + REST API"""

import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class APIHandler(BaseHTTPRequestHandler):
    """处理 API 请求 + 静态文件"""
    app_ref = None  # 由外部注入

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self._json_response(self._get_status())
        elif path == "/api/recordings":
            self._json_response(self.app_ref.list_recordings())
        elif path == "/api/config":
            self._json_response({
                "hotkey_record": self.app_ref.config.get("hotkey_record", []),
                "hotkey_play": self.app_ref.config.get("hotkey_play", []),
                "default_speed": self.app_ref.config.get("default_speed", 1.0),
                "record_mode": self.app_ref.config.get("record_mode", "absolute"),
            })
        elif path == "/api/recording":
            q = parse_qs(parsed.query)
            rec_id = q.get("id", [None])[0]
            if rec_id:
                from storage import load_recording
                data = load_recording(rec_id)
                self._json_response(data)
            else:
                self._json_response({"error": "missing id"}, 400)
        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        if path == "/api/record/start":
            mode = body.get("mode") or "absolute"
            self.app_ref.start_recording(mode)
            self._json_response({"status": "recording"})
        elif path == "/api/record/stop":
            rec_id = self.app_ref.stop_recording()
            self._json_response({"status": "stopped", "id": rec_id})
        elif path == "/api/play":
            rec_id = body.get("id")
            speed = float(body.get("speed") or 1.0)
            loops = int(body.get("loops") or 1)
            if loops <= 0:
                loops = 999999  # 近似无限
            if rec_id:
                self.app_ref.play_recording(rec_id, speed, loops)
                self._json_response({"status": "playing"})
            else:
                self._json_response({"error": "missing id"}, 400)
        elif path == "/api/play/stop":
            self.app_ref.stop_playback()
            self._json_response({"status": "stopped"})
        elif path == "/api/recording/delete":
            rec_id = body.get("id")
            if rec_id:
                self.app_ref.delete_recording(rec_id)
                self._json_response({"status": "deleted"})
            else:
                self._json_response({"error": "missing id"}, 400)
        elif path == "/api/recording/rename":
            rec_id = body.get("id")
            name = body.get("name")
            if rec_id and name:
                self.app_ref.rename_recording(rec_id, name)
                self._json_response({"status": "renamed"})
            else:
                self._json_response({"error": "missing params"}, 400)
        elif path == "/api/recording/trim":
            rec_id = body.get("id")
            start_ms = body.get("start_ms")
            end_ms = body.get("end_ms")
            if rec_id:
                self.app_ref.trim_recording(rec_id, start_ms, end_ms)
                self._json_response({"status": "trimmed"})
            else:
                self._json_response({"error": "missing id"}, 400)
        elif path == "/api/config":
            for key in ("hotkey_record", "hotkey_play", "default_speed", "record_mode"):
                if key in body:
                    from config import set_
                    set_(key, body[key])
            self.app_ref.refresh_config()
            self.app_ref._update_hotkey_listeners()
            self._json_response({"status": "saved"})
        else:
            self._serve_static(path)

    def _get_status(self):
        app = self.app_ref
        return {
            "recording": app._recorder.recording if app._recorder else False,
            "playing": app._player.playing if app._player else False,
        }

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        filepath = os.path.join(STATIC_DIR, path.lstrip("/"))
        if not os.path.abspath(filepath).startswith(os.path.abspath(STATIC_DIR)):
            self.send_error(403)
            return
        if os.path.isfile(filepath):
            content_type = "text/html"
            if filepath.endswith(".css"):
                content_type = "text/css"
            elif filepath.endswith(".js"):
                content_type = "application/javascript"
            elif filepath.endswith(".json"):
                content_type = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.end_headers()
            with open(filepath, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # 静默日志


class WebServer:
    def __init__(self, app, port=8765):
        self._app = app
        self._port = port
        self._server = None
        self._thread = None
        APIHandler.app_ref = app

    def start(self):
        self._server = HTTPServer(("127.0.0.1", self._port), APIHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://127.0.0.1:{self._port}"

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None




