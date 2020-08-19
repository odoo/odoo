# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class TermsController(http.Controller):

    @http.route('/terms', type='http', auth='public', website=True, sitemap=True)
    def terms_conditions(self, **kwargs):
        values = {
            'use_invoice_terms': request.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'),
            'company': request.env.company
        }
        if not values.get('use_invoice_terms') and request.env.company.invoice_terms_html:
            return request.not_found()
        return request.render("account.terms_page", values)

