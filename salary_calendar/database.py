import sqlite3

def init_db(conn):
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS shifts (
        day TEXT PRIMARY KEY,
        activation TEXT,
        end TEXT,
        duration_min INTEGER,
        undertime_min INTEGER,
        overtime_min INTEGER,
        day_pay_cents INTEGER,
        overtime_pay_cents INTEGER,
        notes TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    conn.commit()

def load_shift(conn, day_iso):
    cur = conn.cursor()
    cur.execute("SELECT activation, end, duration_min, undertime_min, overtime_min, day_pay_cents, overtime_pay_cents, notes FROM shifts WHERE day=?", (day_iso,))
    return cur.fetchone()

def save_shift(conn, day_iso, activation, end, duration_min, undertime_min, overtime_min, day_pay_cents, overtime_pay_cents, notes):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shifts(day, activation, end, duration_min, undertime_min, overtime_min, day_pay_cents, overtime_pay_cents, notes)
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(day) DO UPDATE SET
          activation=excluded.activation, end=excluded.end, duration_min=excluded.duration_min,
          undertime_min=excluded.undertime_min, overtime_min=excluded.overtime_min,
          day_pay_cents=excluded.day_pay_cents, overtime_pay_cents=excluded.overtime_pay_cents, notes=excluded.notes
    """, (day_iso, activation, end, duration_min, undertime_min, overtime_min, day_pay_cents, overtime_pay_cents, notes))
    conn.commit()

def delete_shift(conn, day_iso):
    cur = conn.cursor()
    cur.execute("DELETE FROM shifts WHERE day=?", (day_iso,))
    conn.commit()

def find_pending_overtimes(conn, year=None, month=None):
    cur = conn.cursor()
    if year and month:
        cur.execute("""
            SELECT day, overtime_min FROM shifts
            WHERE overtime_min > 0
              AND (overtime_pay_cents IS NULL OR overtime_pay_cents = 0)
              AND strftime('%Y', day) = ? 
              AND strftime('%m', day) = ?
            ORDER BY day
        """, (str(year), f"{month:02d}"))
    else:
        cur.execute("""
            SELECT day, overtime_min FROM shifts
            WHERE overtime_min > 0 
              AND (overtime_pay_cents IS NULL OR overtime_pay_cents = 0)
            ORDER BY day
        """)
    return cur.fetchall()

def list_shifts_between(conn, start_iso, end_iso):
    cur = conn.cursor()
    cur.execute("SELECT * FROM shifts WHERE day BETWEEN ? AND ? ORDER BY day", (start_iso, end_iso))
    return cur.fetchall()