# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):

    @http.route(["/quotation/template/<model('sale.quote.template'):quote>"], type='http', auth="user", website=True)
    def template_view(self, quote, **post):
        values = {'template': quote}
        return request.render('sale_design.so_template', values)

    def _compute_vals_for_add_line(self, Order, Option):
        vals = super(CustomerPortal, self)._compute_vals_for_add_line(Order, Option)
        vals.update(website_description=Option.website_description)
        return vals
