"""Sunrise/sunset calculations using bisection with refraction correction.

We solve for when the true solar altitude equals -0.833° (standard refraction
and solar radius), scanning the local day to bracket the event then refining by
bisection. This is robust for all latitudes with normal Sun paths.
"""

from datetime import datetime, timezone, timedelta
import math
from ..location import Location
from .time_utils import jd_tt_from_jd_ut, gmst_deg_from_jd_ut, to_julian_day
from .astro import sun_ra_dec_tt
from .angles import norm_deg


def sun_altitude_deg_at_ut(jd_ut: float, lat_deg: float, lon_deg: float) -> float:
    """Solar altitude (deg) at a UT-based JD and geographic location."""
    jd_tt = jd_tt_from_jd_ut(jd_ut)
    ra, dec = sun_ra_dec_tt(jd_tt)
    GMST = gmst_deg_from_jd_ut(jd_ut)
    LST = math.radians(norm_deg(GMST + lon_deg))
    H = LST - ra
    lat = math.radians(lat_deg)
    alt = math.degrees(math.asin(math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(H)))
    return alt


def _find_sun_event_jd_utc(date_local: datetime, loc: Location, target_alt: float, is_rise: bool, step_minutes: int = 10) -> float:
    """Find sunrise/sunset UTC JD by scanning and bisection on altitude.

    - date_local: local civil date at location (time ignored)
    - target_alt: altitude in degrees (-0.833 for standard sunrise/sunset)
    - is_rise: True for sunrise, False for sunset
    - step_minutes: scan granularity to find a sign change bracket
    """
    tz = timezone(timedelta(hours=loc.tz))
    local_mid = datetime(date_local.year, date_local.month, date_local.day, 0, 0, 0, tzinfo=tz)
    utc_start = local_mid.astimezone(timezone.utc)
    jd_start = to_julian_day(utc_start)

    def f(jd):
        return sun_altitude_deg_at_ut(jd, loc.lat, loc.lon) - target_alt

    total_minutes = 24 * 60
    step_days = step_minutes / 1440.0
    samples = []
    jd = jd_start
    for _ in range(0, total_minutes // step_minutes + 1):
        samples.append((jd, f(jd)))
        jd += step_days

    bracket = None
    for (a_jd, a_f), (b_jd, b_f) in zip(samples, samples[1:]):
        if a_f == 0.0:
            return a_jd
        if b_f == 0.0:
            return b_jd
        crossed = (a_f <= 0.0 and b_f >= 0.0) if is_rise else (a_f >= 0.0 and b_f <= 0.0)
        if crossed:
            bracket = (a_jd, a_f, b_jd, b_f)
            break

    if bracket is None:
        for day_offset in (-1, 1):
            jd0 = jd_start + day_offset
            a_f = f(jd0)
            b_f = f(jd0 + step_days)
            if is_rise and a_f <= 0.0 and b_f >= 0.0:
                bracket = (jd0, a_f, jd0 + step_days, b_f)
                break
            if (not is_rise) and a_f >= 0.0 and b_f <= 0.0:
                bracket = (jd0, a_f, jd0 + step_days, b_f)
                break
    if bracket is None:
        return jd_start + 0.5

    a, fa, b, fb = bracket
    for _ in range(60):
        m = 0.5 * (a + b)
        fm = f(m)
        if abs(fm) < 1e-7 or (b - a) < 1e-8:
            return m
        if is_rise:
            if fa <= 0.0 and fm <= 0.0:
                a, fa = m, fm
            else:
                b, fb = m, fm
        else:
            if fa >= 0.0 and fm >= 0.0:
                a, fa = m, fm
            else:
                b, fb = m, fm
    return 0.5 * (a + b)


def sunrise_jd_utc(date_local: datetime, loc: Location) -> float:
    return _find_sun_event_jd_utc(date_local, loc, target_alt=-0.833, is_rise=True)


def sunset_jd_utc(date_local: datetime, loc: Location) -> float:
    return _find_sun_event_jd_utc(date_local, loc, target_alt=-0.833, is_rise=False)
