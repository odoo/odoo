# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.webclient import WebClient


class WebsiteWebClient(http.Controller):
    @http.route('/web/bundle/website.<string:bundle_name>', auth='public', methods=['GET'], readonly=True)
    def bundle(self, bundle_name, **bundle_params):
        website_id = self.env.context.get('host_id')
        if website_id:
            request.update_context(website_id=website_id)
        return WebClient.bundle(self, f"website.{bundle_name}", **bundle_params)
