"""Time and timescale helpers (Julian days, TT/UT conversion, GMST).

This module centralizes conversions between civil time and astronomical
timescales used in the package:
- Julian Day (JD)
- Terrestrial Time (TT) and Universal Time (UT) conversion via ΔT
- Greenwich Mean Sidereal Time (GMST)
"""

import calendar
import math
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from .angles import norm_deg


def to_julian_day(dt: datetime) -> float:
    """Convert timezone-aware or naive datetime to Julian Day (UTC).

    Naive datetimes are assumed to be UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    y = dt.year
    m = dt.month
    D = dt.day + (dt.hour + (dt.minute + dt.second / 60.0) / 60.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + (A // 4)
    JD = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + D + B - 1524.5
    return JD


def from_julian_day(jd: float) -> datetime:
    """Convert Julian Day (UTC) to a timezone-aware UTC datetime."""
    Z = int(jd + 0.5)
    F = (jd + 0.5) - Z
    if Z < 2299161:
        A = Z
    else:
        alpha = int((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - int(alpha / 4)
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)
    day = B - D - int(30.6001 * E) + F
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    day_int = int(day)
    frac = day - day_int
    hours = int(frac * 24.0)
    minutes = int((frac * 24.0 - hours) * 60.0)
    seconds = round((((frac * 24.0 - hours) * 60.0) - minutes) * 60.0)
    if seconds == 60:
        seconds = 59
    return datetime(year, month, day_int, hours, minutes, seconds, tzinfo=timezone.utc)


def T_centuries(jd: float) -> float:
    """Julian centuries since J2000.0 (TT), per Meeus convention."""
    return (jd - 2451545.0) / 36525.0


@lru_cache(maxsize=1024)
def delta_t_seconds_approx(year: int, month: int = 1) -> float:
    """Approximate ΔT (TT−UT) in seconds for a given year and month.

    Polynomial approximations good to a few seconds for 1900–2050.
    """
    y = year + (month - 0.5) / 12.0
    if 2005 <= y <= 2050:
        t = y - 2000
        dt = 62.92 + 0.32217 * t + 0.005589 * t * t
        return dt
    if 1900 <= y < 2005:
        t = y - 1900
        dt = -2.79 + 1.494119 * t - 0.0598939 * t * t + 0.0061966 * t * t * t - 0.000197 * t * t * t * t
        return dt
    if y >= 2050:
        t = y - 2000
        dt = 62.92 + 0.32217 * t + 0.005589 * t * t
        return dt
    return 68.0


def jd_tt_from_jd_ut(jd_ut: float) -> float:
    """Convert UT-based JD to TT-based JD using ΔT approximation."""
    dt = from_julian_day(jd_ut)
    dt_s = delta_t_seconds_approx(dt.year, dt.month)
    return jd_ut + dt_s / 86400.0


def jd_ut_from_jd_tt(jd_tt: float) -> float:
    """Convert TT-based JD to UT-based JD using ΔT approximation."""
    dt = from_julian_day(jd_tt)
    dt_s = delta_t_seconds_approx(dt.year, dt.month)
    return jd_tt - dt_s / 86400.0


@lru_cache(maxsize=8192)
def gmst_deg_from_jd_ut(jd_ut: float) -> float:
    """Compute GMST (degrees) from UT-based JD using the IAU expression."""
    T = (jd_ut - 2451545.0) / 36525.0
    GMST = norm_deg(280.46061837 + 360.98564736629 * (jd_ut - 2451545.0) + 0.000387933 * T * T - T * T * T / 38710000.0)
    return GMST


def nth_weekday(year: int, month: int, n: int, weekday: int) -> date:
    """
        Return the n-th occurrence of a given weekday in a specific month/year.
        weekday: 0=Mon ... 6=Sun
    """
    first = date(year, month, 1)
    offset = (weekday - first.weekday() + 7) % 7
    first_occurrence = first + timedelta(days=offset)
    return first_occurrence + timedelta(weeks=n - 1)


def last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, month, calendar.monthrange(year, month)[1])
    offset = (last.weekday() - weekday + 7) % 7
    return last - timedelta(days=offset)


def first_weekday_on_or_after(d: date, weekday: int) -> date:
    """
    Return the first date on or after `d` that lands on `weekday`.
    weekday: Monday=0 ... Sunday=6
    """
    return d + timedelta(days=(weekday - d.weekday()) % 7)
