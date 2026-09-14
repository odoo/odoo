"""Temporary debug instrumentation for the hr_attendance quality-improvement campaign.

Four loggers under ``odoo.addons.hr_attendance.debug``; enable one or all with
``--log-handler odoo.addons.hr_attendance.debug:DEBUG`` (or ``.logic``, ``.performance``,
``.pipeline``, ``.lifecycle``). Every call site imports this module as ``dbg``,
so ``grep -rn 'dbg\\.' addons/hr_attendance`` lists the whole instrumentation for removal.

- ``logic``: decision points -- which branch a guard took and on what input.
- ``performance``: wall time and query count of a method or block.
- ``pipeline``: hand-offs between stages of a flow (kiosk/systray request ->
  employee -> attendance; attendance write -> overtime window -> rule -> line),
  tagged ``[<kind>:<ref>]`` for correlation.
- ``lifecycle``: create / write / unlink / overtime regeneration / cron entry and
  exit.
"""

import functools
import logging
import time
from contextlib import contextmanager

_ROOT = "odoo.addons.hr_attendance.debug"
DEBUG = logging.DEBUG

logic = logging.getLogger(f"{_ROOT}.logic")
performance = logging.getLogger(f"{_ROOT}.performance")
pipeline = logging.getLogger(f"{_ROOT}.pipeline")
lifecycle = logging.getLogger(f"{_ROOT}.lifecycle")

_MAX_IDS = 8


class _Lazy:
    __slots__ = ("fn",)

    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        try:
            return str(self.fn())
        except Exception as exc:  # a label must never break the caller
            return f"<unprintable: {exc!r}>"

    __repr__ = __str__


def lazy(fn):
    return _Lazy(fn)


def _label(records):
    name = records._name
    ids = records._ids
    if not ids:
        return f"{name}[]"
    shown = ",".join(str(i) for i in ids[:_MAX_IDS])
    if len(ids) > _MAX_IDS:
        return f"{name}[{len(ids)}: {shown},...]"
    return f"{name}({shown})"


def rec(records):
    return _Lazy(lambda: _label(records))


def keys(vals):
    return _Lazy(lambda: sorted(vals))


def vals_keys(vals_list):
    return _Lazy(lambda: sorted({k for vals in vals_list for k in vals}))


def names(records, field="display_name"):
    return _Lazy(lambda: records.mapped(field)[:_MAX_IDS])


def timed(func=None, *, label=None):
    def decorate(fn):
        name = label or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not performance.isEnabledFor(DEBUG):
                return fn(self, *args, **kwargs)
            cr = self.env.cr
            queries = cr.sql_statement_count
            start = time.perf_counter()
            try:
                return fn(self, *args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                queries = cr.sql_statement_count - queries
                if queries or elapsed >= 0.05 or self:
                    performance.debug(
                        "%s on %s: %.1f ms, %d queries",
                        name,
                        rec(self),
                        elapsed,
                        queries,
                    )

        return wrapper

    return decorate(func) if func is not None else decorate


@contextmanager
def timer(env, label, *args):
    if not performance.isEnabledFor(DEBUG):
        yield
        return
    cr = env.cr
    queries = cr.sql_statement_count
    start = time.perf_counter()
    try:
        yield
    finally:
        performance.debug(
            "%s: %.1f ms, %d queries",
            label % args if args else label,
            (time.perf_counter() - start) * 1000,
            cr.sql_statement_count - queries,
        )
