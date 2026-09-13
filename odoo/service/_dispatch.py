from __future__ import annotations

import annotationlib
import functools
import inspect
import logging
import re
from collections.abc import Callable, Sequence
from typing import Any

from odoo.db import is_maintenance_db
from odoo.libs.debug_log import DebugLog

from .settings import current

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

__all__ = (
    "dispatch_through_table",
    "get_positional_bounds",
    "get_static_dbfilter",
    "is_db_rpc_exposed",
)


_HOST_PLACEHOLDER_RE = re.compile(r"%[hd]")


@functools.lru_cache(maxsize=8)
def _compile_static_dbfilter(pattern: str) -> re.Pattern[str] | None:
    # Cached per pattern so each warning is said once, not once per RPC call
    # or per cron sweep.
    if _HOST_PLACEHOLDER_RE.search(pattern):
        _debug.logic("rpc.dbfilter_unusable", reason="host_placeholder")
        _logger.warning(
            "dbfilter %r resolves against the request host (%%h/%%d), so it "
            "cannot scope cron and job polling or RPC: those carry no request "
            "host. This process will poll every database its role owns and "
            "answer RPC for any of them. Set db_name to name the databases it "
            "serves, or write a dbfilter with no host placeholder.",
            pattern,
        )
        return None
    try:
        return re.compile(pattern)
    except re.error:
        _logger.warning(
            "dbfilter %r is not a valid regular expression; not scoping cron, "
            "job polling or RPC with it",
            pattern,
            exc_info=True,
        )
        _debug.logic("rpc.dbfilter_unusable", reason="invalid_regex")
        return None


def get_static_dbfilter(pattern: str | None = None) -> re.Pattern[str] | None:
    if pattern is None:
        pattern = current().dbfilter
    return _compile_static_dbfilter(pattern) if pattern else None


def is_db_rpc_exposed(db_name: object) -> bool:
    if not isinstance(db_name, str) or not db_name:
        return False
    if is_maintenance_db(db_name):
        _debug.logic("rpc.db_not_exposed", db=db_name, reason="maintenance")
        return False
    settings = current()
    exposed = settings.db_name
    if exposed:
        allowed = db_name in exposed
        reason = "db_name"
    else:
        dbfilter = get_static_dbfilter(settings.dbfilter)
        allowed = dbfilter is None or dbfilter.match(db_name) is not None
        reason = "dbfilter"
    if _debug.logic.enabled and not allowed:
        _debug.logic("rpc.db_not_exposed", db=db_name, reason=reason)
    return allowed


@functools.cache
def get_positional_bounds(handler: Callable) -> tuple[int, int | None, tuple[str, ...]]:
    required = 0
    maximum = 0
    names: list[str] = []
    signature = inspect.signature(
        handler, annotation_format=annotationlib.Format.FORWARDREF
    )
    for param in signature.parameters.values():
        if param.kind is param.VAR_POSITIONAL:
            _debug.perf.count(
                "rpc.signature_inspected",
                handler=getattr(handler, "__qualname__", None),
                required=required,
                variadic=True,
            )
            return required, None, tuple(names)
        if param.kind not in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
            continue
        names.append(param.name)
        maximum += 1
        if param.default is param.empty:
            required += 1
    _debug.perf.count(
        "rpc.signature_inspected",
        handler=getattr(handler, "__qualname__", None),
        required=required,
        maximum=maximum,
    )
    return required, maximum, tuple(names)


def _check_arity(method: str, handler: Callable, count: int) -> None:
    required, maximum, names = get_positional_bounds(handler)
    if count < required:
        expected = ", ".join(names[:required])
        _debug.logic("rpc.arity_rejected", method=method, required=required, got=count)
        raise TypeError(
            f"RPC method {method!r} requires {required} positional "
            f"argument(s) ({expected}); got {count}."
        )
    if maximum is not None and count > maximum:
        _debug.logic("rpc.arity_rejected", method=method, maximum=maximum, got=count)
        raise TypeError(
            f"RPC method {method!r} takes at most {maximum} positional "
            f"argument(s); got {count}."
        )


def dispatch_through_table(
    method: str,
    params: Sequence[Any],
    table: dict[str, Callable],
    *,
    credentialed: frozenset[str] = frozenset(),
    check_credential: Callable[[Any], Any] | None = None,
) -> Any:
    handler = table.get(method)
    if handler is None:
        _debug.logic("rpc.method_not_found", method=method, table=len(table))
        raise AttributeError(f"Method not found: {method}")
    args = list(params)
    _debug.pipeline(
        "rpc.table_dispatch",
        method=method,
        args=len(args),
        credentialed=method in credentialed,
    )
    if method in credentialed:
        if not args:
            _debug.logic("rpc.credential_missing", method=method)
            raise TypeError(
                f"{method} requires a master password as its first positional "
                f"argument; got 0 arguments."
            )
        if check_credential is None:
            _debug.logic("rpc.credential_unverifiable", method=method)
            raise RuntimeError(
                f"{method!r} is listed as credentialed but the dispatch table "
                f"passed no check_credential; refusing to call it unverified"
            )
        credential, *args = args
        check_credential(credential)
        _debug.pipeline("rpc.credential_checked", method=method)
    _check_arity(method, handler, len(args))
    with _debug.perf(
        "rpc.table_handled",
        method=method,
        handler=getattr(handler, "__qualname__", None),
    ):
        return handler(*args)
