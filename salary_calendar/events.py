from .constants import cents_to_money
import calendar
from datetime import date

def add_overtime_pay(conn, day_iso: str, add_cents: int):
    if add_cents <= 0: return
    cur = conn.cursor()
    cur.execute("SELECT overtime_pay_cents, notes FROM shifts WHERE day=?", (day_iso,))
    row = cur.fetchone()
    if row:
        cur_val = row[0] or 0
        notes = row[1] or ""
        new_val = cur_val + add_cents
        notes = (notes + "\n" if notes else "") + f"Добавлена доп.оплата: {cents_to_money(add_cents)} руб"
        cur.execute("UPDATE shifts SET overtime_pay_cents=?, notes=? WHERE day=?", (new_val, notes, day_iso))
    else:
        notes = f"Добавлена доп.оплата: {cents_to_money(add_cents)} руб"
        cur.execute("INSERT INTO shifts(day, activation, end, duration_min, undertime_min, overtime_min, day_pay_cents, overtime_pay_cents, notes) VALUES(?,?,?,?,?,?,?,?,?)", (day_iso, None, None, None, 0, 0, 0, add_cents, notes))
    conn.commit()

def distribute_overtime_minutes(conn, year: int, month: int, half: int, source_day_iso: str, available_overtime_min: int):
    cur = conn.cursor()
    used_map = {}
    if available_overtime_min <= 0: return available_overtime_min, used_map
    if half == 1:
        start = date(year, month, 1)
        end = date(year, month, 15)
    else:
        last = calendar.monthrange(year, month)[1]
        start = date(year, month, 16)
        end = date(year, month, last)
    cur.execute("SELECT day, undertime_min FROM shifts WHERE day BETWEEN ? AND ? AND undertime_min>0 ORDER BY day ASC", (start.isoformat(), end.isoformat()))
    rows = cur.fetchall()
    for r in rows:
        day_iso, undertime = r[0], r[1] or 0
        if day_iso == source_day_iso: continue
        if available_overtime_min <= 0: break
        if undertime <= 0: continue
        take = min(undertime, available_overtime_min)
        new_undertime = undertime - take
        cur.execute("SELECT notes FROM shifts WHERE day=?", (day_iso,))
        nrow = cur.fetchone()
        notes_target = (nrow[0] or "")
        notes_target = (notes_target + "\n" if notes_target else "") + f"Закрыто переработкой {take} мин (источник {source_day_iso})"
        cur.execute("UPDATE shifts SET undertime_min=?, notes=? WHERE day=?", (new_undertime, notes_target, day_iso))
        conn.commit()
        used_map[day_iso] = take
        available_overtime_min -= take
    if used_map:
        total_used = sum(used_map.values())
        cur.execute("SELECT overtime_min, notes FROM shifts WHERE day=?", (source_day_iso,))
        row = cur.fetchone()
        if row:
            cur_overtime = row[0] or 0
            cur_notes = row[1] or ""
            new_overtime = max(0, cur_overtime - total_used)
            used_info = "; ".join([f"{d}:{m}min" for d,m in used_map.items()])
            cur_notes = (cur_notes + "\n" if cur_notes else "") + f"Использовано для закрытия: {used_info}"
            cur.execute("UPDATE shifts SET overtime_min=?, notes=? WHERE day=?", (new_overtime, cur_notes, source_day_iso))
            conn.commit()
    return available_overtime_min, used_map