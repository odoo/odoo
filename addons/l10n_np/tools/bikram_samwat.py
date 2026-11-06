# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
    Bikram Sambat calendar data and conversion concepts inspired by:
    https://github.com/aerawatcorp/bikram
    https://github.com/amitgaru/nepali-datetime
"""

import bisect
from datetime import date, datetime, timedelta

BS_YEAR_TO_MONTHS = {
    2000: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2001: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2002: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2003: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2004: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2005: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2006: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2007: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2008: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    2009: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2010: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2011: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2012: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2013: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2014: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2015: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2016: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2017: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2018: (31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2019: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2020: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2021: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2022: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2023: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2024: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2025: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2026: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2027: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2028: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2029: (31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30),
    2030: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2031: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2032: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2033: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2034: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2035: (30, 32, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    2036: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2037: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2038: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2039: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2040: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2041: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2042: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2043: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2044: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2045: (31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2046: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2047: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2048: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2049: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2050: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2051: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2052: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2053: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2054: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2055: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2056: (31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30),
    2057: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2058: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2059: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2060: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2061: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2062: (31, 31, 31, 32, 31, 31, 29, 30, 29, 30, 29, 31),
    2063: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2064: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2065: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2066: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31),
    2067: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2068: (31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2069: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2070: (31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30),
    2071: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2072: (31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30),
    2073: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31),
    2074: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2075: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2076: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2077: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2078: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2079: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2080: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2081: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2082: (30, 32, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2083: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2084: (31, 31, 32, 31, 31, 30, 30, 30, 29, 30, 30, 30),
    2085: (31, 32, 31, 32, 30, 31, 30, 30, 29, 30, 30, 30),
    2086: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
    2087: (31, 31, 32, 31, 31, 31, 30, 29, 30, 30, 30, 30),
    2088: (30, 31, 32, 32, 30, 31, 30, 30, 29, 30, 30, 30),
    2089: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
    2090: (30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
}

# pointers to an equivalent date in both AD and BS (present-year anchor)
AD_SCALE = date(2026, 4, 14)
BS_SCALE = (2083, 1, 1)
START_YEAR = min(BS_YEAR_TO_MONTHS)
END_YEAR = max(BS_YEAR_TO_MONTHS)

# _MONTH_OFFSET[year][m] = days elapsed in `year` before month m+1 (0-indexed)
_MONTH_OFFSET = {
    year: [sum(months[:i]) for i in range(12)]
    for year, months in BS_YEAR_TO_MONTHS.items()
}

# _YEAR_START[i] = day offset of Baisakh 1 of (START_YEAR + i) relative to the anchor
# (negative before BS_SCALE year, 0 at the anchor, positive after)
_YEAR_START = []
_offset = -sum(sum(BS_YEAR_TO_MONTHS[y]) for y in range(START_YEAR, BS_SCALE[0]))
for _year in range(START_YEAR, END_YEAR + 1):
    _YEAR_START.append(_offset)
    _offset += sum(BS_YEAR_TO_MONTHS[_year])
_END_OFFSET = _offset  # first day after the last supported year


def convert_ad_to_bs(date_in_ad):
    """
    Convert an Gregorian (AD) date to a Bikram Sambat (BS) date.
    """
    if isinstance(date_in_ad, datetime):
        date_in_ad = date_in_ad.date()
    if not isinstance(date_in_ad, date):
        raise TypeError(f"Expected a date, got {date_in_ad}")

    diff_days = (date_in_ad - AD_SCALE).days
    if diff_days < _YEAR_START[0]:
        first = AD_SCALE + timedelta(days=_YEAR_START[0])
        raise ValueError(f"{date_in_ad} is before the first supported date {first}")
    if diff_days >= _END_OFFSET:
        raise ValueError(f"{date_in_ad} is after the last supported BS year {END_YEAR}")

    idx = bisect.bisect_right(_YEAR_START, diff_days) - 1
    year = START_YEAR + idx
    day_in_year = diff_days - _YEAR_START[idx]
    month = bisect.bisect_right(_MONTH_OFFSET[year], day_in_year)
    day = day_in_year - _MONTH_OFFSET[year][month - 1] + 1
    bs_date = (year, month, day)
    return bs_date


def convert_ad_to_bs_with_formatting(date_in_ad, date_format):
    """
    Convert AD date once and return both tuple and formatted string.
    """
    bs_date = convert_ad_to_bs(date_in_ad)
    formatted = date_format
    formatted = formatted.replace('%Y', str(bs_date[0]))
    formatted = formatted.replace('%m', str(bs_date[1]).zfill(2))
    formatted = formatted.replace('%d', str(bs_date[2]).zfill(2))
    return bs_date, formatted


def convert_bs_to_ad(bs_year, bs_month, bs_day):
    """Convert a Bikram Sambat (BS) date to an AD (Gregorian) date."""
    if not (START_YEAR <= bs_year <= END_YEAR):
        raise ValueError(f"BS year {bs_year} is outside the supported range {START_YEAR}–{END_YEAR}")
    if not 1 <= bs_month <= 12:
        raise ValueError(f"BS month must be 1–12, got {bs_month}")
    days_in_month = BS_YEAR_TO_MONTHS[bs_year][bs_month - 1]
    if not 1 <= bs_day <= days_in_month:
        raise ValueError(f"BS day {bs_day} is out of range for {bs_year}/{bs_month}")

    idx = bs_year - START_YEAR
    day_in_year = _MONTH_OFFSET[bs_year][bs_month - 1] + (bs_day - 1)
    total_days = _YEAR_START[idx] + day_in_year
    ad_date = AD_SCALE + timedelta(days=total_days)
    return ad_date


def get_bs_month_ad_range(bs_year, bs_month):
    """Return the AD start and end dates for a given BS month."""
    days_in_month = BS_YEAR_TO_MONTHS[bs_year][bs_month - 1]
    return convert_bs_to_ad(bs_year, bs_month, 1), convert_bs_to_ad(bs_year, bs_month, days_in_month)
