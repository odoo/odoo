# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections.abc
import contextlib
import functools
import inspect

import odoo.api
from odoo.exceptions import AccessError
from odoo.http import DEFAULT_LANG
from odoo.service.model import retrying
from .exceptions import RpcError, RpcErrorCode

def dispatch(registry, uid, model, method_name, *params):
    record_ids, context, args, kwargs = extract_call_info(params)
    with contextlib.closing(registry.cursor()) as cr:
        env = odoo.api.Environment(cr, uid, context)
        method = bind_method(env, model, record_ids, context, method_name, args, kwargs)
        return retrying(method, env)

def extract_call_info(params):
    params = params or [{}]

    if (len(params) > 1
     or not isinstance(params[0], collections.abc.Mapping)
     or not {'records', 'context', 'args', 'kwargs'}.issuperset(params[0].keys())):
        raise RpcError(RpcErrorCode.invalid_params) from TypeError(
            "the RPC2 endpoint takes a single parameter: a dict with "
            "records, context, args and kwargs (all optional) keys")

    return (
        params[0].get('records', []),
        {'lang': DEFAULT_LANG, **params[0].get('context', {})},
        params[0].get('args', []),
        params[0].get('kwargs', {}),
    )

def bind_method(env, model, record_ids, context, method_name, args, kwargs):
    if method_name.startswith('_'):
        raise AccessError(f"{method_name!r} is a private method and can not be called over RPC")
    try:
        records = env[model].browse(record_ids).with_context(context)
    except KeyError as exc1:
        exc2 = NameError(f"no model {model!r} found")
        exc2.__cause__ = exc1
        raise RpcError(RpcErrorCode.method_not_found) from exc2
    try:
        method = getattr(records, method_name)
    except AttributeError as exc1:
        exc2 = NameError(f"no method {method_name!r} found on model {model!r}")
        exc2.__cause__ = exc1
        raise RpcError(RpcErrorCode.method_not_found) from exc2
    try:
        inspect.signature(method).bind(*args, **kwargs)
    except TypeError as exc:
        raise RpcError(RpcErrorCode.invalid_params) from exc

    return functools.partial(method, *args, **kwargs)
