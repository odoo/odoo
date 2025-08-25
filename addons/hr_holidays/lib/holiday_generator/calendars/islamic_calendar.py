"""Islamic (Hijri) holiday generator using a single crescent-visibility proxy.

Algorithm (one method only)
---------------------------
For each lunar conjunction spanning the target Gregorian year:
1) Convert conjunction (TT) → UT → local civil date D0.
2) Test crescent *at local sunset* for D0, D0+1, D0+2 using:
     - Moon age since conjunction ≥ MIN_AGE_HOURS (e.g., 17 h)
     - Elongation (Moon - Sun) ≥ MIN_ELONG_DEG (e.g., 9°)
   If the proxy passes, the month begins at that sunset; civil "Day 1" is next morning.
3) Tag the evening before "Day 1" with a Hijri month index 1..12 by counting
   mean synodic months since the Hijri epoch (civil) 622-07-19 Gregorian.

We return **civil dates** (midnight-to-midnight). Religious observance starts
the *previous* sunset.

References / building blocks
----------------------------
- Sun/Moon math & TT↔UT/GMST: your astro/time_utils helpers (Meeus-style).
- Sunset finder: altitude = -0.833° via bisection (refraction + solar radius).
- Visibility proxy: age + elongation; simple, fast, tunable (Yallop/Odeh-inspired,
  but not a full curve). You can extend later with altitude and moonset-after-sunset.
"""

import math
from datetime import date, datetime, timedelta, timezone

from .utils.phases import find_phase_time_tt_near, lunar_phase_angle_tt_deg
from .utils.rise_set import sunset_jd_utc
from .utils.time_utils import (
    from_julian_day,
    jd_tt_from_jd_ut,
    jd_ut_from_jd_tt,
    to_julian_day,
)

# Hijri epoch (civil): 1 Muharram AH 1 = 622-07-19 Gregorian
_ISLAMIC_EPOCH_JD = to_julian_day(datetime(622, 7, 19, tzinfo=timezone.utc))
# Mean synodic month
_SYNODIC_DAYS = 29.530588861


# ----- JD/date helpers -----
def _greg_to_jd(d):
    """Gregorian date (UTC midnight) → JD."""
    return to_julian_day(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))


def _jd_to_local_date(jd_ut, tz_hours):
    """UT-based JD → local civil date (ignoring DST; tz as fixed offset)."""
    dt = from_julian_day(jd_ut).astimezone(timezone(timedelta(hours=tz_hours)))
    return dt.date()


# ----- Conjunctions spanning the year -----
def _nearest_conjunctions_for_year(year, loc):
    """Return TT JDs of lunar conjunctions around the year.

    We scan from mid-Dec (year-1) to mid-Jan (year+1), refining each root of
    elongation = 0° via a secant-like method. Step guesses by one lunation.
    """
    start = datetime(year - 1, 12, 15, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 15, tzinfo=timezone.utc)
    jd_guess = jd_tt_from_jd_ut(to_julian_day(start))
    jd_end_tt = jd_tt_from_jd_ut(to_julian_day(end))

    out = []
    guess = jd_guess
    while True:
        root = find_phase_time_tt_near(guess, target_deg=0.0, loc=loc)
        if out and root <= out[-1] + 15.0 / 1440.0:  # ~15 min duplicate guard
            guess += _SYNODIC_DAYS
            continue
        out.append(root)
        if root > jd_end_tt:
            break
        guess = root + _SYNODIC_DAYS
    return out


# ----- Crescent visibility proxy -----
def _crescent_visible_on(date_local, loc, conj_tt, min_elong_deg, min_age_hours):
    """Return True if crescent is plausibly visible at local sunset on date_local."""
    jd_sunset_ut = sunset_jd_utc(datetime(date_local.year, date_local.month, date_local.day), loc)
    jd_sunset_tt = jd_tt_from_jd_ut(jd_sunset_ut)

    # Age (hours) since conjunction at sunset
    age_hours = (jd_sunset_tt - conj_tt) * 24.0
    if age_hours < 0.0:
        return False

    # Elongation at sunset (topocentric Moon longitude)
    elong_deg = lunar_phase_angle_tt_deg(jd_sunset_tt, True, loc)
    return (age_hours >= min_age_hours) and (elong_deg >= min_elong_deg)


