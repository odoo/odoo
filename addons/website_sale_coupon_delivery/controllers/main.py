# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.http import request


class WebsiteSaleCouponDelivery(WebsiteSaleDelivery):

    @http.route()
    def update_eshop_carrier(self, **post):
        result = super(WebsiteSaleCouponDelivery, self).update_eshop_carrier(**post)
        order = request.website.sale_get_order()
        order.recompute_coupon_lines()
        free_shipping_lines = order._get_free_shipping_lines()
        if free_shipping_lines:
            currency = order.currency_id
            amount_free_shipping = sum(free_shipping_lines.mapped('price_subtotal'))
            result.update({
                'new_amount_delivery': self._format_amount(0.0, currency),
                'new_amount_untaxed': self._format_amount(order.amount_untaxed, currency),
                'new_amount_tax': self._format_amount(order.amount_tax, currency),
                'new_amount_total': self._format_amount(order.amount_total, currency),
                'new_amount_order_discounted': self._format_amount(order.reward_amount - amount_free_shipping, currency),
            })
        return result

    @http.route()
    def cart_carrier_rate_shipment(self, carrier_id, **kw):
        order = request.website.sale_get_order(force_create=True)
        free_shipping_lines = order._get_free_shipping_lines()
        # Avoid computing carrier price delivery is free (coupon). It means if
        # the carrier has error (eg 'delivery only for Belgium') it will show
        # Free until the user clicks on it.
        if free_shipping_lines:
            return {
                'carrier_id': carrier_id,
                'status': True,
                'new_amount_delivery': 0.0,
                'error_message': None,
            }
        return super(WebsiteSaleCouponDelivery, self).cart_carrier_rate_shipment(carrier_id, **kw)
