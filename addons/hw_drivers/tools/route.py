import functools
import logging

from odoo.addons.iot_base.tools.payload_signature import verify_hmac_signature
from odoo.addons.hw_drivers.tools import helpers
from odoo.http import request
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
