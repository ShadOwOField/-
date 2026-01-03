from __future__ import annotations

import sys
import os
import math
import ctypes
import re
import logging
import threading
import time
import traceback
import importlib
import subprocess
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

def _in_venv() -> bool:
    return hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix or hasattr(sys, "real_prefix")

def _run_pip_install(pkg: str, use_user: bool) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "pip", "install", pkg]
    if use_user:
        cmd.append("--user")
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def ensure_customtkinter_with_gui(pkg_name: str = "customtkinter", timeout_estimate: int = 60):
    try:
        return importlib.import_module(pkg_name)
    except Exception:
        pass

    root = tk.Tk()
    root.title("Установка зависимостей")
    DARK_BG = "#0b0d10"
    FG = "#e6eef8"
    ACCENT = "#2b5fa0"
    root.configure(bg=DARK_BG)
    root.resizable(False, False)

    w, h = 420, 140
    try:
        sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
        x = (sw - w) // 2; y = (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        root.geometry(f"{w}x{h}")

    frm = tk.Frame(root, bg=DARK_BG)
    frm.pack(fill="both", expand=True, padx=12, pady=12)

    lbl_title = tk.Label(frm, text="Требуется библиотека customtkinter", bg=DARK_BG, fg=FG, font=("Helvetica", 13, "bold"))
    lbl_title.pack(anchor="w", pady=(0, 8))

    lbl_info = tk.Label(frm, text="Устанавливаем пакет. Пожалуйста, дождитесь завершения.", bg=DARK_BG, fg=FG, font=("Helvetica", 10))
    lbl_info.pack(anchor="w")

    progress = ttk.Progressbar(frm, orient="horizontal", length=380, mode="determinate")
    progress.pack(pady=(12, 6))

    lbl_status = tk.Label(frm, text="Ожидание...", bg=DARK_BG, fg=FG, font=("Helvetica", 9))
    lbl_status.pack(anchor="w")

    btn_frame = tk.Frame(frm, bg=DARK_BG)
    btn_frame.pack(fill="x", pady=(8, 0))

    btn_cancel = tk.Button(btn_frame, text="Отмена", command=root.destroy, bg="#222", fg=FG)
    btn_cancel.pack(side="right")

    stop_flag = {"cancel": False, "done": False}
    result_holder = {"proc": None, "success": False, "out": "", "err": ""}

    def install_thread():
        use_user = not _in_venv()
        cmd = [sys.executable, "-m", "pip", "install", pkg_name]
        if use_user:
            cmd.append("--user")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except Exception as exc:
            result_holder["out"] = ""
            result_holder["err"] = str(exc)
            result_holder["success"] = False
            stop_flag["done"] = True
            return

        result_holder["proc"] = proc
        stdout_accum = ""
        start_time = time.time()
        while True:
            if stop_flag["cancel"]:
                try:
                    proc.terminate()
                except Exception:
                    pass
                result_holder["out"] = stdout_accum
                result_holder["err"] = "Отменено пользователем"
                result_holder["success"] = False
                stop_flag["done"] = True
                return
            line = proc.stdout.readline()
            if line:
                stdout_accum += line
            if proc.poll() is not None:
                rest = proc.stdout.read() or ""
                stdout_accum += rest
                break
            time.sleep(0.05)

        rc = proc.returncode
        result_holder["out"] = stdout_accum
        result_holder["err"] = ""
        result_holder["success"] = (rc == 0)
        if rc != 0:
            try:
                cp = _run_pip_install(pkg_name, use_user)
                result_holder["out"] += cp.stdout or ""
                result_holder["err"] += cp.stderr or ""
            except Exception:
                pass
        stop_flag["done"] = True

    t = threading.Thread(target=install_thread, daemon=True)
    t.start()

    start_time = time.time()
    est_total = float(max(10, timeout_estimate))
    last_update = 0.0

    def update_loop():
        if stop_flag["done"]:
            if result_holder["success"]:
                progress['value'] = 100
                lbl_status.config(text="Установка завершена успешно. Подключение модуля...")
                root.update_idletasks()
                time.sleep(0.3)
                try:
                    mod = importlib.import_module(pkg_name)
                    root.destroy()
                    return mod
                except Exception as exc:
                    tb = traceback.format_exc()
                    lbl_status.config(text="Ошибка импорта после установки")
                    messagebox.showerror("Ошибка", f"Пакет установлен, но импорт не удался:\n{exc}\n\nДетали в консоли.")
                    print("=== pip output ===")
                    print(result_holder.get("out", ""))
                    print(result_holder.get("err", ""))
                    print(tb)
                    root.destroy()
                    raise SystemExit(1)
            else:
                progress['value'] = 0
                lbl_status.config(text="Установка не удалась")
                out = result_holder.get("out", "")
                err = result_holder.get("err", "")
                detail = (out + "\n\n" + err).strip()
                if not detail:
                    detail = "Нет дополнительной информации."
                messagebox.showerror("Не удалось установить пакет",
                                     "Установка customtkinter не удалась.\n\n" + detail)
                root.destroy()
                raise SystemExit(1)
            return

        elapsed = time.time() - start_time
        target = min(92.0, (elapsed / est_total) * 92.0)
        pulse = (1 + 0.03 * (1 + (time.time() % 1)))
        new_val = min(92.0, target * pulse)
        cur = progress['value']
        if new_val > cur:
            progress['value'] = new_val
        else:
            progress['value'] = min(92.0, cur + 0.3)

        lbl_status.config(text=f"Устанавливается... {int(progress['value'])}%")
        root.update_idletasks()
        root.after(120, update_loop)

    root.after(120, update_loop)
    def on_cancel():
        if messagebox.askyesno("Отмена", "Прервать установку?"):
            stop_flag["cancel"] = True
            lbl_status.config(text="Отмена...")
    btn_cancel.configure(command=on_cancel)

    root.mainloop()

    try:
        return importlib.import_module(pkg_name)
    except Exception as exc:
        print("Не удалось импортировать пакет после установки:", exc, file=sys.stderr)
        raise ImportError(f"Не удалось импортировать '{pkg_name}' после установки") from exc