def _month_start_from_conjunction(conj_tt, loc, min_elong_deg, min_age_hours):
    """Compute civil 'Day 1' for the Hijri month following a conjunction.

    Check sunset on D0, D0+1, D0+2; first passing evening → Day 1 = that date + 1.
    Fallback: D0+3 (rare numeric/latitude edge).
    """
    jd_conj_ut = jd_ut_from_jd_tt(conj_tt)
    d0 = _jd_to_local_date(jd_conj_ut, loc.tz)

    for offset in (0, 1, 2):
        test_day = d0 + timedelta(days=offset)
        if _crescent_visible_on(test_day, loc, conj_tt, min_elong_deg, min_age_hours):
            return test_day + timedelta(days=1)
    return d0 + timedelta(days=3)


def _label_hijri_month(jd_month_evening_ut):
    """Evening preceding Day 1 (UT JD) → Hijri month number in 1..12."""
    n = math.floor((jd_month_evening_ut - _ISLAMIC_EPOCH_JD) / _SYNODIC_DAYS) + 1
    return ((n - 1) % 12) + 1


def _astronomical_month_starts(year, loc, min_elong_deg, min_age_hours):
    """Return [(hijri_month, gregorian_day1), ...] sorted and deduped."""
    out = []
    for conj_tt in _nearest_conjunctions_for_year(year, loc):
        d1 = _month_start_from_conjunction(conj_tt, loc, min_elong_deg, min_age_hours)
        jd_eve_ut = _greg_to_jd(d1) - 0.5  # evening before Day 1
        mnum = _label_hijri_month(jd_eve_ut)
        out.append((mnum, d1))

    out.sort(key=lambda x: x[1])
    dedup, seen = [], set()
    for m, d1 in out:
        if d1 not in seen:
            dedup.append((m, d1))
            seen.add(d1)
    return dedup


class IslamicHolidayGenerator:
    """Generate Islamic holidays for a Gregorian year at a given Location.

    There is only one method: crescent visibility at local sunset with
    tunable thresholds. Pass thresholds via `loc.visibility_thresholds`
    or let the generator use (9°, 17h) by default.
    """

    def __init__(self, loc):
        self.loc = loc
        self.el, self.age = loc.thresholds_or_default()

    def _gregorian_of(self, year, hijri_month, hijri_day):
        """Gregorian civil date for (Hijri month, day) in this Gregorian year."""
        month_starts = _astronomical_month_starts(year, self.loc, self.el, self.age)
        for mnum, d1 in month_starts:
            if mnum == hijri_month:
                g = d1 + timedelta(days=hijri_day - 1)
                if g.year == year:
                    return g
        return None

    def compute_islamic_new_year(self, year: int) -> date:
        """1 Muharram — Islamic New Year."""
        return self._gregorian_of(year, 1, 1)

    def compute_ashura(self, year: int) -> date:
        """10 Muharram — Day of Ashura."""
        return self._gregorian_of(year, 1, 10)

    def compute_mawlid(self, year: int) -> date:
        """12 Rabi' al-awwal — Mawlid."""
        return self._gregorian_of(year, 3, 12)

    def compute_isra_miraj(self, year: int) -> date:
        """27 Rajab — Isra & Mi'raj."""
        return self._gregorian_of(year, 7, 27)

    def compute_ramadan_start(self, year: int) -> date:
        """1 Ramadan — Start of Ramadan (fast begins previous sunset)."""
        return self._gregorian_of(year, 9, 1)

    def compute_laylat_al_qadr(self, year: int) -> date:
        """27 Ramadan — Laylat al-Qadr (observed convention)."""
        return self._gregorian_of(year, 9, 27)

    def compute_eid_al_fitr(self, year: int) -> date:
        """1 Shawwal — Eid al-Fitr."""
        return self._gregorian_of(year, 10, 1)

    def compute_arafah(self, year: int) -> date:
        """9 Dhu al-Hijjah — Day of Arafah."""
        return self._gregorian_of(year, 12, 9)

    def compute_eid_al_adha(self, year: int) -> date:
        """10 Dhu al-Hijjah — Eid al-Adha."""
        return self._gregorian_of(year, 12, 10)
