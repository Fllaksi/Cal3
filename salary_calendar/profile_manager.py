import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from decimal import Decimal
import sqlite3
from .database import init_db
from .utils import center_window

def parse_hhmm_to_min(s):
    if not s: return 0
    h, m = map(int, s.split(':'))
    return h * 60 + m

def format_min_to_hhmm(m):
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"

class ProfileManager:
    profiles_dir = r"\\mdc\Public\Калмыков Владимир Алексеевич\Calendar"
    pin_dir = os.path.join(profiles_dir, "Pin")
    pin_file = os.path.join(pin_dir, "pins.json")

    def __init__(self):
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
        if not os.path.exists(self.pin_dir):
            os.makedirs(self.pin_dir)
        self.pins = self.load_pins()

    def load_pins(self):
        if os.path.exists(self.pin_file):
            with open(self.pin_file, 'r') as f:
                return json.load(f)
        return {}

    def save_pins(self):
        with open(self.pin_file, 'w') as f:
            json.dump(self.pins, f)

    def get_profiles(self):
        return [f.replace('.db', '') for f in os.listdir(self.profiles_dir) if f.endswith('.db')]

    def create_profile_window(self, master):
        dlg = tk.Toplevel(master)
        dlg.title("Создать профиль")
        dlg.resizable(False, False)
        dlg.geometry("450x500")
        center_window(dlg, 450, 500)
        frame = ttk.Frame(dlg, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Фамилия и Имя:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=10)
        ent_name = ttk.Entry(frame, width=40, font=("Segoe UI", 12))
        ent_name.grid(row=0, column=1, pady=10)
        ttk.Label(frame, text="Зарплата:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", pady=10)
        ent_salary = ttk.Entry(frame, width=40, font=("Segoe UI", 12))
        ent_salary.grid(row=1, column=1, pady=10)
        ttk.Label(frame, text="Время обеда (HH:MM):", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="w", pady=10)
        ent_lunch = ttk.Entry(frame, width=40, font=("Segoe UI", 12))
        ent_lunch.grid(row=2, column=1, pady=10)
        ttk.Label(frame, text="Пин-Код:", font=("Segoe UI", 12)).grid(row=3, column=0, sticky="w", pady=10)
        ent_pin = ttk.Entry(frame, show="*", width=40, font=("Segoe UI", 12))
        ent_pin.grid(row=3, column=1, pady=10)
        ttk.Label(frame, text="Повторите Пин-Код:", font=("Segoe UI", 12)).grid(row=4, column=0, sticky="w", pady=10)
        ent_repeat = ttk.Entry(frame, show="*", width=40, font=("Segoe UI", 12))
        ent_repeat.grid(row=4, column=1, pady=10)
        def on_create():
            name = ent_name.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Введите имя")
                return
            if name in self.get_profiles():
                messagebox.showerror("Ошибка", "Профиль существует")
                return
            try:
                salary = Decimal(ent_salary.get().strip())
            except:
                messagebox.showerror("Ошибка", "Неверная зарплата")
                return
            lunch_str = ent_lunch.get().strip()
            try:
                lunch_min = parse_hhmm_to_min(lunch_str)
            except:
                messagebox.showerror("Ошибка", "Время обеда HH:MM")
                return
            pin = ent_pin.get()
            repeat = ent_repeat.get()
            if pin != repeat:
                messagebox.showerror("Ошибка", "Пины не совпадают")
                return
            if not pin.isdigit():
                messagebox.showerror("Ошибка", "Пин должен быть цифрами")
                return
            db_path = os.path.join(self.profiles_dir, f"{name}.db")
            conn = sqlite3.connect(db_path)
            init_db(conn)
            self.save_setting(conn, 'salary', str(salary))
            self.save_setting(conn, 'lunch_min', str(lunch_min))
            self.save_default_colors(conn)
            conn.close()
            self.pins[name] = pin
            self.save_pins()
            messagebox.showinfo("Успех", "Профиль создан")
            dlg.destroy()
        ttk.Button(frame, text="Создать", command=on_create).grid(row=5, column=0, columnspan=2, pady=20)
        dlg.grab_set()
        master.wait_window(dlg)

    def select_profile_window(self, master):
        profiles = self.get_profiles()
        if not profiles:
            messagebox.showinfo("Нет профилей", "Создайте профиль сначала")
            return None
        dlg = tk.Toplevel(master)
        dlg.title("Выбрать профиль")
        dlg.resizable(False, False)
        dlg.geometry("450x350")
        center_window(dlg, 450, 350)
        frame = ttk.Frame(dlg, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Выберите профиль:", font=("Segoe UI", 12)).pack(pady=10)
        cmb = ttk.Combobox(frame, values=profiles, state="readonly", width=40, font=("Segoe UI", 12))
        cmb.pack(pady=10)
        ttk.Label(frame, text="Пин-Код:", font=("Segoe UI", 12)).pack(pady=15)
        ent_pin = ttk.Entry(frame, show="*", width=30, font=("Segoe UI", 12))
        ent_pin.pack(pady=10)
        selected = None
        def on_select():
            nonlocal selected
            name = cmb.get()
            pin = ent_pin.get()
            if name in self.pins and self.pins[name] == pin:
                selected = name
                dlg.destroy()
            else:
                messagebox.showerror("Ошибка", "Неверный пин")
        ttk.Button(frame, text="Войти", command=on_select).pack(pady=20)
        dlg.grab_set()
        master.wait_window(dlg)
        return selected

    def save_setting(self, conn, key, value):
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

    def load_setting(self, conn, key, default=None):
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

    def default_colors(self):
        return {
            "other_month": "#f0f0f0",
            "weekday_ok": "#c6efce",
            "past_no_data": "#e8e8e8",
            "future_current_month": "#d0d0d0",
            "today": "#fff2a8",
            "weekend": "#ffd9b3",
            "undertime": "#ffcccc",
            "header_bg": "#f7f7f7",
            "gold": "#ffd700",
            "weekly_overtime": "#d4f7d4",
            "weekly_undertime": "#ffd8d8",
        }

    def save_default_colors(self, conn):
        colors = self.default_colors()
        for k, v in colors.items():
            self.save_setting(conn, f"color_{k}", v)

    def load_colors(self, conn):
        colors = self.default_colors()
        for k in colors:
            v = self.load_setting(conn, f"color_{k}")
            if v:
                colors[k] = v
        return colors