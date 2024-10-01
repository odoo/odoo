# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import odoo

from odoo.http import JsonRPCDispatcher, serialize_exception, SessionExpiredException
from werkzeug.exceptions import NotFound, Forbidden, BadRequest


class JsonRPCDispatcherPatch(JsonRPCDispatcher):
    def handle_error(self, exc: Exception) -> collections.abc.Callable:
        """
        Monkey patch the handle_error method to add HTTP 401 Unauthorized error handling.

        :param exc: the exception that occurred.
        :returns: a WSGI application
        """
        error = {
            'code': 200,  # this code is the JSON-RPC level code, it is
            # distinct from the HTTP status code. This
            # code is ignored and the value 200 (while
            # misleading) is totally arbitrary.
            'message': "Odoo Server Error",
            'data': serialize_exception(exc),
        }
        if isinstance(exc, NotFound):
            error['code'] = 404
            error['message'] = "404: Not Found"
        elif isinstance(exc, SessionExpiredException):
            error['code'] = 100
            error['message'] = "Odoo Session Expired"
        elif isinstance(exc, Forbidden):
            error['code'] = 403
            error['message'] = "403: Forbidden"
            error['data'] = {"message": error['data']["message"]}  # only keep the message, not the traceback
        elif isinstance(exc, BadRequest):
            error['code'] = 400
            error['message'] = "400: Bad Request"
            error['data'] = {"message": error['data']["message"]}  # only keep the message, not the traceback

        return self._response(error=error)


def db_list(force=False, host=None):
    return []


odoo.http.db_list = db_list
