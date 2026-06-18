"""工具函数"""

import os
import sys


def get_app_dir():
    """获取应用根目录 — 无论源码运行还是 PyInstaller 打包都正确"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后：EXE 所在目录
        return os.path.dirname(sys.executable)
    else:
        # 源码运行：脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))
