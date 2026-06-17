"""用户配置读写模块"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "hotkey_record": ["ctrl", "shift", "f9"],
    "hotkey_play": ["ctrl", "shift", "f10"],
    "hotkey_stop": ["ctrl", "shift", "f11"],
    "default_speed": 1.0,
    "record_mode": "absolute",
}

_config = None


def load_config():
    global _config
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _config = json.load(f)
    else:
        _config = dict(DEFAULT_CONFIG)
        save_config()
    return _config


def save_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_config, f, indent=2, ensure_ascii=False)


def get(key, default=None):
    if _config is None:
        load_config()
    return _config.get(key, DEFAULT_CONFIG.get(key, default))


def set_(key, value):
    if _config is None:
        load_config()
    _config[key] = value
    save_config()
