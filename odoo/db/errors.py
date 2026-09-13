from __future__ import annotations

import logging
import re
from typing import Any

import psycopg

from odoo.libs.debug_log import DebugLog

CURSOR_LOGGER_NAME = "odoo.db.cursor"

_logger = logging.getLogger(CURSOR_LOGGER_NAME)
_debug = DebugLog(__name__)


PG_RETRY_EXCEPTIONS = (
    psycopg.errors.LockNotAvailable,
    psycopg.errors.SerializationFailure,
    psycopg.errors.DeadlockDetected,
)

PG_RETRY_SQLSTATES: tuple[str, ...] = tuple(e.sqlstate for e in PG_RETRY_EXCEPTIONS)

PG_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    *PG_RETRY_EXCEPTIONS,
    psycopg.errors.ReadOnlySqlTransaction,
)

PG_USER_FAULT_EXCEPTIONS: tuple[type[Exception], ...] = (psycopg.IntegrityError,)

_STALE_PLAN_ATTR = "_odoo_stale_cached_plan"

_SEAM_ATTR = "_odoo_handled_by_statement_seam"

_STATEMENT_VERB_ATTR = "_odoo_failed_statement_verb"

_STATEMENT_VERB_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|COPY)\b", re.IGNORECASE)

PG_STALE_PLAN_EXCEPTIONS: tuple[type[Exception], ...] = (
    psycopg.errors.FeatureNotSupported,
)


def has_reached_server(exc: BaseException) -> bool:
    return getattr(exc, "sqlstate", None) is not None


def mark_stale_cached_plan(exc: Exception) -> None:
    _debug.lifecycle("errors.stale_plan_marked", error=type(exc).__name__)
    setattr(exc, _STALE_PLAN_ATTR, True)


def is_stale_cached_plan(exc: BaseException) -> bool:
    return getattr(exc, _STALE_PLAN_ATTR, False) is True


def mark_handled_by_seam(exc: BaseException) -> None:
    setattr(exc, _SEAM_ATTR, True)


def is_handled_by_seam(exc: BaseException) -> bool:
    return getattr(exc, _SEAM_ATTR, False) is True


def mark_failed_statement(exc: BaseException, query: Any) -> None:
    # PostgreSQL reports both sides of a foreign-key violation with the same
    # SQLSTATE and diagnostics; only lc_messages-dependent prose tells an
    # INSERT that points nowhere from a DELETE something still points at.
    # The statement verb is the locale-proof witness.
    if match := _STATEMENT_VERB_RE.search(str(query)):
        setattr(exc, _STATEMENT_VERB_ATTR, match[1].upper())


def failed_statement_verb(exc: BaseException) -> str | None:
    return getattr(exc, _STATEMENT_VERB_ATTR, None)


def _classify_sql_error(exc: Exception) -> str:
    if is_stale_cached_plan(exc):
        return "stale_plan"
    if isinstance(exc, PG_RECOVERABLE_EXCEPTIONS):
        return "recoverable"
    if isinstance(exc, PG_USER_FAULT_EXCEPTIONS):
        return "user_fault"
    return "bad_statement"


def _log_sql_error(exc: Exception, query: Any, *, label: str = "query") -> None:
    klass = _classify_sql_error(exc)
    diag = getattr(exc, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    if _debug.logic.enabled:
        _debug.logic(
            "errors.sql_error_classified",
            label=label,
            error=type(exc).__name__,
            sqlstate=getattr(exc, "sqlstate", None),
            klass=klass,
            retryable=isinstance(exc, PG_RETRY_EXCEPTIONS),
            constraint=constraint,
            detail=getattr(diag, "message_detail", None),
            context=getattr(diag, "context", None),
        )
    if klass == "stale_plan":
        _logger.warning(
            "stale cached plan discarded (caller may retry): %s: %s",
            type(exc).__name__,
            query,
        )
    elif klass == "recoverable":
        _logger.warning(
            "recoverable SQL error (caller may retry): %s: %s",
            type(exc).__name__,
            query,
        )
    elif klass == "user_fault":
        _logger.warning(
            "constraint violation (surfaced to the user): %s%s: %s",
            type(exc).__name__,
            f" on {constraint}" if constraint else "",
            query,
        )
    else:
        _logger.error("bad %s: %s\nERROR: %s", label, query, exc)
