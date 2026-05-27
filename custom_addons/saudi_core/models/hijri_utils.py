from umalqura.hijri_date import HijriDate
from datetime import date

def gregorian_to_hijri(g_date):
    if not isinstance(g_date, date):
        return ''
    hd = HijriDate(g_date.year, g_date.month, g_date.day, gr=True)
    return f"{hd.year}/{hd.month:02d}/{hd.day:02d}"

def hijri_to_gregorian(h_year, h_month, h_day):
    hd = HijriDate(h_year, h_month, h_day, gr=False)
    return hd.to_gregorian()
