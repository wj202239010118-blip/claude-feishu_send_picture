# 飞书截图哨兵

两个快捷键，彻底分流：

| 快捷键 | 效果 |
|---|---|
| `Ctrl+Shift+A` | 飞书原生截图，剪贴板 = 图片（发 Gemini / 微信照常用） |
| `Ctrl+Shift+X` | AI 截图：脚本自动唤起飞书 → 你框选区域 → 剪贴板变路径（粘贴给 Claude） |

## 启动

双击 `开始监控.bat`（会弹 UAC 提权窗口，点"是"）。

## 文件说明

```
feishu_screenshot_guard.py   核心脚本
开始监控.bat                  启动入口
requirements.txt             Python 依赖（pynput / Pillow / pyperclip）
feishu_uploads/              截图自动保存到这里（最多保留 15 张）
```

## 第一次使用

1. 安装 Python 3.9+，勾选 "Add Python to PATH" 和 "Install py launcher"
2. 双击 `开始监控.bat`，首次会自动安装依赖

## 停止

关闭黑色窗口，或在窗口内按 `Ctrl+C`。
