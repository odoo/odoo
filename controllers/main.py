# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSale(WebsiteSale):

    @http.route(['/shop/pricelist'])
    def pricelist(self, promo, **post):
        order = request.website.sale_get_order()
        coupon_status = request.env['sale.coupon.apply.code'].sudo().apply_coupon(order, promo)
        if coupon_status.get('not_found'):
            return super(WebsiteSale, self).pricelist(promo, **post)
        elif coupon_status.get('error'):
            request.session['error_promo_code'] = coupon_status['error']
        return request.redirect(post.get('r', '/shop/cart'))

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        order = request.website.sale_get_order()
        order.recompute_coupon_lines()
        return super(WebsiteSale, self).payment(**post)

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        order.recompute_coupon_lines()
        return super(WebsiteSale, self).cart(**post)

    def _update_website_sale_coupon(self, **post):
        order = request.website.sale_get_order()
        order.recompute_coupon_lines()
        free_shipping_lines = order._get_free_shipping_lines()
        currency = order.currency_id
        result = {}
        if free_shipping_lines:
            amount_free_shipping = sum(free_shipping_lines.mapped('price_subtotal'))
            result.update({
                'new_amount_delivery': self._format_amount(0.0, currency),
                'new_amount_untaxed': self._format_amount(order.amount_untaxed, currency),
                'new_amount_tax': self._format_amount(order.amount_tax, currency),
                'new_amount_total': self._format_amount(order.amount_total, currency),
                'new_amount_order_discounted': self._format_amount(order.reward_amount - amount_free_shipping, currency)
            })
        return result

    # Override
    # Add in the rendering the free_shipping_line
    def _get_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSale, self)._get_shop_payment_values(order, **kwargs)
        values['free_shipping_lines'] = order._get_free_shipping_lines()
        return values
