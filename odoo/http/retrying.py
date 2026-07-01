from __future__ import annotations

import logging
import random
import time
import typing

import psycopg2
import psycopg2.errorcodes

from odoo.exceptions import ConcurrencyError, ValidationError
from odoo.sql_db import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from . import request

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from odoo.api import Environment

_logger = logging.getLogger('odoo.http')

MAX_TRIES_ON_CONCURRENCY_FAILURE = 5
""" How many times retrying() is allowed to retry. """


def retrying[T](func: Callable[[], T], env: Environment, *, close_on_commit: bool = True) -> T:
    """
    Call ``func``in a loop until the SQL transaction commits with no
    serialisation error. It rollbacks the transaction in between calls.

    A serialisation error occurs when two independent transactions
    attempt to commit incompatible changes such as writing different
    values on a same record. The first transaction to commit works, the
    second is canceled with a :class:`psycopg2.errors.SerializationFailure`.

    This function intercepts those serialization errors, rollbacks the
    transaction, reset things that might have been modified, waits a
    random bit, and then calls the function again.

    It calls the function up to ``MAX_TRIES_ON_CONCURRENCY_FAILURE`` (5)
    times. The time it waits between calls is random with an exponential
    backoff: ``random.uniform(0.0, 2 ** i)`` where ``i`` is the n° of
    the current attempt and starts at 1.

    :param func: The function to call, you can pass arguments
        using :func:`functools.partial`.
    :param env: The environment where the registry
        and the cursor are taken.
    :param close_on_commit: Close the cursor after committing
    """
    tryno = 0
    while True:
        tryno += 1
        try:
            result = func()
            if not env.cr.closed:
                env.cr.flush()  # submit the changes to the database
            break
        except (
            psycopg2.IntegrityError,
            psycopg2.OperationalError,
            ConcurrencyError,
        ) as exc:
            if env.cr.closed:
                raise
            env.cr.rollback()
            if request:
                # We need to reset the `session` attribute of `request`
                # which may have been modified during the transaction.
                # The `dbname` remains the same (consistent with the session).
                from .router import _set_session_and_dbname  # noqa: PLC0415
                _set_session_and_dbname(request)
                # Rewind files in case of failure
                for filename, file in request.httprequest.files.items():
                    if hasattr(file, "seekable") and file.seekable():
                        file.seek(0)
                    else:
                        e = ("Cannot retry request on input file "
                            f"{filename!r} after serialization failure")
                        raise RuntimeError(e) from exc
            if isinstance(exc, psycopg2.IntegrityError):
                model = env['base']
                for rclass in env.registry.values():
                    if exc.diag.table_name == rclass._table:
                        model = env[rclass._name]
                        break
                message = env._(
                    "The operation cannot be completed: %s",
                    model._sql_error_to_message(exc))
                raise ValidationError(message) from exc

            if isinstance(exc, PG_CONCURRENCY_EXCEPTIONS_TO_RETRY):
                error = psycopg2.errorcodes.lookup(exc.pgcode)
            elif isinstance(exc, ConcurrencyError):
                error = repr(exc)
            else:
                raise

            tryleft = MAX_TRIES_ON_CONCURRENCY_FAILURE - tryno
            if not tryleft:
                _logger.info("%s, maximum number of tries reached!", error)
                raise

            wait_time = random.uniform(0.0, 2 ** tryno)
            _logger.info("%s, %s tries left, try again in %.04f sec...",
                error, tryleft, wait_time)
            time.sleep(wait_time)

    if not env.cr.closed:
        env.cr._closing = close_on_commit  # cursor should not be used after the commit
        env.cr.commit()  # effectively commits and execute post-commits
    return result
