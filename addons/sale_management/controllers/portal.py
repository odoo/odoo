# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo import http
from odoo.tools import formatLang
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):

    def _get_portal_order_details(self, order_sudo, order_line=False):
        currency = order_sudo.currency_id
        format_price = partial(formatLang, request.env, digits=currency.decimal_places)
        results = {
            'order_amount_total': format_price(order_sudo.amount_total),
            'order_amount_untaxed': format_price(order_sudo.amount_untaxed),
            'order_amount_tax': format_price(order_sudo.amount_tax),
            'order_amount_undiscounted': format_price(order_sudo.amount_undiscounted),
        }
        if order_line:
            results.update({
               'order_line_product_uom_qty': str(order_line.product_uom_qty),
               'order_line_price_total': format_price(order_line.price_total),
               'order_line_price_subtotal': format_price(order_line.price_subtotal)
            })
            try:
                results['order_totals_table'] = request.env['ir.ui.view']._render_template('sale.sale_order_portal_content_totals_table', {'sale_order': order_sudo})
            except ValueError:
                pass

        return results

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
            results = self._get_portal_order_details(order_sudo)
            results.update({
                'unlink': True,
                'sale_template': request.env['ir.ui.view']._render_template('sale.sale_order_portal_content', {
                    'sale_order': order_sudo,
                    'report_type': "html"
                }),
            })
            return results

        order_line.write({'product_uom_qty': quantity})
        results = self._get_portal_order_details(order_sudo, order_line)

        return results

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
        results = self._get_portal_order_details(order_sudo)
        results['sale_template'] = request.env['ir.ui.view']._render_template("sale.sale_order_portal_content", {
            'sale_order': option_sudo.order_id,
            'report_type': "html"
        })
        return results
