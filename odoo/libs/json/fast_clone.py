"""Fast deep clone for JSON-like data structures.

Uses the Rust ``odoo_rust`` extension when available (~5x faster),
with automatic fallback to a pure-Python implementation.
"""

__all__ = ["ACCEL_AVAILABLE", "fast_clone"]

ACCEL_AVAILABLE: bool

try:
    from odoo_rust import fast_clone

    ACCEL_AVAILABLE = True

except ImportError:
    ACCEL_AVAILABLE = False

    def fast_clone(obj):  # type: ignore[misc]
        """Deep-clone a JSON-like Python object.

        Specialized replacement for ``copy.deepcopy()`` — typically 3x faster
        because it skips the ``__deepcopy__`` protocol, memo dict, and cycle
        detection.  Safe for data from ``json.loads()`` or destined for
        ``json.dumps()`` (dict/list/tuple of str/int/float/bool/None).
        """
        if isinstance(obj, dict):
            return {k: fast_clone(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [fast_clone(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(fast_clone(v) for v in obj)
        return obj
