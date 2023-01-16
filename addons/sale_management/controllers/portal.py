# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo import http
from odoo.tools import formatLang
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.sale.controllers import portal


class CustomerPortal(portal.CustomerPortal):

    @http.route(['/my/orders/<int:order_id>/update_line_dict'], type='json', auth="public", website=True)
    def update_line_dict(self, line_id, remove=False, unlink=False, order_id=None, access_token=None, input_quantity=False, **kwargs):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state not in ('draft', 'sent'):
            return False
        order_line = request.env['sale.order.line'].sudo().browse(int(line_id))
        if order_line.order_id != order_sudo:
            return False

        if input_quantity is not False:
            quantity = input_quantity
        else:
            number = -1 if remove else 1
            quantity = order_line.product_uom_qty + number

        if unlink or quantity <= 0:
            order_line.unlink()
            return

        order_line.write({'product_uom_qty': quantity})

    @http.route(["/my/orders/<int:order_id>/add_option/<int:option_id>"], type='json', auth="public", website=True)
    def add(self, order_id, option_id, access_token=None, **post):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        option_sudo = request.env['sale.order.option'].sudo().browse(option_id)

        if order_sudo != option_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())

        option_sudo.add_option_to_order()
