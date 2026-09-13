from __future__ import annotations

import logging
import time
import typing
from contextlib import suppress

from psycopg import IntegrityError, OperationalError

from odoo.db.errors import (
    PG_RETRY_EXCEPTIONS,
    PG_RETRY_SQLSTATES,
    PG_STALE_PLAN_EXCEPTIONS,
    is_stale_cached_plan,
)
from odoo.exceptions import ConcurrencyError, ValidationError
from odoo.libs import backoff
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from odoo.api import Environment

_logger = logging.getLogger("odoo.service.model")
_debug = DebugLog(__name__)

PG_CONCURRENCY_ERRORS_TO_RETRY = PG_RETRY_SQLSTATES
PG_CONCURRENCY_EXCEPTIONS_TO_RETRY = PG_RETRY_EXCEPTIONS
MAX_TRIES_ON_CONCURRENCY_FAILURE = 5

BASE_CONCURRENCY_BACKOFF_SECONDS = 0.2

MAX_CONCURRENCY_BACKOFF_SECONDS = 2.0

_RECOVERY_EXCEPTIONS: tuple[type[Exception], ...] = (
    IntegrityError,
    OperationalError,
    ConcurrencyError,
    *PG_STALE_PLAN_EXCEPTIONS,
)


def _integrity_error_to_validation_error(
    env: Environment, exc: IntegrityError
) -> ValidationError:
    table_name = exc.diag.table_name
    rclass = env.registry.models_by_table.get(table_name) if table_name else None
    model = env[rclass._name] if rclass is not None else env["base"]
    _debug.logic(
        "retrying.integrity_error.model_resolved",
        table=table_name,
        model=getattr(model, "_name", None),
        constraint=exc.diag.constraint_name,
    )
    message = env._(
        "The operation cannot be completed: %s",
        model._sql_error_to_message(exc),
    )
    return ValidationError(message)


class RetryParticipant(typing.Protocol):
    def on_rollback(self, exc: BaseException) -> None: ...

    def on_retry(self, exc: BaseException) -> None: ...

    def is_uncommitted_warning_suppressed(self) -> bool: ...


def _describe(func: Callable[..., object]) -> str:
    return getattr(func, "__qualname__", type(func).__name__)


def _reset_env_state(env: Environment) -> None:
    if env.cr.closed:
        _debug.logic("retrying.env_reset_skipped", reason="cursor_closed")
        return
    _debug.lifecycle("retrying.env_reset")
    with suppress(Exception):
        env.transaction.reset()
    with suppress(Exception):
        env.registry.reset_changes()


def _warn_cursor_closed_before_commit(
    func: Callable[..., object], participant: RetryParticipant | None
) -> None:
    suppressed = (
        participant is not None and participant.is_uncommitted_warning_suppressed()
    )
    _debug.logic(
        "retrying.cursor_closed_before_commit",
        func=_describe(func),
        warning_suppressed=suppressed,
    )
    if suppressed:
        return
    _logger.warning(
        "retrying(): the cursor was closed before commit; %s's work was "
        "NOT committed and no registry signal was sent. The handler closed "
        "its own cursor, or something else did.",
        _describe(func),
    )


def _commit_and_signal_changes(env: Environment) -> None:
    commits_before = env.cr.commit_count
    try:
        env.cr.commit()
    except Exception:
        _debug.logic(
            "retrying.commit_failed",
            committed=env.cr.commit_count > commits_before,
        )
        if env.cr.commit_count > commits_before:
            with suppress(Exception):
                env.registry.signal_changes()
        raise
    _debug.pipeline(
        "retrying.signalling",
        cursor_closed=env.cr.closed,
        commits=env.cr.commit_count - commits_before,
    )
    if not env.cr.closed:
        env.registry.signal_changes()
    elif env.cr.commit_count > commits_before:
        with suppress(Exception):
            env.registry.signal_changes()


def _rollback_transaction(env: Environment, exc: Exception) -> None:
    _debug.lifecycle(
        "retrying.rollback",
        error=type(exc).__name__,
        sqlstate=getattr(exc, "sqlstate", None),
    )
    try:
        env.cr.rollback()
    except Exception as rollback_error:
        _debug.logic("retrying.rollback_failed", error=type(rollback_error).__name__)
        raise exc from rollback_error
    if env.cr.closed:
        _debug.logic("retrying.rollback.cursor_closed", error=type(exc).__name__)
        raise exc
    env.transaction.reset()
    env.registry.reset_changes()
    _debug.lifecycle("retrying.rolled_back", error=type(exc).__name__)


