"""Redis-backed HTTP session store for Odoo.

Replaces Odoo's default ``odoo.http.Session`` filesystem storage with a
Redis backend.  The store is only activated when the environment variable
``ODOO_SESSION_REDIS_URL`` is set — in local dev without Redis, the
default file-based store is used unchanged.

Design decisions:
- Sessions are stored as JSON strings (not pickled) so they are
  inspectable with ``redis-cli`` and immune to Python version skew.
- Each session gets a TTL of 7 days (``SESSION_TTL_DAYS``).  Idle
  sessions are garbage-collected by Redis automatically — no cron needed.
- The key prefix ``odoo-session:`` namespaces sessions to avoid
  collisions with other Redis users (e.g. the LLM cache).

Integration with Odoo:
  The ``post_init_hook`` in ``hooks.py`` monkey-patches
  ``odoo.http.Session`` to use this store.  The patch is applied once
  at server start; all subsequent ``session.save()`` / ``session.load()``
  calls go through Redis.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "")
REDIS_PREFIX = os.environ.get("ODOO_SESSION_REDIS_PREFIX", "odoo-session:")
SESSION_TTL_DAYS = int(os.environ.get("ODOO_SESSION_REDIS_TTL_DAYS", "7"))
SESSION_TTL_SECONDS = SESSION_TTL_DAYS * 86400


def _get_redis_client():
    """Create and cache a Redis connection pool.

    Returns ``None`` when Redis is not configured (local dev).
    """
    if not REDIS_URL:
        return None
    try:
        import redis

        return redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    except ImportError:
        _logger.warning(
            "session_redis: redis package not installed; "
            "falling back to file-based sessions"
        )
        return None
    except Exception:
        _logger.exception(
            "session_redis: failed to connect to Redis at %s; "
            "falling back to file-based sessions",
            REDIS_URL,
        )
        return None


# Module-level singleton — created once on first import.
_redis_client = None


def get_redis():
    """Return the Redis client, creating it lazily."""
    global _redis_client
    if _redis_client is None:
        _redis_client = _get_redis_client()
    return _redis_client


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

_SESSION_INTERNAL_KEYS = frozenset({
    "_uid",
    "_login",
    "_password",
    "_database",
    "_context",
    "_lang",
    "_tz",
    "_company_ids",
    "_company_id",
    "_active_id",
})


def _serialize_session(session) -> str:
    """Dump the session mapping to a JSON string.

    Private attributes (leading underscore) are preserved so Odoo can
    reconstruct the session fully on load.
    """
    data: dict[str, Any] = {}
    for key in list(session):
        try:
            val = session[key]
            # Only store JSON-serializable values; skip the rest.
            json.dumps(val)
            data[key] = val
        except (TypeError, ValueError):
            continue
    return json.dumps(data)


def _deserialize_session(data_str: str) -> dict[str, Any]:
    """Load session data from a JSON string."""
    if not data_str:
        return {}
    try:
        return json.loads(data_str)
    except (TypeError, ValueError):
        _logger.warning("session_redis: corrupted session data, discarding")
        return {}


# ---------------------------------------------------------------------------
# Redis Session Store API — called by hooks.py monkey-patch
# ---------------------------------------------------------------------------

class RedisSessionStore:
    """Thin wrapper that Odoo's session machinery calls into.

    The monkey-patch in ``hooks.py`` replaces the file-based
    ``odoo.http.Session`` load/save with these methods.
    """

    def __init__(self, redis_client=None, prefix: str = REDIS_PREFIX,
                 ttl: int = SESSION_TTL_SECONDS):
        self._redis = redis_client or get_redis()
        self._prefix = prefix
        self._ttl = ttl

    @property
    def available(self) -> bool:
        """True when Redis is connected and ready."""
        return self._redis is not None

    def _key(self, sid: str) -> str:
        """Build the full Redis key for a session ID."""
        return f"{self._prefix}{sid}"

    def save(self, session) -> None:
        """Persist session data to Redis."""
        if not self.available:
            return
        sid = getattr(session, "sid", None)
        if not sid:
            return
        try:
            payload = _serialize_session(session)
            self._redis.setex(self._key(sid), self._ttl, payload)
        except Exception:
            _logger.exception(
                "session_redis: failed to save session %s", sid,
            )

    def load(self, sid: str) -> dict[str, Any]:
        """Load session data from Redis.

        :return: dict of session attributes, or empty dict if not found.
        """
        if not self.available or not sid:
            return {}
        try:
            data_str = self._redis.get(self._key(sid))
            if data_str is None:
                return {}
            return _deserialize_session(data_str)
        except Exception:
            _logger.exception(
                "session_redis: failed to load session %s", sid,
            )
            return {}

    def delete(self, sid: str) -> None:
        """Remove a session from Redis (logout)."""
        if not self.available or not sid:
            return
        try:
            self._redis.delete(self._key(sid))
        except Exception:
            _logger.exception(
                "session_redis: failed to delete session %s", sid,
            )

    def rotate(self, old_sid: str, new_sid: str) -> None:
        """Rotate a session ID (security: regenerate on login).

        Copies the data under the new key and deletes the old one.
        """
        if not self.available:
            return
        try:
            data_str = self._redis.get(self._key(old_sid))
            if data_str is not None:
                pipe = self._redis.pipeline()
                pipe.setex(self._key(new_sid), self._ttl, data_str)
                pipe.delete(self._key(old_sid))
                pipe.execute()
        except Exception:
            _logger.exception(
                "session_redis: failed to rotate session %s -> %s",
                old_sid, new_sid,
            )


# Module-level singleton for the store
session_store = RedisSessionStore()
