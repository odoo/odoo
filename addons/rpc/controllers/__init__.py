from odoo.http import request

from . import json2


def _check_request():
    if request.db:
        request.env.cr.close()


from .jsonrpc import JSONRPC  # noqa: E402
from .xmlrpc import XMLRPC  # noqa: E402


class RPC(XMLRPC, JSONRPC):
    pass
