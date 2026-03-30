# ruff: noqa: E402, I001, RUF067
import odoo.init  # noqa: I001

# Initialize the global `request`
import typing
from werkzeug.local import LocalStack
_request_stack = LocalStack()
if typing.TYPE_CHECKING:
    from .requestlib import Request
    request: Request
else:
    request = _request_stack()


from .response import Response  # noqa: I001
from . import requestlib
from .routing_map import Controller, route
# import all sub-modules
from . import dispatcher, geoip, retrying, router, server, session, stream
