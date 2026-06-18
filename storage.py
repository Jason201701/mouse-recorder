"""录制文件持久化管理模块"""

import json
import os
import time
import uuid
from utils import get_app_dir

STORAGE_DIR = os.path.join(get_app_dir(), "recordings")


def _ensure_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def list_recordings():
    _ensure_dir()
    recordings = []
    for fname in os.listdir(STORAGE_DIR):
        if fname.endswith(".json"):
            path = os.path.join(STORAGE_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                recordings.append({
                    "id": data.get("id", fname.replace(".json", "")),
                    "name": data.get("name", "未命名"),
                    "mode": data.get("mode", "absolute"),
                    "window_title": data.get("window_title", ""),
                    "event_count": len(data.get("events", [])),
                    "duration_ms": data.get("duration_ms", 0),
                    "file": fname,
                    "path": path,
                })
            except (json.JSONDecodeError, KeyError):
                continue
    recordings.sort(key=lambda r: r.get("name", ""))
    return recordings


def load_recording(recording_id):
    fname = recording_id if recording_id.endswith(".json") else f"{recording_id}.json"
    path = os.path.join(STORAGE_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_recording(data):
    _ensure_dir()
    rec_id = data.get("id") or str(uuid.uuid4())[:8]
    data["id"] = rec_id
    data.setdefault("name", "未命名")
    data.setdefault("mode", "absolute")
    data.setdefault("window_title", "")
    data.setdefault("events", [])
    path = os.path.join(STORAGE_DIR, f"{rec_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return rec_id


def delete_recording(recording_id):
    fname = recording_id if recording_id.endswith(".json") else f"{recording_id}.json"
    path = os.path.join(STORAGE_DIR, fname)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def rename_recording(recording_id, new_name):
    data = load_recording(recording_id)
    if data is None:
        return False
    data["name"] = new_name
    save_recording(data)
    return True


def trim_recording(recording_id, start_ms=None, end_ms=None):
    data = load_recording(recording_id)
    if data is None:
        return False
    events = data.get("events", [])
    if start_ms is not None:
        events = [e for e in events if e.get("ms", 0) >= start_ms]
        min_ms = start_ms
        for e in events:
            e["ms"] -= min_ms
        if events:
            data["duration_ms"] = max(e.get("ms", 0) for e in events)
    if end_ms is not None:
        events = [e for e in events if e.get("ms", 0) <= end_ms]
        if events:
            data["duration_ms"] = max(e.get("ms", 0) for e in events)
    data["events"] = events
    save_recording(data)
    return True
