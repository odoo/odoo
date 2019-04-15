# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tools import float_repr
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):

    # Deprecated because override opportunities are **really** limited
    # In fact it should be removed in master ASAP
    @http.route(['/my/orders/<int:order_id>/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, access_token=None, **post):
        values = self.update_line_dict(line_id, remove, unlink, order_id, access_token, **post)
        if values:
            return [values['order_line_product_uom_qty'], values['order_amount_total']]
        return values

    @http.route(['/my/orders/<int:order_id>/update_line_dict'], type='json', auth="public", website=True)
    def update_line_dict(self, line_id, remove=False, unlink=False, order_id=None, access_token=None, **kwargs):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state not in ('draft', 'sent'):
            return False
        order_line = request.env['sale.order.line'].sudo().browse(int(line_id))
        if order_line.order_id != order_sudo:
            return False
        if unlink:
            order_line.unlink()
            return False  # return False to reload the page, the line must move back to options and the JS doesn't handle it
        number = -1 if remove else 1
        quantity = order_line.product_uom_qty + number
        if quantity < 0:
            quantity = 0
        order_line.write({'product_uom_qty': quantity})
        currency = order_sudo.currency_id

        return {
            'order_line_product_uom_qty': str(quantity),
            'order_line_price_total': float_repr(order_line.price_total, currency.decimal_places),
            'order_line_price_subtotal': float_repr(order_line.price_subtotal, currency.decimal_places),
            'order_amount_total': float_repr(order_sudo.amount_total, currency.decimal_places),
        }

    @http.route(["/my/orders/<int:order_id>/add_option/<int:option_id>"], type='http', auth="public", website=True)
    def add(self, order_id, option_id, access_token=None, **post):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        option_sudo = request.env['sale.order.option'].sudo().browse(option_id)

        if order_sudo != option_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())

        option_sudo.add_option_to_order()

        return request.redirect(option_sudo.order_id.get_portal_url(anchor='details'))
