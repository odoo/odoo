import logging
import threading
from collections import OrderedDict
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from odoo import fields

_logger = logging.getLogger(__name__)


class BaseLRUCache:
    def __init__(
        self,
        max_size: int = 100,
        ttl_hours: float | None = None,
        use_reentrant_lock: bool = False,
    ):
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = timedelta(hours=ttl_hours) if ttl_hours else None
        self._lock = threading.RLock() if use_reentrant_lock else threading.Lock()

    def _on_evict(self, key: str, entry: dict[str, Any]) -> None:
        return None

    def _evict(self, entries: list[tuple[str, dict[str, Any]]]) -> int:
        for key, entry in entries:
            try:
                self._on_evict(key, entry)
            except Exception as e:
                _logger.error("Eviction handler failed for %s: %s", key, e)
        return len(entries)

    def get(self, key: str) -> Any | None:
        expired = None
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if self._is_expired(entry):
                expired = self._cache.pop(key, None)
            else:
                entry["timestamp"] = fields.Datetime.now()
                self._cache.move_to_end(key)
                return entry["value"]

        if expired is not None:
            _logger.debug("LRU entry expired on read: %s", key)
            self._evict([(key, expired)])
        return None

    def set(
        self,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        evicted = self._set_entry(key, value, metadata)
        if evicted is not None:
            self._evict([(key, evicted)])

    def invalidate(self, key: str) -> bool:
        entry = self._remove(key)
        if entry is None:
            return False
        self._evict([(key, entry)])
        _logger.debug("Cache entry invalidated: %s", key)
        return True

    def invalidate_all(self) -> int:
        removed = self._evict(self._clear())
        if removed:
            _logger.info("Cache cleared: %d entries removed", removed)
        return removed

    def invalidate_matching(self, filter_func: Callable[[str], bool]) -> int:
        return self._evict(self._invalidate_matching(filter_func))

    def get_metadata(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            return {
                "created_at": entry.get("created_at") or entry["timestamp"],
                "last_used": entry["timestamp"],
                "metadata": entry["metadata"],
            }

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())

    def _is_expired(self, entry: dict[str, Any]) -> bool:
        if not self._ttl:
            return False
        timestamp = entry.get("timestamp")
        if not timestamp:
            return False
        return fields.Datetime.now() - timestamp > self._ttl

    def _get_entry(self, key: str) -> dict[str, Any] | None:
        return self._cache.get(key)

    def _set_entry(
        self,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        evicted = None

        with self._lock:
            if len(self._cache) >= self._max_size and key not in self._cache:
                oldest_key = next(iter(self._cache))
                evicted = self._cache.pop(oldest_key)
                _logger.debug(
                    "LRU evicting oldest entry: %s (size: %d/%d)",
                    oldest_key,
                    len(self._cache),
                    self._max_size,
                )

            now = fields.Datetime.now()
            existing = self._cache.get(key)
            self._cache[key] = {
                "value": value,
                "metadata": metadata or {},
                "timestamp": now,
                "created_at": existing["created_at"] if existing else now,
            }

            self._cache.move_to_end(key)

        return evicted

    def _touch(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                self._cache[key]["timestamp"] = fields.Datetime.now()
                self._cache.move_to_end(key)

    def _remove(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            return self._cache.pop(key, None)

    def _clear(self) -> list[tuple[str, dict[str, Any]]]:
        with self._lock:
            entries = list(self._cache.items())
            self._cache.clear()
            return entries

    def _invalidate_matching(
        self,
        filter_func: Callable[[str], bool],
    ) -> list[tuple[str, dict[str, Any]]]:
        with self._lock:
            keys_to_remove = [key for key in self._cache if filter_func(key)]
            removed = [(key, self._cache.pop(key)) for key in keys_to_remove]

        if removed:
            _logger.debug("Invalidated %d cache entries matching filter", len(removed))

        return removed

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            size = len(self._cache)
            return {
                "size": size,
                "max_size": self._max_size,
                "ttl_hours": (self._ttl.total_seconds() / 3600 if self._ttl else None),
                "usage_pct": (
                    (size / self._max_size * 100) if self._max_size > 0 else 0
                ),
            }

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        return key in self._cache
