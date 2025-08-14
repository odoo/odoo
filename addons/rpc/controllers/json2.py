# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from typing import Any

from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    NotFound,
    UnprocessableEntity,
)

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.models import BaseModel
from odoo.service.model import get_public_method
from odoo.tools import frozendict

_logger = logging.getLogger(__name__)


class Json2RpcDispatcher(http.Dispatcher):
    routing_type = '/json/2/rpc'
    mimetypes = ('application/json',)

    @classmethod
    def is_compatible_with(cls, request):
        return request.httprequest.mimetype in cls.mimetypes

    def dispatch(self, endpoint, args):
        self.request.params = dict(args)
        if self.request.httprequest.content_length:
            try:
                self.request.params |= self.request.get_json_data()
            except ValueError as exc:
                e = f"could not parse the body as json: {exc.args[0]}"
                raise BadRequest(e) from exc
            except TypeError as exc:
                e = "could not parse the body, expecting a json object"
                raise BadRequest(e) from exc
        if self.request.db:
            result = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            result = endpoint(**self.request.params)
        if isinstance(result, http.Response):
            return result
        return self.request.make_json_response(result)

    def handle_error(self, exc: Exception) -> Callable:
        if isinstance(exc, HTTPException) and exc.response:
            return exc.response

        headers = None
        if isinstance(exc, (UserError, http.SessionExpiredException)):
            status = exc.http_status
            body = http.serialize_exception(exc)
        elif isinstance(exc, HTTPException):
            status = exc.code
            body = http.serialize_exception(
                exc,
                message=exc.description,
                arguments=(exc.description, exc.code),
            )
            # strip Content-Type but keep the remaining headers
            ct, *headers = exc.get_headers()
            assert ct == ('Content-Type', 'text/html; charset=utf-8')
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = http.serialize_exception(exc)

        return self.request.make_json_response(body, headers=headers, status=status)


class WebJson2Controller(http.Controller):
    def _web_json_2_rpc_readonly(self, rule, args):
        try:
            model_name = args['model']
            method_name = args['method']
            Model = request.registry[model_name]
        except KeyError:
            # no need of a read/write cursor to send a 404 http error
            return True
        for cls in Model.mro():
            method = getattr(cls, method_name, None)
            if method is not None and hasattr(method, '_readonly'):
                return method._readonly
        return False

    # Take over /json/<path:subpath>
    @http.route(
        ['/json/2', '/json/2/<path:subpath>'],
        auth='public',
        type='/json/2/rpc',
        readonly=True,
        methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    )
    def web_json_2_404(self, subpath=None):
        e = "Did you mean POST /json/2/<model>/<method>?"
        raise request.not_found(e)

    @http.route(
        '/json/2/<model>/<method>',
        methods=['POST'],
        auth='bearer',
        type='/json/2/rpc',
        readonly=_web_json_2_rpc_readonly,
        save_session=False,
    )
    def web_json_2_rpc(
        self,
        model: str,
        method: str,
        ids: Sequence[int] = (),
        context: Mapping[str, Any] = frozendict(),
        **kwargs,
    ):
        try:
            Model = request.env[model].with_context(context)
        except KeyError as exc:
            e = f"the model {model!r} does not exist"
            raise NotFound(e) from exc

        try:
            func = get_public_method(Model, method)
        except AttributeError as exc:
            raise NotFound(exc.args[0]) from exc
        if hasattr(func, '_api_model') and ids:
            e = f"cannot call {model}.{method} with ids"
            raise UnprocessableEntity(e)

        records = Model.browse(ids)
        signature = inspect.signature(func)
        try:
            signature.bind(records, **kwargs)
        except TypeError as exc:
            raise UnprocessableEntity(exc.args[0])

        result = func(records, **kwargs)
        if isinstance(result, BaseModel):
            result = result.ids

        return result
