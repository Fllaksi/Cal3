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