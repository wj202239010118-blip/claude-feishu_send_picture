"""
纯净 AI 截图哨兵 — Pure AI Screenshot Sentinel

【设计原则】
  脚本完全不监听 A 键，Ctrl+Shift+A 百分之百由飞书原生处理。
  只有当你按下 Ctrl+Shift+X 时，脚本才介入：
    1. 模拟按一下 Ctrl+Shift+A，唤起飞书截图工具
    2. 等待你完成截图（最多 20 秒）
    3. 截图完成后，把剪贴板里的图片替换为文件路径
"""

import hashlib
import os
import signal
import socket
import sys
import threading
import time
from datetime import datetime

import pyperclip
from PIL import ImageGrab, Image
from pynput import keyboard


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def to_int(v, fallback):
    try:
        n = int(v)
        return n if n >= 0 else fallback
    except Exception:
        return fallback


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def list_png_files(save_dir):
    try:
        names = os.listdir(save_dir)
    except Exception:
        return []
    out = []
    for name in names:
        if not name.lower().endswith(".png"):
            continue
        p = os.path.join(save_dir, name)
        try:
            if os.path.isfile(p):
                out.append((p, os.stat(p).st_mtime))
        except Exception:
            continue
    out.sort(key=lambda x: x[1], reverse=True)
    return [p for (p, _) in out]


def cleanup(save_dir, max_files):
    for p in list_png_files(save_dir)[max_files:]:
        try:
            os.remove(p)
            print(f"[GC] {os.path.basename(p)}")
        except Exception:
            pass


def format_path(file_path):
    """返回 Windows 风格绝对路径（反斜杠），Claude Code 最常用的格式。"""
    return os.path.abspath(file_path).replace("/", "\\")


def acquire_lock(port=54237):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


# ─── 核心：纯净 AI 哨兵 ───────────────────────────────────────────────────────

