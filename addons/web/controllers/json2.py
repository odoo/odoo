# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from typing import Any

from werkzeug.exceptions import (
    HTTPException,
    BadRequest, NotFound, MethodNotAllowed, UnprocessableEntity,
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

    @classmethod
    def is_compatible_with(cls, request):
        return request.httprequest.mimetype == 'application/json'

    def dispatch(self, endpoint, args):
        self.request.params = dict(args)
        if self.request.httprequest.content_length:
            try:
                self.request.params |= self.request.get_json_data()
            except ValueError as exc:
                raise BadRequest(f"could not parse the body as json: {exc.args[0]}") from exc
            except TypeError as exc:
                raise BadRequest("could not parse the body, expecting a json object") from exc
        if self.request.db:
            result = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            result = endpoint(**self.request.params)
        if isinstance(result, http.Response):
            return result
        return self.request.make_json_response(result)

    def handle_error(self, exc: Exception) -> Callable:
        headers = None
        cookies = None
        if isinstance(exc, UserError):
            msg = exc.args[0]
            status = exc.http_code
        elif isinstance(exc, HTTPException):
            if res := exc.response:
                ct = res.headers.get('Content-Type', 'application/octet-stream')
                if 'json' in ct or not ct.startswith('text/'):
                    return exc
                msg = res.get_data(as_text=True)
                status = exc.code
                headers = res.headers
            else:
                msg = exc.description
                status = exc.code
        elif isinstance(exc, http.SessionExpiredException):
            # needed by auth='user' but not by auth='bearer'
            msg = (
                "Session Expired\n\n"
                "Surely this is because you are using a session_id "
                "cookie but that session does no longer exists.\n"
                "Either GET and POST the html form at /web/login?db=\n"
                "Either POST using JSONRPC your credentials to "
                "/web/session/authenticate with method 'call' and "
                "params 'db', 'login', and 'password'.\n"
                "In either case, your session_id cookie will be "
                "updated."
            )
            status = HTTPStatus.FORBIDDEN
        else:
            msg = "internal server error"
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return self.request.make_json_response(msg, headers, cookies, status)


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

    @http.route(
        '/json/2/<model>/<method>',
        #methods=['POST'],  # must accept all methods, otherwise /json/<path:subpath> takes over
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
        args: Sequence[Any] = (),
        kwargs: Mapping[str, Any] = frozendict(),
        context: Mapping[str, Any] = frozendict(),
    ):
        if request.httprequest.method != 'POST':
            raise MethodNotAllowed()

        try:
            Model = request.env[model]
        except KeyError as exc:
            raise NotFound(f"the model {model!r} does not exist") from exc
        records = Model.with_context(context).browse(ids)
        try:
            func = get_public_method(records, method)
        except AttributeError as exc:
            raise NotFound(exc.args[0]) from exc
        signature = inspect.signature(func)
        try:
            signature.bind(records, *args, **kwargs)
        except TypeError as exc:
            raise UnprocessableEntity(exc.args[0])

        result = func(records, *args, **kwargs)
        if isinstance(result, BaseModel):
            result = result.ids

        return result
