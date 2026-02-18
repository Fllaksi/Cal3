#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from salary_calendar.utils import center_window
from salary_calendar.interface import CalendarApp
from salary_calendar.profile_manager import ProfileManager

def choose_profile(root, manager):
    profile = None
    dlg = tk.Toplevel(root)
    dlg.title("Календарь")
    dlg.resizable(False, False)
    dlg.geometry("400x200")  # Увеличенный размер
    center_window(dlg, 400, 200)
    ttk.Button(dlg, text="Создать профиль", command=lambda: manager.create_profile_window(dlg)).pack(padx=10, pady=10)
    ttk.Button(dlg, text="Выбрать существующий", command=lambda: select(dlg)).pack(padx=10, pady=10)
    def select(d):
        nonlocal profile
        profile = manager.select_profile_window(dlg)
        if profile:
            d.destroy()
    dlg.grab_set()
    root.wait_window(dlg)
    return profile

def main():
    manager = ProfileManager()
    while True:
        root = tk.Tk()
        root.withdraw()
        profile = choose_profile(root, manager)
        if not profile:
            break
        app = CalendarApp(root, profile, manager)
        root.deiconify()
        root.mainloop()

if __name__ == "__main__":
    main()