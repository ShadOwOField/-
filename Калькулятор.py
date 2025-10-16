try:
    import ttkbootstrap as tb
    THEME_AVAILABLE = True
except Exception:
    tb = None
    THEME_AVAILABLE = False

import tkinter as tk
from tkinter import ttk, messagebox
import math

class CalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Калькулятор')
        self.root.geometry('240x295')
        self.root.resizable(False, False)
        self.max_input_chars = 20

        if THEME_AVAILABLE:
            tb.Style('darkly')
        else:
            self.root.configure(bg='#222831')
        self.container = ttk.Frame(self.root, padding=4)
        self.container.pack(fill='both', expand=True)

        self.build_ui()

    def _center(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _on_validate(self, proposed: str) -> bool:
        # allow empty, digits, operators and a single dot; but limit length
        if len(proposed) > getattr(self, 'max_input_chars', 20):
            return False
        return True

    def _show_msg(self, title: str, message: str, is_error: bool = False):
        # simple dark-themed modal to replace messagebox for consistency
        win = tk.Toplevel(self.root)
        win.transient(self.root)
        win.grab_set()
        win.title(title)
        win.resizable(False, False)
        if THEME_AVAILABLE:
            try:
                style = tb.Style()
                bg = style.colors.bg
            except Exception:
                bg = '#111827'
        else:
            bg = '#111827'
        win.configure(bg=bg)
        fg = '#ffffff' if not is_error else '#ffdddd'
        lbl = tk.Label(win, text=message, bg=bg, fg=fg, font=('Segoe UI', 10) if THEME_AVAILABLE else ('Arial', 10), wraplength=320, justify='left')
        lbl.pack(padx=12, pady=12)
        btn = ttk.Button(win, text='Закрыть окошечко)', command=win.destroy)
        btn.pack(pady=(0,12))
        self._center()

    def make_btn(self, parent, text, command, width=5, kind='digit'):
        if THEME_AVAILABLE:
            boot = 'secondary' if kind == 'digit' else ('primary' if kind == 'op' else 'warning')
            return tb.Button(parent, text=text, command=command, bootstyle=boot + '.outline', width=width)
        else:
            style = ttk.Style()
            try:
                style.configure('Digit.TButton', background='#e9ecef', foreground='#111111', font=('Arial', 12), padding=6)
                style.configure('Op.TButton', background='#0d6efd', foreground='#ffffff', font=('Arial', 12), padding=6)
                style.configure('Spec.TButton', background='#ffc107', foreground='#222831', font=('Arial', 12), padding=6)
                style.map('Op.TButton', background=[('active', '#0056d6')])
            except Exception:
                pass
            style_name = 'Digit.TButton' if kind == 'digit' else ('Op.TButton' if kind == 'op' else 'Spec.TButton')
            return ttk.Button(parent, text=text, width=width, command=command, style=style_name)

    def build_ui(self):
        entry_font = ('Segoe UI', 15) if THEME_AVAILABLE else ('Arial', 13)
        self.entry = tk.Entry(self.container, font=entry_font, justify='right', bd=0, relief='flat', highlightthickness=2, highlightbackground='#3b82f6', highlightcolor='#3b82f6')
        # limit input length (prevents typing/pasting excessively long examples)
        vcmd = self.root.register(self._on_validate)
        self.entry.configure(validate='key', validatecommand=(vcmd, '%P'))
        self.entry.grid(row=0, column=0, columnspan=4, padx=2, pady=(1, 6), sticky='we')

        keys = [
            ('7', '8', '9', '/'),
            ('4', '5', '6', '*'),
            ('1', '2', '3', '-'),
            ('0', '.', '=', '+'),
        ]

        # make columns uniform
        for i in range(4):
            self.container.columnconfigure(i, weight=1, minsize=48)

        for r, row in enumerate(keys, start=1):
            for c, key in enumerate(row):
                cmd = lambda ch=key: self.on_press(ch)
                kind = 'digit' if (key.isdigit() or key == '.') else 'op'
                btn = self.make_btn(self.container, key, cmd, width=5, kind=kind)
                btn.grid(row=r, column=c, padx=2, pady=2, ipadx=0, ipady=4, sticky='nsew')

        specials = ['C', '⌫', 'xʸ', '□']
        for i, key in enumerate(specials):
            cmd = [self.clear_all, self.backspace, self.power_window, self.figures_window][i]
            btn = self.make_btn(self.container, key, cmd, width=5, kind='special')
            btn.grid(row=5, column=i, padx=2, pady=2, ipadx=0, ipady=4, sticky='nsew')

        lbl = ttk.Label(self.container, text='Многофункциональный калькулятор\n(сделанный одним человеком)', anchor='center', justify='center', font=('Segoe UI', 8) if THEME_AVAILABLE else ('Arial', 8))
        lbl.grid(row=6, column=0, columnspan=4, pady=(4, 2))

        self.root.bind('<Return>', lambda e: self.on_press('='))
        self.root.bind('<BackSpace>', lambda e: self.backspace())
        self._center()

    def on_press(self, ch):
        if ch == '=':
            self.evaluate()
            return
        self.entry.insert(tk.END, ch)

    def evaluate(self):
        expr = self.entry.get()
        try:
            result = eval(expr)
            s = str(result)
            max_len = 20
            self.entry.delete(0, tk.END)
            if len(s) > max_len:
                self.entry.insert(0, 'Ответ слишком большой!')
                self._show_msg('Результат (полный)', s)
            else:
                self.entry.insert(0, s)
        except Exception:
            self._show_msg('Ошибка', 'Неверное выражение', is_error=True)

    def clear_all(self):
        self.entry.delete(0, tk.END)

    def backspace(self):
        cur = self.entry.get()
        if cur:
            self.entry.delete(len(cur)-1, tk.END)
    def power_window(self):
        win = tk.Toplevel(self.root)
        win.title('Степень xʸ')
        win.geometry('300x190')
        if not THEME_AVAILABLE:
            win.configure(bg='#222831')
        ttk.Label(win, text='Основание x:').pack(pady=6)
        e_x = ttk.Entry(win)
        e_x.pack(pady=4)
        ttk.Label(win, text='Показатель y:').pack(pady=6)
        e_y = ttk.Entry(win)
        e_y.pack(pady=4)

        def calc():
            try:
                x = float(e_x.get())
                y = float(e_y.get())
                res = x ** y
                self._show_msg('Результат', f'{x} ^ {y} = {res}')
            except Exception:
                self._show_msg('Ошибка', 'Проверьте значения', is_error=True)

        self.make_btn(win, 'Вычислить', calc, width=12, kind='special').pack(pady=8)

    def figures_window(self):
        win = tk.Toplevel(self.root)
        win.title('Фигуры')
        win.geometry('320x220')
        if not THEME_AVAILABLE:
            win.configure(bg='#222831')
        ttk.Label(win, text='Выберите фигуру:').pack(pady=8)
        self.make_btn(win, 'Прямоугольник', lambda: self.figure_input(win, 'Прямоугольник', ['Длина', 'Ширина'], lambda v: (float(v[0]) * float(v[1]), 2 * (float(v[0]) + float(v[1])))), width=18, kind='special').pack(pady=6)
        self.make_btn(win, 'Круг', lambda: self.figure_input(win, 'Круг', ['Радиус'], lambda v: (math.pi * float(v[0]) ** 2, 2 * math.pi * float(v[0]))), width=18, kind='special').pack(pady=6)
        self.make_btn(win, 'Треугольник', lambda: self.figure_triangle(win), width=18, kind='special').pack(pady=6)

    def figure_triangle(self, parent):
        win = tk.Toplevel(parent)
        win.title('Треугольник')
        win.geometry('320x200')
        if not THEME_AVAILABLE:
            win.configure(bg='#222831')
        ttk.Label(win, text='Площадь (основание и высота):').pack(pady=6)
        self.make_btn(win, 'Площадь', lambda: self.figure_input(win, 'Площадь треугольника', ['Основание', 'Высота'], lambda v: (0.5 * float(v[0]) * float(v[1]), None)), width=18, kind='special').pack(pady=4)
        self.make_btn(win, 'Периметр (три стороны)', lambda: self.figure_input(win, 'Периметр треугольника', ['Сторона1', 'Сторона2', 'Сторона3'], lambda v: (None, float(v[0]) + float(v[1]) + float(v[2]))), width=18, kind='special').pack(pady=4)

    def figure_input(self, parent, title, fields, calc):
        win = tk.Toplevel(parent)
        win.title(title)
        win.geometry('320x220')
        if not THEME_AVAILABLE:
            win.configure(bg='#222831')
        entries = []
        for f in fields:
            ttk.Label(win, text=f).pack(pady=3)
            e = ttk.Entry(win)
            e.pack(pady=2)
            entries.append(e)

        def compute():
            try:
                vals = [e.get() for e in entries]
                area, peri = calc(vals)
                parts = []
                if area is not None:
                    parts.append(f'Площадь: {area}')
                if peri is not None:
                    parts.append(f'Периметр: {peri}')
                    self._show_msg('Результат', '\n'.join(parts))
            except Exception:
                    self._show_msg('Ошибка', 'Проверьте ввод', is_error=True)

        self.make_btn(win, 'Вычислить', compute, width=12, kind='special').pack(pady=8)

def main():
    if THEME_AVAILABLE:
        root = tb.Window(title='Калькулятор', themename='darkly')
    else:
        root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()