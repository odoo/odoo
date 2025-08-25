"""Chinese (lunisolar) holiday generator: new moons + principal solar terms.

Algorithm summary
-----------------
- Months begin at the astronomical **new moon** (elongation = 0°).
- A month containing a **principal solar term** (Zhongqi, Sun longitude multiple of 30°)
  is a regular month; a month **without** a principal term is a **leap month** and
  repeats the previous month's number.
- The **month that contains the winter solstice** (Sun longitude 270°) is **month 11**.
  Month numbers increase from there; leap months keep the same month number.
- Major holidays are anchored by lunar month/day (e.g., CNY = 1st day of month 1),
  except **Qingming**, which is a solar-term holiday (~Sun longitude 15°, often Apr 4/5).

We compute:
- All **new moons** (TT JDs) covering [Nov (year-1) .. Mar (year+1)], enough to label months.
- All **principal terms** (Sun longitudes 0°, 30°, ..., 330°) across a slightly wider window.
- The **winter solstice** (Sun longitude 270°) near Dec 21 of (year-1) to locate month 11.
- Month numbers and leap-month flags for each lunation by checking if a principal term falls
  within the interval between successive new moons.

We return **civil dates** in the caller's local time (from `Location.tz`). Day 1 of each
lunar month is the civil date of the new moon at that location's time zone.
"""

import math
from datetime import datetime, timedelta, timezone

from .utils.astro import sun_ecliptic_longitude_deg
from .utils.phases import find_phase_time_tt_near
from .utils.time_utils import (
    from_julian_day,
    jd_tt_from_jd_ut,
    jd_ut_from_jd_tt,
    to_julian_day,
)

_SYNODIC_DAYS = 29.530588861  # mean lunation


# ----- helpers: JD/DT conversions -----
def _jd_to_local_date(jd_ut, tz_hours):
    """UT-based JD → local civil date (tz fixed offset hours)."""
    dt = from_julian_day(jd_ut).astimezone(timezone(timedelta(hours=tz_hours)))
    return dt.date()


def _greg_to_jd(d):
    """Gregorian date (UTC midnight) → JD."""
    return to_julian_day(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))


# ----- solve for Sun longitude = target_deg (tropical) -----
def _find_solar_longitude_tt_near(jd_tt_guess, target_deg):
    """Refine TT JD where Sun ecliptic longitude equals target_deg (deg).

    We use a secant-like iteration on the wrapped difference to handle 360° wrap.
    """
    def f(jd_tt):
        x = sun_ecliptic_longitude_deg(jd_tt) - target_deg
        # wrap to [-180, 180]
        x = (x + 180.0) % 360.0 - 180.0
        return x

    x0 = jd_tt_guess - 2.0
    x1 = jd_tt_guess + 2.0
    y0 = f(x0)
    y1 = f(x1)
    for _ in range(80):
        if abs(y1 - y0) < 1e-12:
            break
        x2 = x1 - y1 * (x1 - x0) / (y1 - y0)
        y2 = f(x2)
        x0, y0, x1, y1 = x1, y1, x2, y2
        if abs(y1) < 1e-8:
            break
    return x1


# ----- enumerate principal terms across a window -----
def _principal_terms_between(jd_tt_start, jd_tt_end):
    """Return list of (target_deg, tt) for principal terms (0°, 30°,...,330°) between TT JDs."""
    # Find the first target multiple of 30° ahead of start
    lon_start = sun_ecliptic_longitude_deg(jd_tt_start)
    first_mult = math.ceil(lon_start / 30.0) * 30
    first_mult %= 360

    out = []
    guess = jd_tt_start
    target = first_mult
    while True:
        root = _find_solar_longitude_tt_near(guess, target)
        if root > jd_tt_end + 1.0:
            break
        out.append((target, root))
        # step toward next principal term
        target = (target + 30) % 360
        # a month-ish later is a good starting guess
        guess = root + 25.0
    return out


# ----- enumerate new moons across an extended window -----
def _new_moons_covering(year, loc):
    """Return list of TT JDs for new moons covering Nov (year-1) .. Mar (year+1)."""
    start = datetime(year - 1, 11, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 3, 31, tzinfo=timezone.utc)
    jd_guess = jd_tt_from_jd_ut(to_julian_day(start))
    jd_end_tt = jd_tt_from_jd_ut(to_julian_day(end))

    out = []
    guess = jd_guess
    while True:
        root = find_phase_time_tt_near(guess, target_deg=0.0, loc=loc)
        if out and root <= out[-1] + 15.0 / 1440.0:  # de-dup within ~15 min
            guess += _SYNODIC_DAYS
            continue
        out.append(root)
        if root > jd_end_tt:
            break
        guess = root + _SYNODIC_DAYS
    return out