try:
    ctk = importlib.import_module("customtkinter")
except Exception:
    ctk = ensure_customtkinter_with_gui("customtkinter")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass(frozen=True)
class Config:
    appearance_mode: str = "dark"
    color_theme: str = "dark-blue"
    win_w: int = 300
    win_h: int = 420
    win_alpha: float = 0.97
    resizable: Tuple[bool, bool] = (False, False)
    entry_h: int = 38
    compact_entry_h: int = 28
    btn_h: int = 42
    btn_corner: int = 6
    container_pad: int = 8
    max_input: int = 64
    try:
        ui_font = ctk.CTkFont(size=13)
        bold_font = ctk.CTkFont(size=14, weight="bold")
        small_font = ctk.CTkFont(size=12, weight="bold")
    except Exception:
        ui_font = ("Helvetica", 13)
        bold_font = ("Helvetica", 14, "bold")
        small_font = ("Helvetica", 12, "bold")
    panel: str = "#0d1114"
    surface: str = "#0b0d10"
    card: str = "#0f1316"
    accent: str = "#2b5fa0"
    accent_alt: str = "#233240"
    text: str = "#e6eef8"
    muted: str = "#7e8a94"

CFG = Config()
try:
    ctk.set_appearance_mode(CFG.appearance_mode)
    ctk.set_default_color_theme(CFG.color_theme)
except Exception:
    pass

_SAFE_EXPR_RE = re.compile(r"^[0-9A-Za-z\s\.\,\+\-\*\/\%\^\(\)eEjJ,]*$")

def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

def adjust_brightness(hex_color: str, factor: float) -> str:
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return rgb_to_hex(r, g, b)
    except Exception:
        return hex_color

def hover_color(hex_color: str, factor: float = 0.06) -> str:
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return rgb_to_hex(r, g, b)
    except Exception:
        return hex_color

def try_enable_acrylic(win: tk.Tk | tk.Toplevel, use_acrylic: bool = True, gradient_color: int = 0x990d1114) -> bool:
    if sys.platform != "win32":
        return False
    try:
        hwnd = win.winfo_id()

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [("AccentState", ctypes.c_int),
                        ("AccentFlags", ctypes.c_int),
                        ("GradientColor", ctypes.c_uint),
                        ("AnimationId", ctypes.c_int)]

        class WINCOMPATTRDATA(ctypes.Structure):
            _fields_ = [("Attribute", ctypes.c_int),
                        ("Data", ctypes.c_void_p),
                        ("SizeOfData", ctypes.c_size_t)]

        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
        ACCENT_ENABLE_BLURBEHIND = 3

        ap = ACCENTPOLICY()
        ap.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND if use_acrylic else ACCENT_ENABLE_BLURBEHIND
        ap.AccentFlags = 0x20
        ap.GradientColor = ctypes.c_uint(gradient_color)

        data = WINCOMPATTRDATA()
        data.Attribute = 19
        data.SizeOfData = ctypes.sizeof(ap)
        data.Data = ctypes.cast(ctypes.pointer(ap), ctypes.c_void_p)

        ctypes.windll.user32.SetWindowCompositionAttribute(ctypes.c_void_p(hwnd), ctypes.byref(data))
        return True
    except Exception:
        return False

