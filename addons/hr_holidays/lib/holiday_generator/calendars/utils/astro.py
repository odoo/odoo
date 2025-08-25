"""Astronomical models (Sun/Moon) used by the calendar.

Implements compact versions of Meeus-style formulas for:
- Mean obliquity
- Solar ecliptic longitude (apparent)
- Lunar ecliptic longitude and distance (reduced series)
- Topocentric lunar longitude via simplified parallax correction
"""

import math
from functools import lru_cache
from .angles import norm_deg, EARTH_RADIUS_KM
from .time_utils import T_centuries, jd_ut_from_jd_tt, gmst_deg_from_jd_ut


@lru_cache(maxsize=4096)
def mean_obliquity_deg(T: float) -> float:
    """Return mean obliquity of the ecliptic (deg) for Julian centuries T."""
    secs = 84381.406 - 46.836769 * T - 0.0001831 * T * T + 0.00200340 * T * T * T
    return secs / 3600.0


def nutation_approx(jd: float) -> tuple[float, float]:
    """Very small set of nutation terms (longitude/obliquity) in degrees."""
    T = T_centuries(jd)
    Omega = math.radians(norm_deg(125.04452 - 1934.136261 * T + 0.0020708 * T * T))
    D = math.radians(norm_deg(297.85036 + 445267.111480 * T))
    delta_psi = (-17.20 * math.sin(Omega) - 1.32 * math.sin(2 * D)) / 3600.0
    delta_eps = (9.20 * math.cos(Omega) + 0.57 * math.cos(2 * D)) / 3600.0
    return delta_psi, delta_eps


def sun_ecliptic_longitude_deg(jd_tt: float) -> float:
    """Apparent ecliptic longitude of the Sun (deg) at TT Julian Day."""
    T = T_centuries(jd_tt)
    L0 = 280.4664567 + 36000.76982779 * T + 0.0003032028 * T * T
    M = 357.52911 + 35999.0502909 * T - 0.0001536 * T * T
    M_rad = math.radians(M)
    C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
    C += (0.019993 - 0.000101 * T) * math.sin(2 * M_rad) + 0.000289 * math.sin(3 * M_rad)
    true_long = L0 + C
    omega = 125.04 - 1934.136 * T
    lam = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    return norm_deg(lam)


def moon_ecliptic_longitude_and_distance(jd_tt: float) -> tuple[float, float]:
    """Geocentric lunar ecliptic longitude (deg) and distance (km), reduced series."""
    T = T_centuries(jd_tt)
    Lp = norm_deg(218.3164477 + 481267.88123421 * T - 0.0015786 * T * T + T ** 3 / 538841.0 - T ** 4 / 65194000.0)
    D = norm_deg(297.8501921 + 445267.1114034 * T - 0.0018819 * T * T)
    M = norm_deg(357.5291092 + 35999.0502909 * T - 0.0001536 * T * T)
    Mp = norm_deg(134.9633964 + 477198.8675055 * T + 0.0087414 * T * T)
    F = norm_deg(93.2720950 + 483202.0175233 * T - 0.0036539 * T * T)

    D_r = math.radians(D)
    M_r = math.radians(M)
    Mp_r = math.radians(Mp)
    F_r = math.radians(F)
    E = 1 - 0.002516 * T - 0.0000074 * T * T

    terms = [
        (6288774, 0, 0, 1, 0, 0, -20905355),
        (1274027, 2, 0, -1, 0, 0, -3699111),
        (658314, 2, 0, 0, 0, 0, -2955968),
        (213618, 0, 0, 2, 0, 0, -569925),
        (-185116, 0, 1, 0, 0, 1, 48888),
        (-114332, 0, 0, 0, 2, 0, -3149),
        (58793, 2, 0, -2, 0, 0, 246158),
        (57066, 2, -1, -1, 0, 1, -152138),
        (53322, 2, 0, 1, 0, 0, -170733),
        (45758, 2, -1, 0, 0, 1, -204586),
        (-40923, 0, 1, -1, 0, 1, -129620),
        (-34720, 1, 0, 0, 0, 0, 108743),
        (-30383, 0, 1, 1, 0, 1, 104755),
        (15327, 2, 0, 0, -2, 0, 10321),
        (-12528, 0, 0, 1, 2, 0, 0),
        (10980, 0, 0, 1, -2, 0, 79661),
        (10675, 4, 0, -1, 0, 0, -34782),
        (10034, 0, 0, 3, 0, 0, -23210),
        (8548, 4, 0, -2, 0, 0, 0),
        (-7888, 2, 1, -1, 0, 1, 0),
        (-6766, 2, 1, 0, 0, 1, 0),
        (-5163, 1, 0, -1, 0, 0, 0),
        (4987, 1, 1, 0, 0, 1, 0),
        (4036, 2, -1, 1, 0, 1, 0),
        (3994, 2, 0, 2, 0, 0, 0),
        (3861, 4, 0, 0, 0, 0, 0),
        (3665, 2, 0, -3, 0, 0, 0),
        (-2689, 0, 1, -2, 0, 1, 0),
    ]

    sigma_l = 0.0
    sigma_r = 0.0
    for coef, d_m, m_m, mp_m, f_m, e_flag, r_coef in terms:
        arg = d_m * D_r + m_m * M_r + mp_m * Mp_r + f_m * F_r
        efac = (E ** abs(m_m)) if e_flag else 1.0
        sigma_l += coef * efac * math.sin(arg)
        sigma_r += r_coef * efac * math.cos(arg)

    lam = Lp + sigma_l / 1e6
    dist = 385000.56 + sigma_r / 1000.0
    return norm_deg(lam), dist


