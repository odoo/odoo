import logging

from .base_lru_cache import BaseLRUCache
from odoo.addons.rate_limit.tools import registry_singleton

_logger = logging.getLogger(__name__)


class SessionCache(BaseLRUCache):
    def __init__(self, max_size: int = 100, ttl_hours: float = 1):
        super().__init__(
            max_size=max_size, ttl_hours=ttl_hours, use_reentrant_lock=True
        )
        _logger.info(
            "SessionCache initialized: max_size=%d, ttl=%.1fh",
            max_size,
            ttl_hours,
        )


def get_session_cache(env, max_size: int = 100, ttl_hours: float = 1) -> SessionCache:
    def prepare_session_cache() -> SessionCache:
        _logger.info(
            "Created new session cache for database '%s': max_size=%d, ttl=%.1fh",
            env.cr.dbname,
            max_size,
            ttl_hours,
        )
        return SessionCache(max_size=max_size, ttl_hours=ttl_hours)

    return registry_singleton(env, "_session_cache", prepare_session_cache)


def invalidate_session_cache(env) -> None:
    registry = env.registry

    if hasattr(registry, "_session_cache"):
        removed = registry._session_cache.invalidate_all()
        _logger.info(
            "Manually invalidated session cache for database '%s': %d entries removed",
            env.cr.dbname,
            removed,
        )
