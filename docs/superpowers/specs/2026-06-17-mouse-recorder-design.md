# Mouse Recorder — 设计文档

## 概述

一款 Windows 鼠标/键盘录制与回放工具。支持录制鼠标移动、点击及键盘输入，通过全局热键触发回放，并提供轻量 GUI 窗口进行管理与配置。

## 功能清单

- 全局热键开始/停止录制（默认 Ctrl+Shift+R）
- 全局热键回放录制（默认 Ctrl+Shift+P）
- 支持绝对坐标 / 窗口相对坐标两种录制模式
- 支持 0.5x ~ 5x 倍速回放
- 支持循环回放（N 次或无限）
- 录制列表管理：查看、重命名、删除、裁剪头尾
- GUI 中可修改触发热键

## 技术栈

- Python 3.x
- pynput：全局鼠标/键盘钩子 + 输入模拟
- tkinter：桌面 GUI（Python 标准库）
- JSON：录制数据持久化

## 架构

| 模块 | 职责 |
|------|------|
| main.py | 入口，启动 GUI 消息循环 + 热键监听线程 |
| recorder.py | pynput Listener 捕获事件，打时间戳，合并输出 |
| player.py | 读取录制，pynput Controller 按时间线回放 |
| hotkey_manager.py | 管理全局热键生命周期，支持运行时修改 |
| storage.py | 录制文件的 CRUD 与 JSON 序列化 |
| gui.py | tkinter 窗口，按功能分区组织 UI |
| config.py | 用户配置（热键、默认速度等）读写 |

## 线程模型

- 主线程：tkinter GUI 事件循环
- 录制线程：pynput mouse/keyboard Listener（互斥于回放）
- 回放线程：按时间线逐事件注入（互斥于录制）
- 热键线程：pynput GlobalHotKeys 始终运行

## 录制文件格式

```json
{
  "name": "demo_2026-06-17",
  "mode": "absolute",
  "window_title": "记事本",
  "events": [
    {"type": "mouse_move",  "ms": 0,   "x": 500, "y": 300},
    {"type": "mouse_click", "ms": 234, "x": 500, "y": 300, "btn": "left", "down": true},
    {"type": "key_press",   "ms": 520, "key": "a"}
  ]
}
```

事件按 `ms`（相对录制起始毫秒偏移）升序排列。

## 文件结构

```
MouseRecorder/
├── main.py
├── recorder.py
├── player.py
├── hotkey_manager.py
├── storage.py
├── gui.py
├── config.py
├── recordings/           ← 录制文件
├── config.json           ← 用户配置
└── requirements.txt      ← pynput
```
