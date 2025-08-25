"""Location model and a small set of example codes for convenience."""

from dataclasses import dataclass


@dataclass
class Location:
    """Observer location and fixed UTC offset.

    Fields:
    - lat, lon: degrees (positive north/east)
    - tz: fixed UTC offset hours (no DST)
    - height_m: elevation in meters (used in more advanced models)
    """
    lat: float
    lon: float
    tz: float
    height_m: float = 0.0

    # Islamic calendar policy
    method: str = "astronomical"
    visibility_thresholds: tuple[float, float] | None = None

    def thresholds_or_default(self) -> tuple[float, float]:
        """Return policy thresholds or global defaults."""
        return self.visibility_thresholds or (9.0, 17.0)
