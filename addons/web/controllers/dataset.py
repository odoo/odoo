# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections.abc import Mapping
from typing import Any

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.models import BaseModel, get_public_method
from odoo.server import thread_local

from .utils import clean_action

_logger = logging.getLogger(__name__)


def call_kw(model: BaseModel, name: str, args: list, kwargs: Mapping):
    """ Invoke the given method ``name`` on the recordset ``model``.

    Private methods cannot be called, only ones returned by `get_public_method`.
    """
    method = get_public_method(model, name)

    # Extract the record ids and context from the args and kwargs (relic of OpenERP...)
    if getattr(method, '_api_model', False):
        records = model
    else:
        ids, args = args[0], args[1:]
        records = model.browse(ids)
    kwargs = dict(kwargs)  # keep the original dict intact (for retrying)
    context = kwargs.pop('context', None) or {}
    records = records.with_context(context)

    # Log the call with its arguments in debug
    if _logger.isEnabledFor(logging.DEBUG):
        args_ = ', '.join(map(repr, args))
        kwargs_ = ', '.join(f'{key}={value!r}' for key, value in kwargs.items())
        params = f'{args_}, {kwargs_}' if args_ and kwargs_ else (args_ + kwargs_)
        _logger.debug("call %s.%s(%s)", records, method.__name__, params)

    # Call the method
    result = method(records, *args, **kwargs)

    # Convert records to a list of ids, or a single id for single create
    if name == "create":
        result = result.id if isinstance(args[0], Mapping) else result.ids
    elif isinstance(result, BaseModel):
        result = result.ids

    return result


class DataSet(http.Controller):

    def _call_kw_readonly(self, rule, args):
        params = request.get_json_data()['params']
        try:
            model_class = request.registry[params['model']]
        except KeyError as e:
            raise NotFound() from e
        method_name = params['method']
        for cls in model_class.mro():
            method = getattr(cls, method_name, None)
            if method is not None and hasattr(method, '_readonly'):
                return method._readonly
        return False

    @http.route(['/web/dataset/call_kw', '/web/dataset/call_kw/<path:path>'], type='jsonrpc', auth="user", readonly=_call_kw_readonly)
    def call_kw(self, model: str, method: str, args: list, kwargs: dict, path: str | None = None) -> Any:
        if path != f'{model}.{method}':
            thread_local.rpc_model_method = f'{model}.{method}'
        return call_kw(request.env[model], method, args, kwargs)

    @http.route(['/web/dataset/call_button', '/web/dataset/call_button/<path:path>'], type='jsonrpc', auth="user", readonly=_call_kw_readonly)
    def call_button(self, model, method, args, kwargs, path=None):
        if path != f'{model}.{method}':
            thread_local.rpc_model_method = f'{model}.{method}'
        action = call_kw(request.env[model], method, args, kwargs)
        if isinstance(action, dict) and action.get('type') != '':  # noqa: PLC1901
            return clean_action(action, env=request.env)
        return False
