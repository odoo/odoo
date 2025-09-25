# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import threading
from collections.abc import Mapping, Sequence
from functools import partial

from odoo import api, http
from odoo.exceptions import (
    AccessDenied,
    UserError,
)
from odoo.models import BaseModel, get_public_method
from odoo.modules.registry import Registry
from odoo.tools import lazy

from .server import thread_local

_logger = logging.getLogger(__name__)


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
    """ Invoke the given method ``name`` on the recordset ``model``.

    Private methods cannot be called, only ones returned by `get_public_method`.
    """
    method = get_public_method(model, name)

    # get the records and context
    if getattr(method, '_api_model', False):
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
    result = method(recs, *args, **kwargs)

    # adapt the result
    if name == "create":
        # special case for method 'create'
        result = result.id if isinstance(args[0], Mapping) else result.ids
    elif isinstance(result, BaseModel):
        result = result.ids

    return result


def dispatch(method, params):
    db, uid, passwd, model, method_, *args = params
    uid = int(uid)
    if not passwd:
        raise AccessDenied
    # access checked once we open a cursor

    threading.current_thread().uid = uid
    registry = Registry(db).check_signaling()
    try:
        if method == 'execute':
            kw = {}
        elif method == 'execute_kw':
            # accept: (args, kw=None)
            if len(args) == 1:
                args += ({},)
            args, kw = args
            if kw is None:
                kw = {}
        else:
            raise NameError(f"Method not available {method}")  # noqa: TRY301
        with registry.cursor() as cr:
            api.Environment(cr, api.SUPERUSER_ID, {})['res.users']._check_uid_passwd(uid, passwd)
            res = execute_cr(cr, uid, model, method_, args, kw)
        registry.signal_changes()
    except Exception:
        registry.reset_changes()
        raise
    return res


def execute_cr(cr, uid, obj, method, args, kw):
    # clean cache etc if we retry the same transaction
    cr.reset()
    env = api.Environment(cr, uid, {})
    env.transaction.default_env = env  # ensure this is the default env for the call
    recs = env.get(obj)
    if recs is None:
        raise UserError(f"Object {obj} doesn't exist")  # pylint: disable=missing-gettext
    thread_local.rpc_model_method = f'{obj}.{method}'
    result = http.retrying(partial(call_kw, recs, method, args, kw), env)
    # force evaluation of lazy values before the cursor is closed, as it would
    # error afterwards if the lazy isn't already evaluated (and cached)
    for l in _traverse_containers(result, lazy):
        _0 = l._value
    if result is None:
        _logger.info('The method %s of the object %s cannot return `None`!', method, obj)
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
