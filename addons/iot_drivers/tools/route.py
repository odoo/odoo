import functools
import logging

from odoo.addons.iot_base.tools.payload_signature import verify_hmac_signature
from odoo.addons.iot_drivers.tools import helpers
from odoo.addons.iot_drivers.tools.system import IS_RPI
from odoo.http import request
from odoo import http
from werkzeug.exceptions import Forbidden

_logger = logging.getLogger(__name__)


def protect(endpoint):
    """Decorate a route to protect it with a hmac signature. If the IoT Box is not connected
    to a db, the route will not be protected.
    """
    fname = f"<function {endpoint.__module__}.{endpoint.__qualname__}>"

    @functools.wraps(endpoint)
    def protect_wrapper(*args, **kwargs):
        # If no db connected, we don't protect the endpoint
        if not helpers.get_odoo_server_url():
            return endpoint(*args, **kwargs)

        signature = request.httprequest.headers.get('Authorization')
        url = request.httprequest.url
        payload = dict(kwargs)
        if not signature or not verify_hmac_signature(url, payload, signature, helpers.get_token()):
            _logger.error('%s: Authentication failed.', fname)
            return Forbidden('Authentication failed.')

        return endpoint(*args, **kwargs)
    return protect_wrapper


def iot_route(route=None, sign=False, linux_only=False, **kwargs):
    """A wrapper for the http.route function that sets useful defaults for IoT:
      - ``auth = 'none'``
      - ``save_session = False``

    Both auth and sessions are useless on IoT since we have no DB and no users.

    :param route: The route to be decorated.
    :param sign: If ``True``, the route will be wrapped with ``@route.protect``.
    :param linux_only: If ``True``, the route will be forbidden for virtual IoT Boxes.
    """
    if 'auth' not in kwargs:
        kwargs['auth'] = 'none'
    if 'save_session' not in kwargs:
        kwargs['save_session'] = False

    http_decorator = http.route(route, **kwargs)

    def decorator(endpoint):
        if linux_only and not IS_RPI:
            return None  # Remove the route if not Linux (will return 404)
        return protect(http_decorator(endpoint)) if sign else http_decorator(endpoint)

    return decorator
