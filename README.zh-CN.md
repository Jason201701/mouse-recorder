# Mouse Recorder（鼠标录制器）

一款轻量级 Windows 工具，通过全局热键录制鼠标移动、点击及键盘输入，并支持倍速回放。

## 功能

- **录制** 鼠标移动、点击、滚轮及所有键盘输入
- **回放** 支持 0.5x ~ 5x 倍速和循环次数调节
- **全局热键** — 在任何窗口下都能触发，无需切换到应用
- **系统托盘图标** — 录制时红色、回放时绿色，悬停显示计时
- **自动隐藏浏览器** — 录制时界面自动最小化，结束后恢复
- **Web 管理界面** — 录制列表管理、热键修改、参数配置
- **两种坐标模式** — 绝对屏幕坐标 / 窗口相对坐标

## 默认热键

| 操作 | 热键 |
|------|------|
| 开始 / 停止录制 | `Ctrl + Shift + F9` |
| 回放选中录制 | `Ctrl + Shift + F10` |
| 停止一切操作 | `Ctrl + Shift + F11` |

> 所有热键均可在 Web 界面中自定义修改。

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装运行

```bash
pip install pynput
python main.py
```

浏览器会自动打开管理界面 `http://127.0.0.1:8765`。

## 项目结构

```
MouseRecorder/
├── main.py              # 程序入口
├── recorder.py          # 鼠标/键盘录制引擎
├── player.py            # 回放引擎
├── hotkey_manager.py    # 全局热键管理
├── tray.py              # 系统托盘图标（纯 Win32 API）
├── storage.py           # 录制文件持久化
├── web_server.py        # 内置 HTTP API 服务
├── config.py            # 用户配置
├── static/index.html    # Web 管理界面
├── recordings/          # 录制文件存放（已 gitignore）
└── requirements.txt     # pynput
```

## 录制文件格式

```json
{
  "id": "a1b2c3d4",
  "name": "演示",
  "mode": "absolute",
  "window_title": "记事本",
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