class PureAISentinel:
    """
    脚本对 A 键零感知。
    trigger() 在独立线程里运行完整的"模拟截图 → 等待 → 写路径"流程。
    """

    TIMEOUT_S = 20.0    # 等待截图完成的最长时间（秒）
    POLL_S    = 0.3     # 轮询剪贴板的间隔（秒）
    MAX_FILES = 15      # 保留的最大文件数量

    def __init__(self, save_dir, prefix="cap"):
        self.save_dir = save_dir
        self.prefix   = prefix
        self._busy      = False
        self._busy_lock = threading.Lock()
        ensure_dir(save_dir)

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def trigger(self):
        """由热键回调调用；防止并发。"""
        with self._busy_lock:
            if self._busy:
                print("[跳过] 上一次截图尚未完成，请稍后再试")
                return
            self._busy = True
        threading.Thread(target=self._run, daemon=True).start()

    # ── 内部流程 ──────────────────────────────────────────────────────────────

    def _get_hash(self):
        """取剪贴板图片的哈希，剪贴板无图片时返回 None。"""
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                return hashlib.blake2b(img.tobytes(), digest_size=16).hexdigest()
        except Exception:
            pass
        return None

    def _simulate_feishu(self):
        """用 pynput 模拟 Ctrl+Shift+A，唤起飞书截图工具。"""
        kb = keyboard.Controller()
        # 先把可能残留的物理按键全部释放，再等用户松手
        for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                  keyboard.Key.shift_l, keyboard.Key.shift_r):
            try:
                kb.release(k)
            except Exception:
                pass
        try:
            kb.release(keyboard.KeyCode(char='x'))
        except Exception:
            pass
        # 等待足够长，确保所有物理按键已抬起，避免 Ctrl+Shift+X+A 混合信号
        time.sleep(0.35)
        # 用 ctrl_l / shift_l（左键修饰符）模拟，飞书注册热键时用的是这两个
        with kb.pressed(keyboard.Key.ctrl_l):
            with kb.pressed(keyboard.Key.shift_l):
                kb.press('a')
                kb.release('a')

    def _run(self):
        try:
            old_hash = self._get_hash()
            print("")
            print(">>> [Step 1] Ctrl+Shift+X detected — releasing keys, wait 0.35s...")

            self._simulate_feishu()

            print(">>> [Step 2] Simulated Ctrl+Shift+A sent to Feishu — draw your region now")

            # 轮询等待剪贴板变化（超时 30 秒）
            deadline = time.time() + 30.0
            while time.time() < deadline:
                curr_hash = self._get_hash()
                if curr_hash and curr_hash != old_hash:
                    time.sleep(0.2)   # 给 OS 写稳剪贴板的时间
                    img = ImageGrab.grabclipboard()
                    if isinstance(img, Image.Image):
                        print(">>> [Step 3] New image detected in clipboard")
                        self._save_and_copy(img)
                        return
                time.sleep(self.POLL_S)

            print(">>> Timeout: no screenshot detected within 30s")

        except Exception as e:
            print(f">>> 发生异常: {e}")
        finally:
            with self._busy_lock:
                self._busy = False

    def _save_and_copy(self, img):
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.prefix}_{ts}.png"
        fpath    = os.path.join(self.save_dir, filename)

        img.save(fpath, "PNG")
        out_path = format_path(fpath)
        pyperclip.copy(out_path)

        print("-------------------------------------------")
        print(f"[完成] 路径已写入剪贴板")
        print(f"文件: {filename}")
        print(f"路径: {out_path}")
        print("-------------------------------------------")

        cleanup(self.save_dir, self.MAX_FILES)


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def main():
    # 单实例检测
    _lock = acquire_lock()
    if _lock is None:
        print("=" * 50)
        print("  检测到旧实例仍在运行！")
        print("  请关闭旧窗口，或执行：")
        print("    taskkill /f /im python.exe")
        print("    taskkill /f /im pythonw.exe")
        print("  然后重新双击启动")
        print("=" * 50)
        time.sleep(8)
        sys.exit(1)

    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feishu_uploads")
    sentinel = PureAISentinel(save_dir=save_dir, prefix="cap")

    print("=" * 50)
    print("  纯净 AI 截图哨兵已启动")
    print("=" * 50)
    print("")
    print("  Ctrl+Shift+A  ->  飞书原生截图（脚本零干预，剪贴板=图片）")
    print("  Ctrl+Shift+X  ->  AI 截图（自动唤起飞书，完成后剪贴板=路径）")
    print("")
    print(f"  保存目录: {save_dir}")
    print("  按 Ctrl+C 或关闭窗口停止")
    print("")

    # ── 热键监听：只跟踪 ctrl / shift / x，完全不记录 a ──────────────────────
    pressed = set()

    # When Ctrl is held, pynput sets key.char = '\x18' (ASCII 24, Ctrl+X),
    # NOT 'x' — so a plain char comparison always fails.
    # Fix: check vk (Windows virtual-key code, 0x58 = VK_X) as primary,
    # and fall back to matching the control character '\x18' for safety.
    def _is_x(key):
        if getattr(key, 'vk', None) == 0x58:          # VK_X, reliable on Windows
            return True
        c = getattr(key, 'char', None)
        return c in ('x', 'X', '\x18')                # '\x18' = Ctrl+X control char

    def on_press(key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            pressed.add('ctrl')
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            pressed.add('shift')
        elif _is_x(key):
            pressed.add('x')
        # 'a' is intentionally never tracked

        if {'ctrl', 'shift', 'x'} <= pressed:
            pressed.discard('x')   # remove immediately to prevent re-fire
            print(">>> [Key OK] Ctrl+Shift+X recognized")
            sentinel.trigger()

    def on_release(key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            pressed.discard('ctrl')
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            pressed.discard('shift')
        elif _is_x(key):
            pressed.discard('x')
        elif key == keyboard.Key.esc:
            pressed.clear()   # Esc clears stuck-key state

    stop_event = threading.Event()

    def on_stop(sig=None, frame=None):
        stop_event.set()

    signal.signal(signal.SIGINT, on_stop)
    try:
        signal.signal(signal.SIGTERM, on_stop)
    except AttributeError:
        pass

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        _lock.close()
        print("\n[已停止监听]")


if __name__ == "__main__":
    main()
