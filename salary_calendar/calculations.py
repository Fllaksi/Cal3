import calendar
from decimal import Decimal
from .constants import DEC, money_to_cents

def working_days_in_month(year: int, month: int, holidays_set: set) -> int:
    cal = calendar.Calendar(firstweekday=0)
    cnt = 0
    for week in cal.monthdatescalendar(year, month):
        for d in week:
            if d.month != month: continue
            if d.weekday() >= 5: continue
            if d in holidays_set: continue
            cnt += 1
    return cnt

def hourly_rate_for_month(year: int, month: int, holidays_set: set, base_amount: Decimal) -> Decimal:
    wd = working_days_in_month(year, month, holidays_set)
    if wd <= 0: return DEC('0.00')
    return (base_amount / DEC(wd) / DEC(8)).quantize(DEC('0.01'))

def day_base_pay(hourly_rate: Decimal) -> int:
    return money_to_cents((hourly_rate * DEC(8)).quantize(DEC('0.01')))

def calc_overtime_pay_minutes(overtime_min: int, hourly_rate: Decimal, is_weekend=False) -> int:
    if overtime_min <= 0: return 0
    if is_weekend:
        pay = hourly_rate * DEC('2.0') * (DEC(overtime_min) / DEC(60))
        return money_to_cents(pay.quantize(DEC('0.01')))
    first = min(overtime_min, 120)
    rest = max(0, overtime_min - 120)
    pay_first = hourly_rate * DEC('1.5') * (DEC(first) / DEC(60))
    pay_rest = hourly_rate * DEC('2.0') * (DEC(rest) / DEC(60))
    return money_to_cents((pay_first + pay_rest).quantize(DEC('0.01')))

def weekend_pay_for_duration(duration_min: int, hourly_rate: Decimal, lunch_min: int) -> int:
    work_minutes = duration_min or 0
    if work_minutes > 240:
        work_minutes -= lunch_min
    return calc_overtime_pay_minutes(work_minutes, hourly_rate, is_weekend=True)