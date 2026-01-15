import odoo.release
from odoo.http import request, route

from . import json2

RPC_DEPRECATION_NOTICE = """\
The /xmlrpc, /xmlrpc/2 and /jsonrpc endpoints are deprecated in Odoo 19 \
and scheduled for removal in Odoo 20. Please report the problem to the \
client making the request.
Mute this logger: --log-handler %s:ERROR
https://www.odoo.com/documentation/latest/developer/reference/external_api.html#migrating-from-xml-rpc-json-rpc"""


def _check_request():
    if request.db:
        request.env.cr.close()


from .jsonrpc import JSONRPC  # noqa: E402
from .xmlrpc import XMLRPC  # noqa: E402


class RPC(XMLRPC, JSONRPC):
    @route(['/web/version', '/json/version'], type='http', auth='none', readonly=True)
    def version(self):
        return request.make_json_response({
            'version_info': odoo.release.version_info,
            'version': odoo.release.version,
        })
