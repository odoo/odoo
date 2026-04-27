# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request


class TermsController(http.Controller):

    def sitemap_sign_terms(env, rule, qs):
        use_sign_terms = env['ir.config_parameter'].sudo().get_param('sign.use_sign_terms')
        if not (use_sign_terms and env.company.sign_terms_type == 'html'):
            return False

        if not qs or qs.lower() in '/sign/terms':
            yield {'loc': '/sign/terms'}

    @http.route('/sign/terms', type='http', auth='public', website=True, sitemap=sitemap_sign_terms)
    def terms_conditions(self, **kwargs):
        use_sign_terms = request.env['ir.config_parameter'].sudo().get_param('sign.use_sign_terms')
        if not (use_sign_terms and request.env.company.sign_terms_type == 'html'):
            return request.render('http_routing.http_error', {
                'status_code': _('Oops'),
                'status_message': _("""The requested page is invalid, or doesn't exist anymore.""")})
        values = {
            'use_sign_terms': use_sign_terms,
            'company': request.env.company
        }
        return request.render("sign.sign_terms_conditions_page", values)
