"""Redis-backed LLM response cache for Claude extractions.

Cache key: SHA-256 of (model_id + prompt_version + ocr_text).
TTL: 24 hours by default (``LLM_CACHE_TTL_HOURS`` overrides).
Cache hit/miss counters tracked in Redis for monitoring.

Fail-open: any Redis error logs and returns a miss — a cache outage must
never break extraction.
"""

import hashlib
import json
import logging
import os

import redis

_logger = logging.getLogger(__name__)

# Configuration
CACHE_TTL_HOURS = float(os.environ.get("LLM_CACHE_TTL_HOURS", "24"))
CACHE_TTL_SECONDS = int(CACHE_TTL_HOURS * 3600)
CACHE_KEY_PREFIX = "invoice:llm:"
STATS_HITS_KEY = "invoice:llm:stats:hits"
STATS_MISSES_KEY = "invoice:llm:stats:misses"

# Prompt version — bump this to invalidate all cached extractions
# when the system prompt changes.
PROMPT_VERSION = os.environ.get("LLM_CACHE_PROMPT_VERSION", "v1")

_redis_client: redis.Redis | None = None


def _get_client() -> redis.Redis | None:
    """Return a lazily-created Redis client, or None when it fails."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return None
    try:
        _redis_client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    except Exception:
        _logger.exception("llm_cache: failed to create Redis client")
        return None
    return _redis_client


def build_cache_key(
    ocr_text: str,
    model_id: str,
    prompt_version: str = PROMPT_VERSION,
) -> str:
    """Deterministic cache key for LLM extraction results.

    The key includes the model and prompt version so that changing either
    automatically invalidates stale cache entries.
    """
    raw = f"{model_id}:{prompt_version}:{ocr_text}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{CACHE_KEY_PREFIX}{digest}"


def cache_get(ocr_text: str, model: str) -> dict | None:
    """Look up a cached extraction result.

    :return: the stored dict (``{"result": {...}}``) or None on miss/error.
    """
    client = _get_client()
    if client is None:
        return None

    key = build_cache_key(ocr_text, model)
    try:
        data = client.get(key)
        if data is not None:
            client.incr(STATS_HITS_KEY)
            _logger.info("llm_cache: HIT %s", key[-16:])
            return json.loads(data)
        client.incr(STATS_MISSES_KEY)
        _logger.info("llm_cache: MISS %s", key[-16:])
        return None
    except Exception:
        _logger.exception("llm_cache: error reading %s", key)
        return None


def _to_jsonable(value: object) -> object:
    """Convert pydantic models (and nested structures) to JSON-safe data.

    ``result["parsed"]`` is an ``InvoiceExtraction`` pydantic model; naive
    ``default=str`` would store its repr string and break cache reads.
    """
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


def cache_set(ocr_text: str, result: dict, model: str) -> None:
    """Store an extraction result with TTL."""
    client = _get_client()
    if client is None:
        return

    key = build_cache_key(ocr_text, model)
    payload = {"result": _to_jsonable(result)}
    try:
        client.setex(
            key,
            CACHE_TTL_SECONDS,
            json.dumps(payload),
        )
        _logger.info(
            "llm_cache: stored %s (TTL %ds)",
            key[-16:],
            CACHE_TTL_SECONDS,
        )
    except Exception:
        _logger.exception("llm_cache: error writing %s", key)


def cache_stats() -> dict:
    """Return cache hit/miss counters (for /v1/cache/stats)."""
    client = _get_client()
    if client is None:
        return {"error": "Redis unavailable"}
    try:
        hits = int(client.get(STATS_HITS_KEY) or 0)
        misses = int(client.get(STATS_MISSES_KEY) or 0)
        total = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate": f"{hits / total * 100:.1f}%" if total > 0 else "N/A",
        }
    except Exception:
        _logger.exception("llm_cache: error reading stats")
        return {"error": "Redis unavailable"}
