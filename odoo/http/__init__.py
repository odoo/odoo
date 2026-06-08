# ruff: noqa: E402, I001, RUF067
import odoo.init  # noqa: I001

# Initialize the global `request`
import contextvars
import typing
if typing.TYPE_CHECKING:
    from .requestlib import Request
    request_var: contextvars.ContextVar[Request]
    request: Request
else:
    from werkzeug.local import LocalProxy
    request_var = contextvars.ContextVar('request')
    request = LocalProxy(request_var, unbound_message="request not bound")


from .response import Response  # noqa: I001
from . import requestlib
from .routing_map import Controller, route
# import all sub-modules
from . import dispatcher, geoip, retrying, router, server, session, stream
