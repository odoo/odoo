# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import odoo.http

from odoo.http import JsonRPCDispatcher, serialize_exception
from odoo.addons.iot_drivers.tools.system import IS_TEST
from werkzeug.exceptions import Forbidden


class JsonRPCDispatcherPatch(JsonRPCDispatcher):
    def handle_error(self, exc: Exception) -> collections.abc.Callable:
        """Monkey patch the handle_error method to add HTTP 403 Forbidden
        error handling.

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
        if isinstance(exc, Forbidden):
            error['code'] = 403
            error['message'] = "403: Forbidden"
            error['data'] = {"message": error['data']["message"]}  # only keep the message, not the traceback

        return self._response(error=error)


if not IS_TEST:
    # Test IoT system is expected to handle Odoo database unlike "real" IoT systems.

    def db_list(force=False, host=None):
        return []

    odoo.http.db_list = db_list
