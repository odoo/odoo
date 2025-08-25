"""Sidereal (Lahiri) conversion and solar ingress finder."""

from .angles import norm_deg
from .time_utils import T_centuries
from .astro import sun_ecliptic_longitude_deg


def lahiri_ayanamsa_deg(jd_tt: float) -> float:
    """Approximate Lahiri ayanamsa (deg) at TT JD.

    Uses a base value near J2000.0 and a linear drift ~1.396°/century with a
    small quadratic correction.
    """
    T = T_centuries(jd_tt)
    base_j2000 = 23.85308
    drift_deg_per_century = 1.3962634
    quad = -0.000044 * (T * T)
    return norm_deg(base_j2000 + drift_deg_per_century * T + quad)


def to_sidereal_deg(lambda_tropical_deg: float, jd_tt: float) -> float:
    """Convert tropical ecliptic longitude to Lahiri sidereal longitude (deg)."""
    return norm_deg(lambda_tropical_deg - lahiri_ayanamsa_deg(jd_tt))


def find_solar_sidereal_ingress_tt_near(jd_tt_guess: float, target_sid_deg: float) -> float:
    """Find TT JD when sidereal Sun equals target_sid_deg (secant-like method)."""
    x0 = jd_tt_guess - 2.0
    x1 = jd_tt_guess + 2.0
    def f(jd_tt):
        val = ((to_sidereal_deg(sun_ecliptic_longitude_deg(jd_tt), jd_tt) - target_sid_deg + 180.0) % 360.0) - 180.0
        return val
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