def format_number(val: Union[int, float], decimals: int = 5, use_comma: bool = True) -> str:
    try:
        s = f"{float(val):.{decimals}f}"
        return s.replace(".", ",") if use_comma else s
    except Exception:
        return str(val)

def parse_number(s: str) -> Union[float, complex]:
    s = (s or "").strip()
    if not s:
        raise ValueError("Empty")
    if "j" in s or "J" in s:
        return complex(s.replace(",", "."))
    return float(s.replace(",", "."))

class Animator:
    def __init__(self, root: tk.Tk | tk.Toplevel):
        self.root = root
        self._jobs: Dict[str, int] = {}

    def cancel(self, name: str):
        job = self._jobs.pop(name, None)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass

    def schedule(self, name: str, delay_ms: int, fn: Callable[[], None]):
        self.cancel(name)
        self._jobs[name] = self.root.after(delay_ms, fn)

    def fade_in(self, win: tk.Toplevel | tk.Tk, target_alpha: float = 1.0, duration: int = 220, steps: int = 12):
        try:
            win.attributes("-alpha", 0.0)
        except Exception:
            try:
                win.wm_attributes("-alpha", 0.0)
            except Exception:
                return

        step_ms = max(1, duration // steps)

        def _step(i: int):
            a = (i + 1) / steps * target_alpha
            try:
                win.attributes("-alpha", a)
            except Exception:
                try:
                    win.wm_attributes("-alpha", a)
                except Exception:
                    return
            if i + 1 < steps:
                self.schedule(f"fade_{id(win)}", step_ms, lambda: _step(i + 1))

        _step(0)

    def pulse_color(self, widget: ctk.CTkButton, base_color: str, min_factor: float = 0.88, max_factor: float = 1.12,
                    period_ms: int = 1200, steps: int = 20, name: Optional[str] = None):
        if name is None:
            name = f"pulse_{id(widget)}"
        self.cancel(name)
        half = steps // 2
        step_ms = max(10, period_ms // steps)

        def frame(i: int = 0):
            if i < half:
                t = i / max(1, half - 1)
                factor = min_factor + (max_factor - min_factor) * t
            else:
                t = (i - half) / max(1, steps - half - 1)
                factor = max_factor - (max_factor - min_factor) * t
            try:
                widget.configure(fg_color=adjust_brightness(base_color, factor))
            except Exception:
                pass
            self._jobs[name] = self.root.after(step_ms, lambda: frame((i + 1) % steps))

        frame(0)

    def press_animation(self, widget: ctk.CTkButton, shrink_factor: float = 0.94, dur_ms: int = 120):
        try:
            orig_w = widget.cget("width") or widget.winfo_width()
            orig_h = widget.cget("height") or widget.winfo_height()
        except Exception:
            orig_w = orig_h = None

        try:
            if orig_w and orig_h:
                widget.configure(width=int(orig_w * shrink_factor), height=int(orig_h * shrink_factor))
                widget.update_idletasks()
                self.root.after(dur_ms, lambda: widget.configure(width=orig_w, height=orig_h))
                return
        except Exception:
            pass

        try:
            orig = widget.cget("fg_color")
            widget.configure(fg_color=adjust_brightness(orig, 0.85))
            self.root.after(dur_ms, lambda: widget.configure(fg_color=orig))
        except Exception:
            pass

    def animate_numeric_change(self, entry: ctk.CTkEntry, start: float, end: float, steps: int = 8, step_ms: int = 25,
                               decimals: int = 5, use_comma: bool = True):
        if steps <= 1:
            entry.delete(0, "end")
            entry.insert(0, format_number(end, decimals, use_comma))
            return

        def frame(i: int):
            t = i / steps
            val = start + (end - start) * t
            txt = f"{val:.{decimals}f}"
            if use_comma:
                txt = txt.replace(".", ",")
            entry.delete(0, "end")
            entry.insert(0, txt)
            if i < steps:
                self.root.after(step_ms, lambda: frame(i + 1))

        frame(0)

class CalculatorApp:
    FIGURES_MAP: Dict[str, List[str]] = {
        "Прямоугольник": ["Длина", "Ширина"],
        "Круг": ["Радиус"],
        "Треуг. (осн.,выс.)": ["Основание", "Высота"],
        "Треуг. (3 стороны)": ["a", "b", "c"],
        "Куб": ["a"],
        "Параллелепипед": ["Длина", "Ширина", "Высота"],
        "Шар": ["R"],
        "Цилиндр": ["R", "H"],
        "Конус": ["R", "H"],
        "Пирамида": ["Sосн", "H"],
    }

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Калькулятор — Compact Strict Dark")
        self.root.geometry(f"{CFG.win_w}x{CFG.win_h}")
        self.root.resizable(*CFG.resizable)
        try:
            self.root.wm_attributes("-alpha", 0.0)
        except Exception:
            pass
        try_enable_acrylic(self.root, use_acrylic=True)

        self.anim = Animator(self.root)
        self.anim.fade_in(self.root, target_alpha=CFG.win_alpha, duration=260, steps=14)

        self.max_input_chars = CFG.max_input
        self._hover_cache: Dict[str, str] = {}
        self._accent_buttons: List[ctk.CTkButton] = []
        self._build_ui()

        for b in self._accent_buttons:
            self.anim.pulse_color(b, CFG.accent, min_factor=0.9, max_factor=1.12, period_ms=1600, steps=26)

        self.root.bind("<Return>", lambda e: self._on_press("="))
        self.root.bind("<BackSpace>", lambda e: self.backspace())
        self.root.bind("<Escape>", lambda e: self.clear_all())

    def _hover_cached(self, color: str) -> str:
        if color not in self._hover_cache:
            self._hover_cache[color] = hover_color(color)
        return self._hover_cache[color]

    def _create_button(self, parent, text: str, fg_color: str, command: Callable[[], None], width: Optional[int] = None) -> ctk.CTkButton:
        btn = ctk.CTkButton(parent, text=text, corner_radius=CFG.btn_corner, fg_color=fg_color,
                            hover_color=self._hover_cached(fg_color), height=CFG.btn_h,
                            font=CFG.ui_font, command=command, text_color=CFG.text)
        if width:
            try:
                btn.configure(width=width)
            except Exception:
                pass
        return btn

    def _attach_focus_highlight(self, entry: ctk.CTkEntry):
        try:
            orig = entry.cget("fg_color")
        except Exception:
            orig = CFG.surface
        focused = adjust_brightness(orig, 1.12)

        def on_in(e=None):
            try:
                entry.configure(fg_color=focused)
            except Exception:
                pass

        def on_out(e=None):
            try:
                entry.configure(fg_color=orig)
            except Exception:
                pass

        entry.bind("<FocusIn>", on_in)
        entry.bind("<FocusOut>", on_out)

    def _build_ui(self):
        pad = CFG.container_pad
        container = ctk.CTkFrame(self.root, corner_radius=8, fg_color=CFG.panel)
        container.pack(fill="both", expand=True, padx=pad, pady=pad)
        self.container = container

        self.entry_var = tk.StringVar()
        self.display = ctk.CTkEntry(container, textvariable=self.entry_var, corner_radius=6,
                                    fg_color=CFG.surface, text_color=CFG.text, height=CFG.entry_h,
                                    font=CFG.bold_font)
        self.display.grid(row=0, column=0, columnspan=4, padx=10, pady=(12, 6), sticky="we")
        self._attach_focus_highlight(self.display)

        keys = [
            ("7", "8", "9", "/"),
            ("4", "5", "6", "*"),
            ("1", "2", "3", "-"),
            ("0", ".", "=", "+"),
        ]
        for r, row in enumerate(keys, start=1):
            for c, key in enumerate(row):
                fg = CFG.card
                if key == "=":
                    fg = CFG.accent
                elif key in "+-*/%":
                    fg = CFG.accent_alt

                btn = self._create_button(container, key, fg, lambda ch=key: self._on_press(ch))
                btn.configure(command=lambda b=btn, ch=key: (self.anim.press_animation(b), self._on_press(ch)))
                btn.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
                if fg == CFG.accent:
                    self._accent_buttons.append(btn)

        specials = [
            ("C", self.clear_all, CFG.accent_alt),
            ("⌫", self.backspace, CFG.card),
            ("xʸ", self.power_window, CFG.card),
            ("□", self.figures_window_compact_centered, CFG.accent_alt),
        ]
        for i, (txt, cmd, color) in enumerate(specials):
            btn = self._create_button(container, txt, color, cmd)
            btn.configure(command=lambda b=btn, fn=cmd: (self.anim.press_animation(b), self.root.after(110, fn)))
            btn.grid(row=5, column=i, padx=6, pady=(6, 10), sticky="nsew")
            if color == CFG.accent:
                self._accent_buttons.append(btn)

        for i in range(4):
            container.grid_columnconfigure(i, weight=1)

        footer = ctk.CTkLabel(container, text="Compact • Strict • Dark", text_color=CFG.muted, anchor="center", font=CFG.ui_font)
        footer.grid(row=6, column=0, columnspan=4, pady=(0, 8))

    def _on_press(self, ch: str):
        if ch == "=":
            self.evaluate()
            return
        cur = self.entry_var.get()
        if len(cur) >= self.max_input_chars:
            return
        self.display.insert("end", ch)

    def evaluate(self):
        expr = self.entry_var.get().strip()
        if not expr:
            return
        expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", ".")
        if not _SAFE_EXPR_RE.match(expr) or "__" in expr or "_" in expr:
            self._show_message("Ошибка", "Недопустимые символы в выражении", is_error=True)
            return
        try:
            allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("__")}
            allowed.update({"pi": math.pi, "e": math.e})
            result = eval(expr, {"__builtins__": None}, allowed)
            s = str(result)
            self.display.delete(0, "end")
            if len(s) > 32:
                self.display.insert(0, "Результат слишком длинный")
                self._show_full_result(s)
            else:
                self.display.insert(0, s)
        except Exception:
            self._show_message("Ошибка", "Неверное выражение", is_error=True)

    def clear_all(self):
        self.display.delete(0, "end")

    def backspace(self):
        cur = self.entry_var.get()
        if cur:
            try:
                self.display.delete("end-2c", "end-1c")
            except Exception:
                self.display.delete(max(0, len(cur) - 1), "end")

    def _show_message(self, title: str, message: str, is_error: bool = False):
        win = ctk.CTkToplevel(self.root)
        win.title(title)
        win.geometry("320x110")
        win.transient(self.root); win.grab_set()
        try_enable_acrylic(win, use_acrylic=True)
        self.anim.fade_in(win, target_alpha=1.0, duration=220, steps=12)

        frame = ctk.CTkFrame(win, corner_radius=8, fg_color=CFG.panel)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        lbl = ctk.CTkLabel(frame, text=message, wraplength=280, text_color=("#ffb4b4" if is_error else CFG.text), font=CFG.ui_font)
        lbl.pack(pady=(8, 8))
        ctk.CTkButton(frame, text="Закрыть", fg_color=CFG.accent, command=win.destroy, font=CFG.ui_font, text_color=CFG.text).pack(pady=(0, 6))

    def _show_full_result(self, text: str):
        win = ctk.CTkToplevel(self.root)
        win.title("Результат (полный)")
        win.geometry("480x260")
        win.transient(self.root); win.grab_set()
        try_enable_acrylic(win, use_acrylic=True)
        self.anim.fade_in(win, target_alpha=1.0, duration=260, steps=14)

        frame = ctk.CTkFrame(win, corner_radius=8, fg_color=CFG.panel)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        txt = ctk.CTkTextbox(frame, width=440, height=200, corner_radius=6, fg_color=CFG.surface, font=CFG.ui_font)
        txt.pack(expand=True, fill="both", padx=6, pady=6)
        txt.insert("0.0", text)
        txt.configure(state="disabled")
        ctk.CTkButton(frame, text="Закрыть", fg_color=CFG.accent, command=win.destroy, font=CFG.ui_font, text_color=CFG.text).pack(pady=(6, 0))

    def power_window(self):
        win_w, win_h = 320, 260
        win = ctk.CTkToplevel(self.root)
        win.title("Степень xʸ")
        self.root.update_idletasks()
        try:
            rx = self.root.winfo_rootx(); ry = self.root.winfo_rooty()
            rw = self.root.winfo_width(); rh = self.root.winfo_height()
            x = rx + max(0, (rw - win_w) // 2); y = ry + max(0, (rh - win_h) // 2)
            win.geometry(f"{win_w}x{win_h}+{x}+{y}")
        except Exception:
            sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
            x = (sw - win_w) // 2; y = (sh - win_h) // 2
            win.geometry(f"{win_w}x{win_h}+{x}+{y}")
        win.resizable(False, False)
        win.transient(self.root); win.grab_set()
        try_enable_acrylic(win, use_acrylic=True)
        self.anim.fade_in(win, target_alpha=1.0, duration=220, steps=12)

        f = ctk.CTkFrame(win, corner_radius=6, fg_color=CFG.panel)
        f.pack(fill="both", expand=True, padx=10, pady=10)

        inputs = ctk.CTkFrame(f, fg_color=f.cget("fg_color"))
        inputs.pack(fill="both", expand=True, pady=(0, 6))

        ctk.CTkLabel(inputs, text="x (основание):", font=CFG.ui_font, text_color=CFG.text).pack(anchor="w", pady=(6, 2))
        ex = ctk.CTkEntry(inputs, corner_radius=6, font=CFG.ui_font, fg_color=CFG.surface, text_color=CFG.text, height=CFG.compact_entry_h)
        ex.pack(fill="x", pady=(0, 6)); self._attach_focus_highlight(ex)

        ctk.CTkLabel(inputs, text="y (показатель):", font=CFG.ui_font, text_color=CFG.text).pack(anchor="w", pady=(6, 2))
        ey = ctk.CTkEntry(inputs, corner_radius=6, font=CFG.ui_font, fg_color=CFG.surface, text_color=CFG.text, height=CFG.compact_entry_h)
        ey.pack(fill="x", pady=(0, 6)); self._attach_focus_highlight(ey)

        res_lbl = ctk.CTkLabel(inputs, text="", text_color=CFG.text, wraplength=300, justify="left", font=CFG.ui_font)
        res_lbl.pack(fill="x", pady=(6, 2))

        bottom_frame = ctk.CTkFrame(f, fg_color=f.cget("fg_color"))
        bottom_frame.pack(side="bottom", fill="x")
        bottom_frame.configure(height=70)
        bottom_frame.pack_propagate(False)

        btn = ctk.CTkButton(bottom_frame, text="Вычислить", fg_color=CFG.accent, width=285, corner_radius=6,
                            font=CFG.ui_font, text_color=CFG.text, hover_color=self._hover_cached(CFG.accent))
        btn.pack(side="right", padx=(0, 8), pady=(10, 10))

        def do_progress_animation(label: ctk.CTkButton, running: Dict[str, bool]):
            dots = 0

            def frame():
                nonlocal dots
                if not running.get("run"):
                    label.configure(text="Вычислить")
                    return
                dots = (dots + 1) % 4
                label.configure(text="Вычисление" + "." * dots)
                self.root.after(300, frame)

            frame()

        def compute_and_show():
            self.anim.press_animation(btn)
            running = {"run": True}
            do_progress_animation(btn, running)
            try:
                x = parse_number(ex.get().strip())
                y = parse_number(ey.get().strip())
                res = x ** y
                formatted = str(res)
                short = formatted if len(formatted) <= 64 else (formatted[:61] + "...")
                res_lbl.configure(text=f"Результат: {short}", text_color=CFG.text)
                if len(formatted) > 64:
                    self._show_full_result(formatted)
            except ValueError:
                res_lbl.configure(text="Ошибка ввода: ожидаются числа", text_color="#ffb4b4")
            except OverflowError:
                res_lbl.configure(text="Ошибка: переполнение результата", text_color="#ffb4b4")
            except Exception:
                res_lbl.configure(text="Ошибка при вычислении", text_color="#ffb4b4")
            finally:
                running["run"] = False
                btn.configure(text="Вычислить")

        btn.configure(command=compute_and_show)

    def figures_window_compact_centered(self):
        win_w, win_h = 480, 220
        win = ctk.CTkToplevel(self.root)
        win.title("Фигуры — компактно")
        self.root.update_idletasks()
        try:
            rx = self.root.winfo_rootx(); ry = self.root.winfo_rooty()
            rw = self.root.winfo_width(); rh = self.root.winfo_height()
            x = rx + max(0, (rw - win_w) // 2); y = ry + max(0, (rh - win_h) // 2)
            win.geometry(f"{win_w}x{win_h}+{x}+{y}")
        except Exception:
            sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
            x = (sw - win_w) // 2; y = (sh - win_h) // 2
            win.geometry(f"{win_w}x{win_h}+{x}+{y}")
        win.resizable(False, False)
        win.transient(self.root); win.grab_set()
        try_enable_acrylic(win, use_acrylic=True)
        self.anim.fade_in(win, target_alpha=1.0, duration=220, steps=12)

        main = ctk.CTkFrame(win, corner_radius=8, fg_color=CFG.panel)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        top = ctk.CTkFrame(main, corner_radius=6, fg_color=CFG.surface)
        top.pack(fill="x", padx=6, pady=(6, 8))
        top.grid_columnconfigure(0, weight=1); top.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(top, text="Фигура", font=CFG.ui_font, text_color=CFG.text).grid(row=0, column=0, sticky="e", padx=(0, 6))

        names = list(self.FIGURES_MAP.keys())
        choice = ctk.CTkOptionMenu(top, values=names, width=300, fg_color=CFG.surface, button_color=CFG.accent_alt,
                                   text_color=CFG.text, dropdown_fg_color=("#f3f3f3", CFG.surface),
                                   dropdown_text_color=("#333333", CFG.text), corner_radius=6, font=CFG.ui_font,
                                   command=lambda v: self._populate_fields_for_figure_centered(v, fields_frame))
        choice.set(names[0])
        choice.grid(row=0, column=1, sticky="w", padx=(6, 0))

        fields_frame = ctk.CTkFrame(main, corner_radius=6, fg_color=CFG.panel)
        fields_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self._populate_fields_for_figure_centered(names[0], fields_frame)

    def _populate_fields_for_figure_centered(self, figure_name: str, container: ctk.CTkFrame):
        for w in container.winfo_children():
            w.destroy()

        fields = self.FIGURES_MAP.get(figure_name, [])
        entries: List[ctk.CTkEntry] = []

        inner = ctk.CTkFrame(container, fg_color=container.cget("fg_color"))
        inner.pack(fill="both", expand=True, padx=4, pady=2)

        inputs_holder = ctk.CTkFrame(inner, fg_color=inner.cget("fg_color"))
        inputs_holder.pack(fill="x", side="top", pady=(2, 4))

        bottom_frame = ctk.CTkFrame(inner, fg_color=inner.cget("fg_color"))
        bottom_frame.pack(side="bottom", fill="x", pady=(4, 2))

        if not fields:
            ctk.CTkLabel(inputs_holder, text="Нет параметров для этой фигуры", font=CFG.ui_font, text_color=CFG.muted).pack(padx=8, pady=6)
        else:
            for f in fields:
                row = ctk.CTkFrame(inputs_holder, fg_color=inputs_holder.cget("fg_color"))
                row.pack(fill="x", padx=6, pady=2)

                ctk.CTkLabel(row, text=f + ":", width=70, anchor="e", font=CFG.ui_font, text_color=CFG.text).pack(side="left", padx=(0, 8))

                ctrl = ctk.CTkFrame(row, fg_color=row.cget("fg_color"))
                ctrl.pack(side="left", fill="x", expand=True, padx=(0, 6))

                entry_width = 260
                e = ctk.CTkEntry(ctrl, corner_radius=6, font=CFG.ui_font, fg_color=CFG.surface, text_color=CFG.text,
                                height=CFG.compact_entry_h, width=entry_width)
                e.pack(side="left", fill="x", expand=True)
                self._attach_focus_highlight(e)

                spin_bg = ctrl.cget("fg_color")
                spin_frame = ctk.CTkFrame(ctrl, fg_color=spin_bg)
                spin_frame.pack(side="right", padx=(8, 0), pady=0)

                btn_w = 36
                btn_h = CFG.compact_entry_h
                common_opts = dict(width=btn_w, height=btn_h, corner_radius=6,
                                   fg_color=spin_bg, hover_color=spin_bg,
                                   font=CFG.small_font, text_color=CFG.text, border_width=0)

                btn_dec = ctk.CTkButton(spin_frame, text="▼", **common_opts)
                btn_dec.pack(side="right", padx=(6, 0))
                btn_inc = ctk.CTkButton(spin_frame, text="▲", **common_opts)
                btn_inc.pack(side="right")

                if not e.get().strip():
                    e.insert(0, format_number(0))

                def make_spin_handlers(entry: ctk.CTkEntry, step: float = 1.0, decimals: int = 5):
                    def set_val(val: float):
                        entry.delete(0, "end")
                        entry.insert(0, format_number(val, decimals=decimals))

                    def inc():
                        try:
                            v = parse_number(entry.get())
                            if isinstance(v, complex):
                                return
                            start = float(v); target = start + step
                            self.anim.animate_numeric_change(entry, start, target, steps=9, step_ms=22, decimals=decimals)
                        except Exception:
                            set_val(step)

                    def dec():
                        try:
                            v = parse_number(entry.get())
                            if isinstance(v, complex):
                                return
                            start = float(v); target = start - step
                            self.anim.animate_numeric_change(entry, start, target, steps=9, step_ms=22, decimals=decimals)
                        except Exception:
                            set_val(0.0)

                    return inc, dec

                inc_fn, dec_fn = make_spin_handlers(e, step=1.0, decimals=5)
                btn_inc.configure(command=lambda b=btn_inc, fn=inc_fn: (self.anim.press_animation(b), self.root.after(80, fn)))
                btn_dec.configure(command=lambda b=btn_dec, fn=dec_fn: (self.anim.press_animation(b), self.root.after(80, fn)))

                entries.append(e)

        res_lbl = ctk.CTkLabel(bottom_frame, text="", text_color=CFG.text, wraplength=420, justify="left", font=CFG.ui_font)
        res_lbl.pack(side="left", padx=(6, 4))

        def compute_and_show():
            try:
                vals = [entry.get() for entry in entries]

                def getf(i: int) -> float:
                    v = parse_number(vals[i])
                    if isinstance(v, complex):
                        raise ValueError("Требуется вещественное число")
                    return float(v)

                area = peri = vol = None
                name = figure_name
                if name == "Прямоугольник":
                    a = getf(0); b = getf(1); area = a * b; peri = 2 * (a + b)
                elif name == "Круг":
                    r = getf(0); area = math.pi * r * r; peri = 2 * math.pi * r
                elif name == "Треуг. (осн.,выс.)":
                    a = getf(0); h = getf(1); area = 0.5 * a * h
                elif name == "Треуг. (3 стороны)":
                    a = getf(0); b = getf(1); c = getf(2); peri = a + b + c
                elif name == "Куб":
                    a = getf(0); area = 6 * a * a; vol = a ** 3
                elif name == "Параллелепипед":
                    a = getf(0); b = getf(1); c = getf(2); area = 2 * (a * b + b * c + a * c); vol = a * b * c
                elif name == "Шар":
                    r = getf(0); area = 4 * math.pi * r * r; vol = 4 / 3 * math.pi * r ** 3
                elif name == "Цилиндр":
                    r = getf(0); h = getf(1); area = 2 * math.pi * r * (r + h); vol = math.pi * r * r * h
                elif name == "Конус":
                    r = getf(0); h = getf(1); slant = math.sqrt(r * r + h * h); area = math.pi * r * (r + slant); vol = 1 / 3 * math.pi * r * r * h
                elif name == "Пирамида":
                    S = getf(0); h = getf(1); vol = 1 / 3 * S * h

                parts: List[str] = []
                if area is not None:
                    parts.append(f"📐 Площадь: {area:.4f}")
                if peri is not None:
                    parts.append(f"📏 Периметр/Стороны: {peri:.4f}")
                if vol is not None:
                    parts.append(f"📦 Объём: {vol:.4f}")
                res_lbl.configure(text="\n".join(parts) if parts else "Нет данных для выбранной фигуры", text_color=CFG.text)
            except ValueError:
                res_lbl.configure(text="Ошибка ввода: ожидаются числа", text_color="#ffb4b4")
            except Exception:
                res_lbl.configure(text="Ошибка при вычислении", text_color="#ffb4b4")

        calc_btn = ctk.CTkButton(bottom_frame, text="Вычислить", fg_color=CFG.accent, width=140, corner_radius=6,
                                command=lambda: (self.anim.press_animation(calc_btn), self.root.after(110, compute_and_show)),
                                font=CFG.ui_font, text_color=CFG.text, hover_color=self._hover_cached(CFG.accent))
        calc_btn.pack(side="right", padx=(0, 8), pady=(6, 4))
        self.anim.pulse_color(calc_btn, CFG.accent, min_factor=0.94, max_factor=1.08, period_ms=1600, steps=20)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    CalculatorApp().run()
