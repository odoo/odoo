# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random
import threading
import time
from collections.abc import Mapping, Sequence
from functools import partial

from psycopg2 import IntegrityError, OperationalError, errorcodes, errors

import odoo
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.models import BaseModel, check_method_name
from odoo.modules.registry import Registry
from odoo.tools import lazy

from . import security

_logger = logging.getLogger(__name__)

PG_CONCURRENCY_ERRORS_TO_RETRY = (errorcodes.LOCK_NOT_AVAILABLE, errorcodes.SERIALIZATION_FAILURE, errorcodes.DEADLOCK_DETECTED)
PG_CONCURRENCY_EXCEPTIONS_TO_RETRY = (errors.LockNotAvailable, errors.SerializationFailure, errors.DeadlockDetected)
MAX_TRIES_ON_CONCURRENCY_FAILURE = 5


class Params:
    """Representation of parameters to a function call that can be stringified for display/logging"""
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        params = [repr(arg) for arg in self.args]
        params.extend(f"{key}={value!r}" for key, value in sorted(self.kwargs.items()))
        return ', '.join(params)


def call_kw(model: BaseModel, name: str, args: list, kwargs: Mapping):
    """ Invoke the given method ``name`` on the recordset ``model``. """
    method = getattr(model, name, None)
    if not method:
        raise AttributeError(f"The method '{name}' does not exist on the model '{model._name}'")

    # get the records and context
    api = getattr(method, '_api', None)
    if api and api.startswith('model'):
        # @api.model -> no ids
        recs = model
    else:
        ids, args = args[0], args[1:]
        recs = model.browse(ids)

    # altering kwargs is a cause of errors, for instance when retrying a request
    # after a serialization error: the retry is done without context!
    kwargs = dict(kwargs)
    context = kwargs.pop('context', None) or {}
    recs = recs.with_context(context)

    # call
    _logger.debug("call %s.%s(%s)", recs, method.__name__, Params(args, kwargs))
    result = getattr(recs, name)(*args, **kwargs)

    # adapt the result
    if name == "create":
        # special case for method 'create'
        result = result.id if isinstance(args[0], Mapping) else result.ids
    elif isinstance(result, BaseModel):
        result = result.ids

    return result


def dispatch(method, params):
    db, uid, passwd = params[0], int(params[1]), params[2]
    security.check(db, uid, passwd)

    threading.current_thread().dbname = db
    threading.current_thread().uid = uid
    registry = Registry(db).check_signaling()
    try:
        if method == 'execute':
            res = execute(db, uid, *params[3:])
        elif method == 'execute_kw':
            res = execute_kw(db, uid, *params[3:])
        else:
            raise NameError(f"Method not available {method}")  # noqa: TRY301
        registry.signal_changes()
    except Exception:
        registry.reset_changes()
        raise
    return res


def execute_cr(cr, uid, obj, method, *args, **kw):
    # clean cache etc if we retry the same transaction
    cr.reset()
    env = odoo.api.Environment(cr, uid, {})
    env.transaction.default_env = env  # ensure this is the default env for the call
    recs = env.get(obj)
    if recs is None:
        raise UserError(env._("Object %s doesn't exist", obj))
    result = retrying(partial(call_kw, recs, method, args, kw), env)
    # force evaluation of lazy values before the cursor is closed, as it would
    # error afterwards if the lazy isn't already evaluated (and cached)
    for l in _traverse_containers(result, lazy):
        _0 = l._value
    return result


def execute_kw(db, uid, obj, method, args, kw=None):
    return execute(db, uid, obj, method, *args, **kw or {})


def execute(db, uid, obj, method, *args, **kw):
    # TODO could be conditionnaly readonly as in _call_kw_readonly
    with Registry(db).cursor() as cr:
        check_method_name(method)
        res = execute_cr(cr, uid, obj, method, *args, **kw)
        if res is None:
            _logger.info('The method %s of the object %s can not return `None`!', method, obj)
        return res


def retrying(func, env):
    """
    Call ``func`` until the function returns without serialisation
    error. A serialisation error occurs when two requests in independent
    cursors perform incompatible changes (such as writing different
    values on a same record). By default, it retries up to 5 times.

    :param callable func: The function to call, you can pass arguments
        using :func:`functools.partial`:.
    :param odoo.api.Environment env: The environment where the registry
        and the cursor are taken.
    """
    try:
        for tryno in range(1, MAX_TRIES_ON_CONCURRENCY_FAILURE + 1):
            tryleft = MAX_TRIES_ON_CONCURRENCY_FAILURE - tryno
            try:
                result = func()
                if not env.cr._closed:
                    env.cr.flush()  # submit the changes to the database
                break
            except (IntegrityError, OperationalError) as exc:
                if env.cr._closed:
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
                            raise RuntimeError(f"Cannot retry request on input file {filename!r} after serialization failure") from exc
                if isinstance(exc, IntegrityError):
                    model = env['base']
                    for rclass in env.registry.values():
                        if exc.diag.table_name == rclass._table:
                            model = env[rclass._name]
                            break
                    message = env._("The operation cannot be completed: %s", model._sql_error_to_message(exc))
                    raise ValidationError(message) from exc
                if not isinstance(exc, PG_CONCURRENCY_EXCEPTIONS_TO_RETRY):
                    raise
                if not tryleft:
                    _logger.info("%s, maximum number of tries reached!", errorcodes.lookup(exc.pgcode))
                    raise

                wait_time = random.uniform(0.0, 2 ** tryno)
                _logger.info("%s, %s tries left, try again in %.04f sec...", errorcodes.lookup(exc.pgcode), tryleft, wait_time)
                time.sleep(wait_time)
        else:
            # handled in the "if not tryleft" case
            raise RuntimeError("unreachable")

    except Exception:
        env.transaction.reset()
        env.registry.reset_changes()
        raise

    if not env.cr.closed:
        env.cr.commit()  # effectively commits and execute post-commits
    env.registry.signal_changes()
    return result


def _traverse_containers(val, type_):
    """ Yields atoms filtered by specified ``type_`` (or type tuple), traverses
    through standard containers (non-string mappings or sequences) *unless*
    they're selected by the type filter
    """
    from odoo.models import BaseModel
    if isinstance(val, type_):
        yield val
    elif isinstance(val, (str, bytes, BaseModel)):
        return
    elif isinstance(val, Mapping):
        for k, v in val.items():
            yield from _traverse_containers(k, type_)
            yield from _traverse_containers(v, type_)
    elif isinstance(val, Sequence):
        for v in val:
            yield from _traverse_containers(v, type_)
