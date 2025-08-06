import logging
import random
import time

import psycopg2
import psycopg2.errorcodes

from odoo.exceptions import ConcurrencyError, ValidationError
from odoo.sql_db import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

_logger = logging.getLogger('odoo.http')

MAX_TRIES_ON_CONCURRENCY_FAILURE = 5
""" How many times retrying() is allowed to retry. """


def retrying(func, env):
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

    :param callable func: The function to call, you can pass arguments
        using :func:`functools.partial`.
    :param odoo.api.Environment env: The environment where the registry
        and the cursor are taken.
    """
    try:
        for tryno in range(1, MAX_TRIES_ON_CONCURRENCY_FAILURE + 1):
            tryleft = MAX_TRIES_ON_CONCURRENCY_FAILURE - tryno
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
                env.transaction.reset()
                env.registry.reset_changes()
                if request:
                    request.session = request._get_session_and_dbname()[0]
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
                if not tryleft:
                    _logger.info("%s, maximum number of tries reached!", error)
                    raise

                wait_time = random.uniform(0.0, 2 ** tryno)
                _logger.info("%s, %s tries left, try again in %.04f sec...",
                    error, tryleft, wait_time)
                time.sleep(wait_time)
        else:
            # handled in the "if not tryleft" case
            raise RuntimeError("unreachable")  # noqa: EM101, TRY301

    except Exception:
        env.transaction.reset()
        env.registry.reset_changes()
        raise

    if not env.cr.closed:
        env.cr.commit()  # effectively commits and execute post-commits
    env.registry.signal_changes()
    return result


from .requestlib import request  # noqa: E402
