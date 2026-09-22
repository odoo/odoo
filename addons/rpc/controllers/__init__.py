import odoo.release
from odoo.http import request, route

from . import common, doc, json2
from .xmlrpc import XMLRPC


class RPC(XMLRPC):
    @route(["/web/version", "/json/version"], type="http", auth="none", readonly=True)
    def version(self):
        return request.prepare_json_response(
            {
                "version_info": odoo.release.version_info,
                "version": odoo.release.version,
            }
        )
