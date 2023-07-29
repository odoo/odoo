from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any


class RateLimiter:
    def __init__(self, max_count: int, time_window: timedelta):
        self._max_count: int = max_count
        self._time_window: timedelta = time_window
        self._timestamps: defaultdict[Any, list[datetime]] = defaultdict(list)

    def is_rate_limited(self, key: Any) -> bool:
        now = datetime.now()
        timestamps = self._timestamps[key]
        while timestamps and now - timestamps[0] >= self._time_window:
            # Remove timestamps that are older than the time window.
            timestamps.pop(0)

        if len(timestamps) < self._max_count:
            timestamps.append(now)
            return False
        return True
