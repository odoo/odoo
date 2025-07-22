import logging

from odoo.addons.iot_drivers.tools.system import IS_RPI
from odoo import http

_logger = logging.getLogger(__name__)


def iot_route(route=None, linux_only=False, **kwargs):
    """A wrapper for the http.route function that sets useful defaults for IoT:
      - ``auth = 'none'``
      - ``save_session = False``

    Both auth and sessions are useless on IoT since we have no DB and no users.

    :param route: The route to be decorated.
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
        return http_decorator(endpoint)

    return decorator
