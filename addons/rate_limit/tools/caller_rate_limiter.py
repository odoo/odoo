import logging
import threading
from collections import OrderedDict
from datetime import timedelta

from odoo import fields

from .registry_singleton import registry_singleton

_logger = logging.getLogger(__name__)


class SlidingWindowLimiter:
    DEFAULT_MAX_KEYS = 10000

    def __init__(self, max_keys: int = DEFAULT_MAX_KEYS):
        self._attempts: OrderedDict[tuple, list] = OrderedDict()
        self._lock = threading.RLock()
        self._max_keys = max_keys
        _logger.info(
            "RateLimiter initialized with max_keys=%d",
            max_keys,
        )

    def check(self, key, limit=100, window_seconds=3600):
        with self._lock:
            now = fields.Datetime.now()
            window_start = now - timedelta(seconds=window_seconds)

            existing = self._attempts.get(key, [])

            filtered = [ts for ts in existing if ts > window_start]

            current_attempts = len(filtered)
            allowed = current_attempts < limit

            if allowed:
                key_is_new = key not in self._attempts
                if key_is_new and len(self._attempts) >= self._max_keys:
                    self._evict_oldest_key()

                filtered.append(now)
                current_attempts += 1

            if filtered:
                self._attempts[key] = filtered
                self._attempts.move_to_end(key)
            elif key in self._attempts:
                del self._attempts[key]

            reset_at = None
            if filtered:
                oldest = min(filtered)
                reset_at = oldest + timedelta(seconds=window_seconds)

            result = {
                "allowed": allowed,
                "attempts": current_attempts,
                "limit": limit,
                "window_seconds": window_seconds,
                "reset_at": reset_at,
            }

            if not allowed:
                _logger.warning(
                    "Rate limit exceeded for %s: %s/%s in %ss",
                    key,
                    current_attempts,
                    limit,
                    window_seconds,
                )

            return result

    def _evict_oldest_key(self):
        if not self._attempts:
            return

        oldest_key, _timestamps = self._attempts.popitem(last=False)
        _logger.debug(
            "Rate limiter evicted LRU key %s (max_keys=%d reached)",
            oldest_key,
            self._max_keys,
        )

    def reset(self, key):
        with self._lock:
            if key in self._attempts:
                del self._attempts[key]
                _logger.info("Rate limit reset for %s", key)

    def get_stats(self):
        with self._lock:
            total_attempts = sum(len(attempts) for attempts in self._attempts.values())
            total_keys = len(self._attempts)
            return {
                "total_keys": total_keys,
                "max_keys": self._max_keys,
                "total_attempts_tracked": total_attempts,
                "memory_usage_pct": (
                    (total_keys / self._max_keys * 100) if self._max_keys > 0 else 0.0
                ),
            }

    def cleanup_old_entries(self, max_age_hours=24):
        with self._lock:
            cutoff = fields.Datetime.now() - timedelta(hours=max_age_hours)
            keys_to_remove = []

            for key, attempts in self._attempts.items():
                self._attempts[key] = [ts for ts in attempts if ts > cutoff]

                if not self._attempts[key]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._attempts[key]

            if keys_to_remove:
                _logger.info(
                    "Rate limiter cleanup: removed %d empty keys",
                    len(keys_to_remove),
                )

            return len(keys_to_remove)


def get_caller_rate_limiter(env):
    def build() -> SlidingWindowLimiter:
        _logger.info(
            "Created inbound caller rate limiter for worker (database '%s')",
            env.cr.dbname,
        )
        return SlidingWindowLimiter()

    return registry_singleton(env, "_inbound_caller_rate_limiter", build)