def sun_ra_dec_tt(jd_tt: float) -> tuple[float, float]:
    """Right ascension and declination of the Sun at TT JD (radians)."""
    lam = math.radians(sun_ecliptic_longitude_deg(jd_tt))
    eps = math.radians(mean_obliquity_deg(T_centuries(jd_tt)))
    x = math.cos(lam)
    y = math.cos(eps) * math.sin(lam)
    z = math.sin(eps) * math.sin(lam)
    ra = math.atan2(y, x)
    dec = math.atan2(z, math.sqrt(x * x + y * y))
    return ra, dec


def topocentric_moon_longitude(jd_tt: float, lat_deg: float, lon_deg: float, height_m: float = 0.0) -> float:
    """Approximate topocentric lunar ecliptic longitude (deg) including parallax.

    This uses a simplified transformation through equatorial coordinates and a
    small-angle parallax correction. It is not a full rigorous topocentric
    transform but adequate for day-level festival rules.
    """
    lam_geo_deg, dist_km = moon_ecliptic_longitude_and_distance(jd_tt)
    parallax_rad = math.asin(EARTH_RADIUS_KM / dist_km)
    lam = math.radians(lam_geo_deg)
    eps = math.radians(mean_obliquity_deg(T_centuries(jd_tt)))
    x = math.cos(lam)
    y = math.cos(eps) * math.sin(lam)
    z = math.sin(eps) * math.sin(lam)
    ra = math.atan2(y, x)
    dec = math.atan2(z, math.sqrt(x * x + y * y))

    jd_ut = jd_ut_from_jd_tt(jd_tt)
    GMST = gmst_deg_from_jd_ut(jd_ut)
    LST = math.radians(norm_deg(GMST + lon_deg))
    HA = LST - ra
    lat = math.radians(lat_deg)

    delta_ra = -math.asin(math.sin(parallax_rad) * math.sin(HA) / math.cos(dec))
    delta_dec = math.asin((math.sin(dec) - math.sin(parallax_rad) * math.sin(lat)) * math.cos(delta_ra) - math.cos(dec) * math.sin(delta_ra) * math.sin(lat))
    ra_top = ra + delta_ra
    dec_top = dec + delta_dec
    
    sin_lam = math.sin(ra_top) * math.cos(eps) + math.tan(dec_top) * math.sin(eps)
    cos_lam = math.cos(ra_top)
    lam_top = math.atan2(sin_lam, cos_lam)
    return norm_deg(math.degrees(lam_top))
