# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class LinkTracker(http.Controller):

    @http.route('/r/<string:code>', type='http', auth='public', website=True)
    def full_url_redirect(self, code, **post):
        country_code = request.session.geoip and request.session.geoip.get('country_code') or False
        request.env['link.tracker.click'].sudo().add_click(
            code,
            ip=request.httprequest.remote_addr,
            country_code=country_code
        )
        redirect_url = request.env['link.tracker'].get_url_from_code(code)
        return request.redirect(redirect_url or '', code=301, local=False)
