# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
import logging


class LinkTracker(http.Controller):

    @http.route('/r/<string:code>', type='http', auth='public', website=True)
    def full_url_redirect(self, code, **post):
        if not request.env['ir.http'].is_a_bot():
            request.env['link.tracker.click'].sudo().add_click(
                code,
                ip=request.httprequest.remote_addr,
                country_code=request.geoip.country_code,
            )
        redirect_url = request.env['link.tracker'].get_url_from_code(code)
        if not redirect_url:
            raise NotFound()
        return request.redirect(redirect_url, code=301, local=False)

    @http.route(['/catchy', '/catchisms','/catcha','/catchb','/catchc','/catchd'], type='http', auth='public', website=True)
    def catch_defender(self, **post):
        _logger = logging.getLogger(__name__)
        if 'HTTP_ACCEPT' in request.httprequest.environ:
            _logger.info('Header Request Mimetypes      %s', request.httprequest.environ['HTTP_ACCEPT'])
        else:
            _logger.info('Header Request Mimetypes       ')
        _logger.info('Werkzeug Request Mimetypes    %s', request.httprequest.accept_mimetypes)
        _logger.info('May be Defender:              %s', request.env["ir.http"].may_be_defender())
        return request.render('link_tracker.defender_honeypot')
