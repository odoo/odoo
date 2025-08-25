"""Lightweight math utilities and constants used across the calendar package."""

import math

RAD = math.pi / 180.0  # radians per degree
DEG = 180.0 / math.pi  # degrees per radian
EARTH_RADIUS_KM = 6378.137  # WGS-84 equatorial radius, km


def norm_deg(x: float) -> float:
    """Normalize angle to [0, 360) degrees."""
    x = x % 360.0
    if x < 0:
        x += 360.0
    return x


def wrap180(x: float) -> float:
    """Wrap angle to (-180, 180] degrees for robust sign-change tests."""
    return (x + 180.0) % 360.0 - 180.0
