"""Lunar phase, tithi, and phase-root finding utilities."""

import math
from datetime import datetime
from ..location import Location
from .time_utils import jd_tt_from_jd_ut
from .astro import topocentric_moon_longitude, moon_ecliptic_longitude_and_distance, sun_ecliptic_longitude_deg
from .rise_set import sunrise_jd_utc, sunset_jd_utc
from .angles import norm_deg


def lunar_phase_angle_tt_deg(jd_tt: float, use_topo: bool, loc: Location) -> float:
    """Elongation λ_moon − λ_sun (deg) at TT JD.

    If use_topo is True, uses a simplified topocentric lunar longitude.
    """
    if use_topo:
        lam_m = topocentric_moon_longitude(jd_tt, loc.lat, loc.lon, loc.height_m)
    else:
        lam_m, _ = moon_ecliptic_longitude_and_distance(jd_tt)
    lam_s = sun_ecliptic_longitude_deg(jd_tt)
    return norm_deg(lam_m - lam_s)


def tithi_at_local_sunrise(date_local: datetime, loc: Location) -> int:
    """Tithi number (1–30) prevailing at local sunrise."""
    jd_sunrise_ut = sunrise_jd_utc(date_local, loc)
    jd_tt = jd_tt_from_jd_ut(jd_sunrise_ut)
    ang = lunar_phase_angle_tt_deg(jd_tt, False, loc)
    return int(ang // 12.0) + 1


def tithi_at_local_sunset(date_local: datetime, loc: Location) -> int:
    """Tithi number (1–30) prevailing at local sunset."""
    jd_sunset_ut = sunset_jd_utc(date_local, loc)
    jd_tt = jd_tt_from_jd_ut(jd_sunset_ut)
    ang = lunar_phase_angle_tt_deg(jd_tt, False, loc)
    return int(ang // 12.0) + 1


def find_phase_time_tt_near(jd_tt_guess: float, target_deg: float, loc: Location) -> float:
    """Refine to a TT time where elongation equals target_deg (secant method)."""
    x0 = jd_tt_guess - 1.0
    x1 = jd_tt_guess + 1.0
    def f(jd_tt):
        d = lunar_phase_angle_tt_deg(jd_tt, True, loc) - target_deg
        if d > 180.0:
            d -= 360.0
        if d < -180.0:
            d += 360.0
        return d
    y0 = f(x0)
    y1 = f(x1)
    for _ in range(60):
        if abs(y1 - y0) < 1e-12:
            break
        x2 = x1 - y1 * (x1 - x0) / (y1 - y0)
        y2 = f(x2)
        x0, y0, x1, y1 = x1, y1, x2, y2
        if abs(y1) < 1e-8:
            break
    return x1
