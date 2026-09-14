"""Temporary debug instrumentation for the web quality-improvement campaign.

Four loggers under ``odoo.addons.web.debug``; enable one or all with
``--log-handler odoo.addons.web.debug:DEBUG`` (or ``.logic``, ``.performance``,
``.pipeline``, ``.lifecycle``). Every call site imports this module as ``dbg``,
so ``grep -rn 'dbg\\.' addons/web`` lists the whole instrumentation for removal.

- ``logic``: decision points -- which branch a guard took and on what input.
- ``performance``: wall time and statement count (round-trips, not rows) of a
  handler, helper or block; payload and fan-out sizes.
- ``pipeline``: hand-offs between stages of a request (route -> resolve ->
  render / stream; export -> search -> rows -> writer; login -> authenticate ->
  redirect), tagged ``[<kind>:<ref>]`` for correlation.
- ``lifecycle``: handler entry and exit, session and database transitions,
  attachment and record creation.

Controllers carry no ``env``: ``timed`` and ``timer`` read the cursor from
``self.env`` when the owner has one, else from ``request.env``, and count only
wall time when neither is bound (``auth="none"`` routes without a database).
Secrets never reach a line -- passwords, master passwords, tokens and session
tokens are logged as presence booleans only.
"""

import functools
import logging
import time
from contextlib import contextmanager

from odoo.http import request

_ROOT = "odoo.addons.web.debug"
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


def count(iterable):
    return _Lazy(lambda: len(iterable))


def _request_label():
    if not request:
        return "<no request>"
    http = request.httprequest
    session = request.session
    return (
        f"{http.method} {http.path} db={request.db or '-'} "
        f"uid={getattr(session, 'uid', None) or '-'}"
    )


def req():
    return _Lazy(_request_label)


def _cursor_of(env):
    return getattr(env, "cr", None) if env is not None else None


def _env_of(owner):
    env = getattr(owner, "env", None)
    if env is not None:
        return env
    return request.env if request else None


def _statements(cr):
    return getattr(cr, "sql_statement_count", 0) if cr is not None else 0


def timed(func=None, *, label=None):
    def decorate(fn):
        name = label or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not performance.isEnabledFor(DEBUG):
                return fn(self, *args, **kwargs)
            cr = _cursor_of(_env_of(self))
            queries = _statements(cr)
            start = time.perf_counter()
            try:
                return fn(self, *args, **kwargs)
            finally:
                performance.debug(
                    "%s: %.1f ms, %d statements",
                    name,
                    (time.perf_counter() - start) * 1000,
                    _statements(cr) - queries,
                )

        return wrapper

    return decorate(func) if func is not None else decorate


@contextmanager
def timer(env, label, *args):
    if not performance.isEnabledFor(DEBUG):
        yield
        return
    cr = _cursor_of(env)
    queries = _statements(cr)
    start = time.perf_counter()
    try:
        yield
    finally:
        performance.debug(
            "%s: %.1f ms, %d statements",
            label % args if args else label,
            (time.perf_counter() - start) * 1000,
            _statements(cr) - queries,
        )
