"""Sentinel values for distinguishing special states from None.

Pure Python utility with no Odoo dependencies.
"""

__all__ = ["PENDING", "SENTINEL", "Sentinel"]

import enum


class Sentinel(enum.Enum):
    """Class for typing parameters with a sentinel as a default."""

    SENTINEL = -1
    PENDING = -2


SENTINEL = Sentinel.SENTINEL
PENDING = Sentinel.PENDING
"""Stored computed field awaiting recomputation.

Written into the field cache during ``_create()`` for stored computed
fields whose value hasn't been set explicitly.  Unlike ``None`` (which
is a valid cache value for nullable fields), ``PENDING`` unambiguously
signals "not yet computed" — any cache read that encounters it should
treat it as a cache miss and trigger recomputation via
``field.ensure_computed()`` or fall back to ``Field.__get__``.
"""