# ----- build lunation table with month numbers & leap flags -----
def _build_lunar_months(year, loc):
    """Compute month table with fields:
       - start_tt: TT JD of new moon
       - start_local: civil date (local tz) for Day 1
       - has_principal_term: bool
       - month_no: 1..12 (assigned later)
       - leap: bool (assigned later)

    Steps:
    - Find all new moons and principal terms across a wide window.
    - Mark intervals [nm[i], nm[i+1]) that contain a principal term.
    - Locate winter solstice (≈ Dec 21, target 270° Sun longitude) near Dec of (year-1)
      to identify month 11 (the interval containing it).
    - Number months forward/backward; mark intervals without principal term as leap.
    """
    # New moons
    nms = _new_moons_covering(year, loc)

    # Principal terms across padded window
    jd_tt_start = nms[0] - 35.0
    jd_tt_end = nms[-1] + 35.0
    pts = _principal_terms_between(jd_tt_start, jd_tt_end)
    pt_times = [tt for _, tt in pts]

    # Build month intervals
    months = []
    for i in range(len(nms) - 1):
        a = nms[i]
        b = nms[i + 1]
        # Any principal term strictly inside (a, b)?
        has_pt = any((a < t) and (t < b) for t in pt_times)
        start_local = _jd_to_local_date(jd_ut_from_jd_tt(a), loc.tz)
        months.append({
            "start_tt": a,
            "start_local": start_local,
            "has_pt": has_pt,
            "month_no": None,
            "leap": False,
        })

    # Locate winter solstice near Dec 21 of (year-1)
    dec21 = datetime(year - 1, 12, 21, tzinfo=timezone.utc)
    dec21_tt = jd_tt_from_jd_ut(to_julian_day(dec21))
    solstice_tt = _find_solar_longitude_tt_near(dec21_tt, 270.0)

    # Find interval containing solstice
    idx11 = None
    for i in range(len(nms) - 1):
        if nms[i] <= solstice_tt < nms[i + 1]:
            idx11 = i
            break
    if idx11 is None:
        # Fallback: choose interval whose start is closest before solstice
        idx11 = max(0, max([i for i in range(len(months)) if nms[i] <= solstice_tt], default=0))

    # Assign month 11 at idx11
    months[idx11]["month_no"] = 11
    months[idx11]["leap"] = False

    # Forward numbering
    for j in range(idx11 + 1, len(months)):
        prev = months[j - 1]
        if months[j]["has_pt"]:
            months[j]["month_no"] = 1 if prev["month_no"] == 12 else prev["month_no"] + 1
            months[j]["leap"] = False
        else:
            months[j]["month_no"] = prev["month_no"]  # leap month repeats number
            months[j]["leap"] = True

    # Backward numbering
    for j in range(idx11 - 1, -1, -1):
        nxt = months[j + 1]
        if months[j]["has_pt"]:
            months[j]["month_no"] = 12 if nxt["month_no"] == 1 else nxt["month_no"] - 1
            months[j]["leap"] = False
        else:
            months[j]["month_no"] = nxt["month_no"]  # leap month repeats number
            months[j]["leap"] = True

    return months


class ChineseHolidayGenerator:
    """Generate key Chinese lunisolar holidays for a Gregorian year.

    Holidays
    --------
    - Chinese New Year (Lunar 1/1)
    - Lantern Festival (Lunar 1/15)
    - Dragon Boat Festival (Lunar 5/5)
    - Mid-Autumn Festival (Lunar 8/15)
    - Double Ninth Festival (Lunar 9/9)
    - Qingming Festival (Solar term at Sun longitude 15°; local civil date)
    """

    def __init__(self, loc):
        self.loc = loc

    # ---- utility ----
    def _gregorian_of(self, year, lunar_month, lunar_day, prefer_non_leap=True):
        """Return civil date for (lunar_month, lunar_day) in Gregorian year.

        prefer_non_leap: if True, pick the non-leap month when both exist.
        """
        candidates = []
        months = _build_lunar_months(year, self.loc)
        for m in months:
            if m["month_no"] != lunar_month:
                continue
            if prefer_non_leap and m["leap"]:
                continue
            d = m["start_local"] + timedelta(days=lunar_day - 1)
            if d.year == year:
                candidates.append(d)
        # Fallback: allow leap if none found
        if not candidates:
            for m in months:
                if m["month_no"] == lunar_month:
                    d = m["start_local"] + timedelta(days=lunar_day - 1)
                    if d.year == year:
                        candidates.append(d)
        return min(candidates) if candidates else None

    def _qingming_date(self, year):
        """Compute Qingming as the civil date when Sun longitude crosses 15°."""
        # Use a guess around April 4 (UTC) to find TT root, then convert to local date
        guess = to_julian_day(datetime(year, 4, 4, tzinfo=timezone.utc))
        root_tt = _find_solar_longitude_tt_near(jd_tt_from_jd_ut(guess), 15.0)
        root_ut = jd_ut_from_jd_tt(root_tt)
        return _jd_to_local_date(root_ut, self.loc.tz)

    def compute_chinese_new_year(self, year):
        return self._gregorian_of(year, 1, 1)

    def compute_lantern_festival(self, year):
        return self._gregorian_of(year, 1, 15)

    def compute_dragon_boat(self, year):
        return self._gregorian_of(year, 5, 5)

    def compute_mid_autumn(self, year):
        return self._gregorian_of(year, 8, 15)

    def compute_double_ninth(self, year):
        return self._gregorian_of(year, 9, 9)

    def compute_qingming(self, year):
        return self._qingming_date(year)
