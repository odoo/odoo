# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.web.controllers.webclient import WebClient


class WebsiteWebClient(http.Controller):
    @http.route('/web/bundle/website.<string:bundle_name>', auth='public', methods=['GET'], website=True, readonly=True)
    def bundle(self, bundle_name, **bundle_params):
        return WebClient.bundle(self, f"website.{bundle_name}", **bundle_params)
