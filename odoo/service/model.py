# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random
import threading
import time
from collections.abc import Mapping, Sequence
from functools import partial

from psycopg2 import IntegrityError, OperationalError, errorcodes

import odoo
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.models import check_method_name
from odoo.tools import DotDict
from odoo.tools.translate import _, translate_sql_constraint
from . import security
from ..tools import lazy

_logger = logging.getLogger(__name__)

PG_CONCURRENCY_ERRORS_TO_RETRY = (errorcodes.LOCK_NOT_AVAILABLE, errorcodes.SERIALIZATION_FAILURE, errorcodes.DEADLOCK_DETECTED)
MAX_TRIES_ON_CONCURRENCY_FAILURE = 5


def dispatch(method, params):
    db, uid, passwd = params[0], int(params[1]), params[2]
    security.check(db, uid, passwd)

    threading.current_thread().dbname = db
    threading.current_thread().uid = uid
    registry = odoo.registry(db).check_signaling()
    with registry.manage_changes():
        if method == 'execute':
            res = execute(db, uid, *params[3:])
        elif method == 'execute_kw':
            res = execute_kw(db, uid, *params[3:])
        else:
            raise NameError("Method not available %s" % method)
    return res


def execute_cr(cr, uid, obj, method, *args, **kw):
    # clean cache etc if we retry the same transaction
    cr.reset()
    env = odoo.api.Environment(cr, uid, {})
    recs = env.get(obj)
    if recs is None:
        raise UserError(_("Object %s doesn't exist", obj))
    result = retrying(partial(odoo.api.call_kw, recs, method, args, kw), env)
    # force evaluation of lazy values before the cursor is closed, as it would
    # error afterwards if the lazy isn't already evaluated (and cached)
    for l in _traverse_containers(result, lazy):
        _0 = l._value
    return result


def execute_kw(db, uid, obj, method, args, kw=None):
    return execute(db, uid, obj, method, *args, **kw or {})


def execute(db, uid, obj, method, *args, **kw):
    with odoo.registry(db).cursor() as cr:
        check_method_name(method)
        res = execute_cr(cr, uid, obj, method, *args, **kw)
        if res is None:
            _logger.info('The method %s of the object %s can not return `None` !', method, obj)
        return res


def _as_validation_error(env, exc):
    """ Return the IntegrityError encapsuled in a nice ValidationError """

    unknown = _('Unknown')
    for _name, rclass in env.registry.items():
        if exc.diag.table_name == rclass._table:
            model = rclass
            field = model._fields.get(exc.diag.column_name)
            break
    else:
        model = DotDict({'_name': unknown.lower(), '_description': unknown})
        field = DotDict({'name': unknown.lower(), 'string': unknown})

    if exc.pgcode == errorcodes.NOT_NULL_VIOLATION:
        return ValidationError(_(
            "The operation cannot be completed:\n"
            "- Create/update: a mandatory field is not set.\n"
            "- Delete: another model requires the record being deleted."
            " If possible, archive it instead.\n\n"
            "Model: %(model_name)s (%(model_tech_name)s)\n"
            "Field: %(field_name)s (%(field_tech_name)s)\n",
            model_name=model._description,
            model_tech_name=model._name,
            field_name=field.string,
            field_tech_name=field.name,
        ))

    if exc.pgcode == errorcodes.FOREIGN_KEY_VIOLATION:
        return ValidationError(_(
            "The operation cannot be completed: another model requires "
            "the record being deleted. If possible, archive it instead.\n\n"
            "Model: %(model_name)s (%(model_tech_name)s)\n"
            "Constraint: %(constraint)s\n",
            model_name=model._description,
            model_tech_name=model._name,
            constraint=exc.diag.constraint_name,
        ))

    if exc.diag.constraint_name in env.registry._sql_constraints:
        return ValidationError(_(
            "The operation cannot be completed: %s",
            translate_sql_constraint(env.cr, exc.diag.constraint_name, env.context['lang'])
        ))

    return ValidationError(_("The operation cannot be completed: %s", exc.args[0]))


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
                env.registry.reset_changes()
                if request:
                    request.session = request._get_session_and_dbname()[0]
                if isinstance(exc, IntegrityError):
                    raise _as_validation_error(env, exc) from exc
                if exc.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
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
