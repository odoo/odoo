# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.http import request


class WebsiteSaleLoyaltyDelivery(WebsiteSaleDelivery):

    @http.route()
    def update_eshop_carrier(self, **post):
        Monetary = request.env['ir.qweb.field.monetary']
        result = super().update_eshop_carrier(**post)
        order = request.website.sale_get_order()
        free_shipping_lines = None

        if order:
            order._update_programs_and_rewards()
            order.validate_taxes_on_sales_order()
            free_shipping_lines = order._get_free_shipping_lines()

        if free_shipping_lines:
            currency = order.currency_id
            if request.env.user.has_group('account.group_show_line_subtotals_tax_excluded'):
                amount_free_shipping = sum(free_shipping_lines.mapped('price_subtotal'))
            else:
                amount_free_shipping = sum(free_shipping_lines.mapped('price_total'))
            result.update({
                'new_amount_delivery_discounted': Monetary.value_to_html(order.amount_delivery + amount_free_shipping, {'display_currency': currency}),
                'new_amount_delivery_discount': Monetary.value_to_html(amount_free_shipping, {'display_currency': currency}),
                'new_amount_untaxed': Monetary.value_to_html(order.amount_untaxed, {'display_currency': currency}),
                'new_amount_tax': Monetary.value_to_html(order.amount_tax, {'display_currency': currency}),
                'new_amount_total': Monetary.value_to_html(order.amount_total, {'display_currency': currency}),
                'new_amount_order_discounted': Monetary.value_to_html(order.reward_amount - amount_free_shipping, {'display_currency': currency}),
                'new_amount_total_raw': order.amount_total,
                'delivery_discount_minor_amount': payment_utils.to_minor_currency_units(
                    amount_free_shipping, currency
                ),
            })
        return result

    @http.route()
    def cart_carrier_rate_shipment(self, carrier_id, **kw):
        Monetary = request.env['ir.qweb.field.monetary']
        order = request.website.sale_get_order(force_create=True)
        free_shipping_lines = order._get_free_shipping_lines()
        # Avoid computing carrier price delivery is free (coupon). It means if
        # the carrier has error (eg 'delivery only for Belgium') it will show
        # Free until the user clicks on it.
        if free_shipping_lines:
            return {
                'carrier_id': carrier_id,
                'status': True,
                'is_free_delivery': True,
                'new_amount_delivery': Monetary.value_to_html(0.0, {'display_currency': order.currency_id}),
                'error_message': None,
            }
        return super().cart_carrier_rate_shipment(carrier_id, **kw)
