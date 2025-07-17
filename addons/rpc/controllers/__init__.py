import odoo.release
from odoo.http import request, route

from . import json2


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