def _resolve_retry_error_name(exc: Exception) -> str | None:
    if isinstance(exc, PG_RETRY_EXCEPTIONS):
        return type(exc).__name__
    if isinstance(exc, ConcurrencyError):
        return repr(exc)
    if is_stale_cached_plan(exc):
        return "StaleCachedPlan"
    _debug.logic(
        "retrying.not_retryable",
        error=type(exc).__name__,
        sqlstate=getattr(exc, "sqlstate", None),
    )
    return None


def retrying[T](
    func: Callable[[], T],
    env: Environment,
    participant: RetryParticipant | None = None,
) -> T:
    commits_before = env.cr.commit_count
    name = _describe(func)
    _debug.pipeline(
        "retrying.start",
        func=name,
        participant=participant is not None,
        max_tries=MAX_TRIES_ON_CONCURRENCY_FAILURE,
    )
    try:
        for tryno in range(1, MAX_TRIES_ON_CONCURRENCY_FAILURE + 1):
            tryleft = MAX_TRIES_ON_CONCURRENCY_FAILURE - tryno
            try:
                with _debug.perf(
                    "retrying.attempt", cr=env.cr, func=name, attempt=tryno
                ):
                    result = func()
                if env.cr.closed:
                    _warn_cursor_closed_before_commit(func, participant)
                    break
                env.cr.flush()
                _commit_and_signal_changes(env)
                _debug.pipeline("retrying.committed", func=name, attempt=tryno)
                break
            except _RECOVERY_EXCEPTIONS as exc:
                if env.cr.closed or env.cr.commit_count > commits_before:
                    _debug.logic("retrying.unrecoverable", cursor_closed=env.cr.closed)
                    raise
                _rollback_transaction(env, exc)
                if participant is not None:
                    _debug.pipeline(
                        "retrying.participant_rollback",
                        participant=type(participant).__name__,
                        error=type(exc).__name__,
                    )
                    participant.on_rollback(exc)
                if isinstance(exc, IntegrityError):
                    translated = None
                    with suppress(Exception):
                        translated = _integrity_error_to_validation_error(env, exc)
                    _debug.logic(
                        "retrying.integrity_error",
                        constraint=exc.diag.constraint_name,
                        table=exc.diag.table_name,
                        translated=translated is not None,
                    )
                    if translated is not None:
                        raise translated from exc
                    raise

                error = _resolve_retry_error_name(exc)
                if error is None:
                    _logger.info(
                        "OperationalError not retryable: %s (sqlstate=%s)",
                        type(exc).__name__,
                        getattr(exc, "sqlstate", None),
                    )
                    raise
                if not tryleft:
                    _logger.info("%s, maximum number of tries reached!", error)
                    _debug.logic("retrying.exhausted", error=error, attempts=tryno)
                    raise

                if participant is not None:
                    participant.on_retry(exc)
                wait_time = backoff.get_delay(
                    tryno,
                    base=BASE_CONCURRENCY_BACKOFF_SECONDS,
                    cap=MAX_CONCURRENCY_BACKOFF_SECONDS,
                )
                _debug.logic(
                    "retrying.retry",
                    error=error,
                    attempt=tryno,
                    tries_left=tryleft,
                    wait_s=wait_time,
                )
                _logger.info(
                    "%s, %s tries left, try again in %.04f sec...",
                    error,
                    tryleft,
                    wait_time,
                )
                time.sleep(wait_time)
    except Exception as exc:
        _debug.logic(
            "retrying.failed",
            func=name,
            error=type(exc).__name__,
            committed=env.cr.commit_count > commits_before,
        )
        if env.cr.commit_count == commits_before:
            _reset_env_state(env)
        raise
    return result


__all__ = (
    "BASE_CONCURRENCY_BACKOFF_SECONDS",
    "MAX_CONCURRENCY_BACKOFF_SECONDS",
    "MAX_TRIES_ON_CONCURRENCY_FAILURE",
    "PG_CONCURRENCY_ERRORS_TO_RETRY",
    "PG_CONCURRENCY_EXCEPTIONS_TO_RETRY",
    "RetryParticipant",
    "retrying",
)
