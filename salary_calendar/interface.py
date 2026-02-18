#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from datetime import date, datetime, timedelta
from .utils import center_window
import calendar
from decimal import Decimal
import os
import sqlite3

from .constants import cents_to_money, format_minutes_hhmm
from . import database, calculations, events, widgets
from .profile_manager import ProfileManager, parse_hhmm_to_min, format_min_to_hhmm

def center_window(window, width=None, height=None):
    window.update_idletasks()
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

class CalendarApp:
    def __init__(self, master, profile_name, manager: ProfileManager):
        self.master = master
        self.master.title(f"Salary Calendar (Рабочий календарь) - {profile_name}")
        self.master.geometry("1150x740")
        center_window(self.master, 1150, 740)
        self.master.resizable(False, False)
        self.profile_name = profile_name
        self.manager = manager
        self.db_path = os.path.join(manager.profiles_dir, f"{profile_name}.db")
        self.conn = sqlite3.connect(self.db_path)
        if not self._db_exists():
            database.init_db(self.conn)
            self.manager.save_default_colors(self.conn)
        self.base_amount = Decimal(self.manager.load_setting(self.conn, 'salary', '90610.5'))
        self.lunch_min = int(self.manager.load_setting(self.conn, 'lunch_min', '60'))
        self.required_minutes = 480 + self.lunch_min
        self.colors = self.manager.load_colors(self.conn)
        self.holidays_set, self.holidays_names = self._load_manual_holidays(range(2024, 2028))
        self.today = date.today()
        self.cur_year = self.today.year
        self.cur_month = self.today.month
        self.tooltip = None
        self._build_ui()
        self._draw_calendar()
        self._start_timer()

    def _db_exists(self):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        return bool(tables)

    def _load_manual_holidays(self, years):
        hset = set()
        names = {}
        for y in years:
            for mday in range(1, 10):
                from datetime import date as _d
                hset.add(_d(y, 1, mday))
                names[_d(y, 1, mday)] = "Новогодние каникулы"
            from datetime import date as _d
            names[_d(y, 1, 7)] = "Рождество"
            hset.add(_d(y, 1, 7))
            names[_d(y, 2, 23)] = "День защитника Отечества"
            hset.add(_d(y, 2, 23))
            names[_d(y, 3, 8)] = "Международный женский день"
            hset.add(_d(y, 3, 8))
            names[_d(y, 5, 1)] = "Праздник труда"
            hset.add(_d(y, 5, 1))
            names[_d(y, 5, 9)] = "День Победы"
            hset.add(_d(y, 5, 9))
            names[_d(y, 6, 12)] = "День России"
            hset.add(_d(y, 6, 12))
            names[_d(y, 11, 4)] = "День единства"
            hset.add(_d(y, 11, 4))
            names[_d(y, 12, 31)] = "Новый год"
            hset.add(_d(y, 12, 31))
        return hset, names

    def _build_ui(self):
        top = ttk.Frame(self.master)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Button(top, text="◀", width=3, command=self._prev_month).pack(side="left")
        ttk.Button(top, text="▶", width=3, command=self._next_month).pack(side="left")

        self.lbl_month = ttk.Label(top, text="", font=("Segoe UI", 14, "bold"))
        self.lbl_month.pack(side="left", expand=True, padx=20)

        self.btn_settings = ttk.Button(top, text="⚙", width=3, command=self._on_settings)
        self.btn_settings.pack(side="right", padx=2)
        self.create_tooltip(self.btn_settings, "Настройки Вида")

        self.btn_profile = ttk.Button(top, text="👤", width=3, command=self._on_profile)
        self.btn_profile.pack(side="right", padx=2)
        self.create_tooltip(self.btn_profile, "Профиль")

        # Панель статуса
        status_container = ttk.Frame(self.master)
        status_container.pack(fill="x", pady=10)

        end_frame = ttk.LabelFrame(status_container, text=" Ожидаемый конец смены ", padding=10)
        end_frame.pack(side="left", expand=True, fill="x", padx=20)
        self.lbl_expected_end = ttk.Label(end_frame, text="—", font=("Segoe UI", 12))
        self.lbl_expected_end.pack()

        earn_frame = ttk.LabelFrame(status_container, text=" Заработок за сегодня ", padding=10)
        earn_frame.pack(side="left", expand=True, fill="x", padx=20)
        self.lbl_today_earn = ttk.Label(earn_frame, text="0.00 руб", font=("Segoe UI", 12))
        self.lbl_today_earn.pack()

        nav = ttk.Frame(self.master)
        nav.pack(fill="x", padx=8)
        ttk.Label(nav, text="Год:").pack(side="left")
        self.spin_year = tk.Spinbox(nav, from_=1970, to=2100, width=6, command=self._on_spin)
        self.spin_year.delete(0, "end")
        self.spin_year.insert(0, str(self.cur_year))
        self.spin_year.pack(side="left", padx=(6, 12))
        ttk.Label(nav, text="Месяц:").pack(side="left")
        self.cmb_month = ttk.Combobox(nav, values=[calendar.month_name[i] for i in range(1, 13)], state="readonly", width=18)
        self.cmb_month.current(self.cur_month - 1)
        self.cmb_month.bind("<<ComboboxSelected>>", self._on_combo)
        self.cmb_month.pack(side="left", padx=6)

        self.cal_frame = ttk.Frame(self.master)
        self.cal_frame.pack(padx=8, pady=6, fill="both", expand=True)
        self.day_buttons = {}
        self._create_calendar_grid()

        self.info_frame = ttk.Frame(self.master)
        self.info_frame.pack(fill="x", padx=8, pady=6)
        self.lbl_salary_first = ttk.Label(self.info_frame, text="")
        self.lbl_salary_first.pack(side="left", padx=10)
        self.lbl_salary_second = ttk.Label(self.info_frame, text="")
        self.lbl_salary_second.pack(side="left", padx=10)
        self.lbl_total_salary = ttk.Label(self.info_frame, text="")
        self.lbl_total_salary.pack(side="left", padx=10)
        self.lbl_pending_overtime = ttk.Label(self.info_frame, text="")
        self.lbl_pending_overtime.pack(side="left", padx=10)

        # Блок кнопок — всегда в самом низу окна
        buttons_frame = tk.Frame(self.master)  # ← tk вместо ttk
        buttons_frame.pack(side="bottom", fill="x", pady=10, padx=20)
        buttons_frame.config(bg="red")  # Теперь bg работает
        ttk.Button(buttons_frame, text="Начать смену", command=self._start_shift_today).pack(side="left", padx=15)
        ttk.Button(buttons_frame, text="Закончить смену", command=self._end_shift_today).pack(side="left", padx=15)
        ttk.Button(buttons_frame, text="Обработать переработки", command=self._distribute_overtime).pack(side="left",
                                                                                                         padx=15)

    def create_tooltip(self, widget, text):
        def enter(event):
            x = widget.winfo_rootx() + 25
            y = widget.winfo_rooty() + 25
            self.tw = tk.Toplevel(widget)
            self.tw.wm_overrideredirect(True)
            self.tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tw, text=text, background="yellow", relief="solid", borderwidth=1)
            label.pack()
        def leave(event):
            if hasattr(self, 'tw'):
                self.tw.destroy()
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _on_profile(self):
        popup = tk.Menu(self.master, tearoff=0)
        popup.add_command(label="Сменить профиль", command=self._change_profile)
        popup.add_command(label="Изменить данные Профиля", command=self._edit_profile)
        popup.add_command(label="Выйти из профиля", command=self._logout)
        x = self.btn_profile.winfo_rootx()
        y = self.btn_profile.winfo_rooty() + self.btn_profile.winfo_height()
        popup.tk_popup(x, y, 0)

    def _change_profile(self):
        self.master.destroy()

    def _edit_profile(self):
        dlg = tk.Toplevel(self.master)
        dlg.title("Изменить данные профиля")
        dlg.resizable(False, False)
        dlg.geometry("450x500")
        center_window(dlg, 450, 500)
        frame = ttk.Frame(dlg, padding=20)
        frame.pack(fill="both", expand=True)
        current_salary = self.base_amount
        current_lunch = self.lunch_min
        current_name = self.profile_name
        ttk.Label(frame, text="Фамилия и Имя:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=10)
        ent_name = ttk.Entry(frame, width=40, font=("Segoe UI", 12))
        ent_name.insert(0, current_name)
        ent_name.grid(row=0, column=1, pady=10)
        ttk.Label(frame, text="Зарплата:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", pady=10)
        ent_salary = ttk.Entry(frame, width=40, font=("Segoe UI", 12))
        ent_salary.insert(0, str(current_salary))
        ent_salary.grid(row=1, column=1, pady=10)
        ttk.Label(frame, text="Время обеда (HH:MM):", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="w", pady=10)
        ent_lunch = ttk.Entry(frame, width=40, font=("Segoe UI", 12))
        ent_lunch.insert(0, format_min_to_hhmm(current_lunch))
        ent_lunch.grid(row=2, column=1, pady=10)
        ttk.Label(frame, text="Новый Пин-Код (пусто — не менять):", font=("Segoe UI", 12)).grid(row=3, column=0, sticky="w", pady=10)
        ent_pin = ttk.Entry(frame, show="*", width=40, font=("Segoe UI", 12))
        ent_pin.grid(row=3, column=1, pady=10)
        ttk.Label(frame, text="Повторите Пин-Код:", font=("Segoe UI", 12)).grid(row=4, column=0, sticky="w", pady=10)
        ent_repeat = ttk.Entry(frame, show="*", width=40, font=("Segoe UI", 12))
        ent_repeat.grid(row=4, column=1, pady=10)
        def on_save():
            new_name = ent_name.get().strip()
            profiles = self.manager.get_profiles()
            if new_name != current_name and new_name in profiles:
                messagebox.showerror("Ошибка", "Имя существует")
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
            if pin and pin != repeat:
                messagebox.showerror("Ошибка", "Пины не совпадают")
                return
            if pin and not pin.isdigit():
                messagebox.showerror("Ошибка", "Пин цифры")
                return
            self.manager.save_setting(self.conn, 'salary', str(salary))
            self.manager.save_setting(self.conn, 'lunch_min', str(lunch_min))
            self.base_amount = salary
            self.lunch_min = lunch_min
            self.required_minutes = 480 + lunch_min
            if pin:
                self.manager.pins[new_name] = pin
            if new_name != current_name:
                old_db = self.db_path
                new_db = os.path.join(self.manager.profiles_dir, f"{new_name}.db")
                self.conn.close()
                os.rename(old_db, new_db)
                self.db_path = new_db
                self.conn = sqlite3.connect(new_db)
                if current_name in self.manager.pins:
                    self.manager.pins[new_name] = self.manager.pins.pop(current_name)
                self.profile_name = new_name
                self.master.title(f"Salary Calendar (Рабочий календарь) - {new_name}")
            self.manager.save_pins()
            messagebox.showinfo("Успех", "Данные обновлены")
            dlg.destroy()
            self._draw_calendar()
        ttk.Button(frame, text="Сохранить", command=on_save).grid(row=5, column=0, columnspan=2, pady=20)
        dlg.grab_set()
        self.master.wait_window(dlg)

    def _on_settings(self):
        dlg = tk.Toplevel(self.master)
        dlg.title("Настройки Вида")
        dlg.resizable(False, False)
        dlg.geometry("500x600")
        center_window(dlg, 500, 600)
        colors = self.colors.copy()
        entries = {}
        rus_names = {
            "other_month": "Дни другого месяца",
            "weekday_ok": "Обычный рабочий день",
            "past_no_data": "Прошлый день без записи",
            "future_current_month": "Будущие дни текущего месяца",
            "today": "Сегодняшний день",
            "weekend": "Выходной или праздник",
            "undertime": "День с недоработкой",
            "header_bg": "Фон заголовков и недели",
            "gold": "Дни с переработкой, учтённой в зарплате",
            "weekly_overtime": "Неделя с переработкой",
            "weekly_undertime": "Неделя с недоработкой",
        }
        row = 0
        for k in sorted(colors):
            rus_text = rus_names.get(k, k)
            ttk.Label(dlg, text=rus_text).grid(row=row, column=0, sticky="w", padx=5, pady=5)
            ent = ttk.Entry(dlg)
            ent.insert(0, colors[k])
            ent.grid(row=row, column=1, padx=5, pady=5)
            entries[k] = ent
            def choose(k=k, ent=ent):
                color = colorchooser.askcolor(color=colors[k])[1]
                if color:
                    ent.delete(0, tk.END)
                    ent.insert(0, color)
            ttk.Button(dlg, text="Выбрать", command=choose).grid(row=row, column=2, padx=5, pady=5)
            row += 1
        def on_save():
            for k, ent in entries.items():
                color = ent.get().strip()
                if color and len(color) == 7 and color.startswith('#'):
                    self.manager.save_setting(self.conn, f"color_{k}", color)
            self.colors = self.manager.load_colors(self.conn)
            self._draw_calendar()
            dlg.destroy()
        ttk.Button(dlg, text="Сохранить", command=on_save).grid(row=row, column=0, columnspan=3, pady=10)
        dlg.grab_set()
        self.master.wait_window(dlg)

    def _logout(self):
        self.master.destroy()

    def _prev_month(self):
        if self.cur_month == 1:
            self.cur_month = 12
            self.cur_year -= 1
        else:
            self.cur_month -= 1
        self._draw_calendar()

    def _next_month(self):
        if self.cur_month == 12:
            self.cur_month = 1
            self.cur_year += 1
        else:
            self.cur_month += 1
        self._draw_calendar()

    def _on_spin(self):
        try:
            self.cur_year = int(self.spin_year.get())
            self._draw_calendar()
        except:
            pass

    def _on_combo(self, event):
        self.cur_month = self.cmb_month.current() + 1
        self._draw_calendar()

    def _create_calendar_grid(self):
        headers = ["Неделя", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for c, txt in enumerate(headers):
            lbl = tk.Label(self.cal_frame, text=txt, bg=self.colors["header_bg"], relief="ridge", anchor="center")
            lbl.grid(row=0, column=c, sticky="nsew")
        for r in range(1, 7):
            for c in range(8):
                if c == 0:
                    lbl = tk.Label(self.cal_frame, text="", bg=self.colors["header_bg"], relief="ridge", anchor="center")
                    lbl.grid(row=r, column=c, sticky="nsew")
                else:
                    btn = tk.Button(self.cal_frame, text="", width=10, height=5, relief="flat", command=lambda row=r, col=c: self._on_day_click(self.day_buttons[(row, col)]["date"]))
                    btn.grid(row=r, column=c, sticky="nsew")
                    self.day_buttons[(r, c)] = {"btn": btn, "date": None}
                    btn.bind("<Enter>", lambda e, rc=(r, c): self._show_tooltip(e, rc))
                    btn.bind("<Leave>", lambda e: self._hide_tooltip())
        for i in range(8):
            self.cal_frame.grid_columnconfigure(i, weight=1)
        for i in range(7):
            self.cal_frame.grid_rowconfigure(i, weight=1)

    def _draw_calendar(self):
        self.lbl_month.config(text=f"{calendar.month_name[self.cur_month]} {self.cur_year}")
        self.spin_year.delete(0, "end")
        self.spin_year.insert(0, str(self.cur_year))
        self.cmb_month.current(self.cur_month - 1)
        cal = calendar.Calendar()
        weeks = cal.monthdatescalendar(self.cur_year, self.cur_month)
        for r in range(1, 7):
            weekly_total_min = 0
            for c in range(1, 8):
                if r-1 >= len(weeks):
                    self.day_buttons[(r,c)]["btn"].config(text="", state="disabled")
                    continue
                d = weeks[r-1][c-1]
                self.day_buttons[(r,c)]["date"] = d
                color = self._color_for_day(d)
                self.day_buttons[(r,c)]["btn"].config(text=str(d.day), state="normal", bg=color)
                shift = database.load_shift(self.conn, d.isoformat())
                if shift:
                    weekly_total_min += shift[2] or 0
            week_lbl = self.cal_frame.grid_slaves(row=r, column=0)[0]
            week_color = self.colors["weekly_overtime"] if weekly_total_min > 5 * self.required_minutes else self.colors["weekly_undertime"] if weekly_total_min < 5 * self.required_minutes else self.colors["header_bg"]
            week_lbl.config(background=week_color, text=f"Нед {r}: {format_minutes_hhmm(weekly_total_min)}")
        self._update_info_labels()

    def _color_for_day(self, d):
        if d.month != self.cur_month: return self.colors["other_month"]
        if d == self.today: return self.colors["today"]
        shift = database.load_shift(self.conn, d.isoformat())
        is_weekend = d.weekday() >= 5 or d in self.holidays_set
        if shift:
            if shift[3] > 0: return self.colors["undertime"]
            return self.colors["weekend"] if is_weekend else self.colors["weekday_ok"]
        if d < self.today: return self.colors["past_no_data"]
        return self.colors["weekend"] if is_weekend else self.colors["weekday_ok"]

    def _show_tooltip(self, event, rc):
        d = self.day_buttons[rc]["date"]
        if not d: return
        shift = database.load_shift(self.conn, d.isoformat())
        lines = self._tooltip_lines_for_day(d, shift)
        if not lines: return
        self.tooltip = widgets.Tooltip(self.master, lines, lambda: self._on_day_click(d))
        x, y = event.x_root + 10, event.y_root + 10
        self.tooltip.show_at(x, y)

    def _hide_tooltip(self):
        if self.tooltip: self.tooltip.close()
        self.tooltip = None

    def _tooltip_lines_for_day(self, d, shift):
        lines = [d.strftime("%d %B %Y")]
        if d in self.holidays_names: lines.append(self.holidays_names[d])
        if shift:
            act = shift[0] or "Нет"
            end = shift[1] or "Нет"
            duration = format_minutes_hhmm(shift[2] or 0)
            undertime = format_minutes_hhmm(shift[3] or 0)
            overtime = format_minutes_hhmm(shift[4] or 0)
            day_pay = cents_to_money(shift[5] or 0)
            ot_pay = cents_to_money(shift[6] or 0)
            notes = shift[7] or "Нет заметок"
            lines += [
                f"Активация: {act}",
                f"Окончание: {end}",
                f"Длительность: {duration}",
                f"Недоработка: {undertime}",
                f"Переработка: {overtime}",
                f"Оплата дня: {day_pay} руб",
                f"Оплата ОТ: {ot_pay} руб",
                f"Заметки: {notes[:50]}..." if len(notes) > 50 else notes
            ]
        return lines

    def _on_day_click(self, d):
        if self.tooltip: self.tooltip.close()
        existing = database.load_shift(self.conn, d.isoformat()) or (None, None, None, None, None, None, None, None)
        existing_dict = {"activation": existing[0], "end": existing[1], "notes": existing[7]}
        dlg = widgets.EditShiftDialog(self.master, d, existing_dict, self.conn, self.lunch_min)
        self.master.wait_window(dlg)
        if not dlg.result: return
        if dlg.result.get("deleted"):
            self._draw_calendar()
            return
        activation = dlg.result["activation"]
        end = dlg.result["end"]
        notes = dlg.result["notes"]
        duration_min = self._calculate_duration(activation, end)
        hourly = calculations.hourly_rate_for_month(d.year, d.month, self.holidays_set, self.base_amount)
        is_weekend = d.weekday() >= 5 or d in self.holidays_set
        if not is_weekend:
            undertime_min = max(0, self.required_minutes - duration_min)
            overtime_min = max(0, duration_min - self.required_minutes)
            day_pay_cents = calculations.day_base_pay(hourly)
            overtime_pay_cents = calculations.calc_overtime_pay_minutes(overtime_min, hourly)
        else:
            undertime_min = 0
            overtime_min = 0
            day_pay_cents = calculations.weekend_pay_for_duration(duration_min, hourly, self.lunch_min)
            overtime_pay_cents = 0
        database.save_shift(self.conn, d.isoformat(), activation, end, duration_min, undertime_min, overtime_min, day_pay_cents, overtime_pay_cents, notes)
        self._draw_calendar()

    def _calculate_duration(self, act, end):
        if not act or not end: return 0
        try:
            act_dt = datetime.strptime(act, "%H:%M")
            end_dt = datetime.strptime(end, "%H:%M")
            if end_dt < act_dt: end_dt += timedelta(days=1)
            return int((end_dt - act_dt).total_seconds() / 60)
        except:
            return 0

    def _update_info_labels(self):
        first_start = date(self.cur_year, self.cur_month, 1).isoformat()
        first_end = date(self.cur_year, self.cur_month, 15).isoformat()
        second_start = date(self.cur_year, self.cur_month, 16).isoformat()
        last_day = calendar.monthrange(self.cur_year, self.cur_month)[1]
        second_end = date(self.cur_year, self.cur_month, last_day).isoformat()
        first_shifts = database.list_shifts_between(self.conn, first_start, first_end)
        second_shifts = database.list_shifts_between(self.conn, second_start, second_end)
        salary_first = sum(cents_to_money(s[5] + s[6]) for s in first_shifts if s[5] or s[6])
        salary_second = sum(cents_to_money(s[5] + s[6]) for s in second_shifts if s[5] or s[6])
        total = salary_first + salary_second
        pending = database.find_pending_overtimes(self.conn, self.cur_year, self.cur_month)
        pending_ot = sum(row[1] or 0 for row in pending)
        self.lbl_salary_first.config(text=f"1-15: {salary_first:.2f} руб")
        self.lbl_salary_second.config(text=f"16-{last_day}: {salary_second:.2f} руб")
        self.lbl_total_salary.config(text=f"Итого: {total:.2f} руб")
        self.lbl_pending_overtime.config(text=f"Нераспределенная переработка: {format_minutes_hhmm(pending_ot)}")

    def _start_timer(self):
        self.master.after(60000, self._start_timer)
        self._draw_calendar()

    def _start_shift_today(self):
        messagebox.showinfo("Информация", "Функция 'Начать смену' пока в разработке")

    def _end_shift_today(self):
        messagebox.showinfo("Информация", "Функция 'Закончить смену' пока в разработке")

    def _distribute_overtime(self):
        messagebox.showinfo("Информация", "Функция 'Обработать переработки' пока в разработке")

if __name__ == "__main__":
    pass