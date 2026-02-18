from decimal import Decimal, ROUND_HALF_UP

DEC = Decimal

def money_to_cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def cents_to_money(cents: int) -> Decimal:
    return (DEC(cents) / 100).quantize(DEC('0.01'), rounding=ROUND_HALF_UP)

def format_minutes_hhmm(minutes: int) -> str:
    sign = ""
    if minutes < 0:
        sign = "-"; minutes = -minutes
    h = minutes // 60
    m = minutes % 60
    return f"{sign}{h}:{m:02d}"