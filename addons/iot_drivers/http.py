import collections

from werkzeug.exceptions import Forbidden

import odoo.http
from odoo.http import JsonRPCDispatcher, serialize_exception

from odoo.addons.iot_drivers.tools.system import IS_TEST


class JsonRPCDispatcherPatch(JsonRPCDispatcher):
    def prepare_error_response(self, exc: Exception) -> collections.abc.Callable:
        """Monkey patch the prepare_error_response method to add HTTP 403 Forbidden
        error handling.

        :param exc: the exception that occurred.
        :returns: a WSGI application
        """
        error = {
            "code": 200,  # this code is the JSON-RPC level code, it is
            # distinct from the HTTP status code. This
            # code is ignored and the value 200 (while
            # misleading) is totally arbitrary.
            "message": "Odoo Server Error",
            "data": serialize_exception(exc),
        }
        if isinstance(exc, Forbidden):
            error["code"] = 403
            error["message"] = "403: Forbidden"
            error["data"] = {
                "message": error["data"]["message"]
            }  # only keep the message, not the traceback

        return self._response(error=error)


if not IS_TEST:
    # Test IoT system is expected to handle Odoo database unlike "real" IoT systems.

    def get_dbs_served(self, host=None):
        return []

    odoo.http.Application.get_dbs_served = get_dbs_served
