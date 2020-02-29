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

    # Override
    # Add in the rendering the free_shipping_line
    def _get_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSale, self)._get_shop_payment_values(order, **kwargs)
        values['free_shipping_lines'] = order._get_free_shipping_lines()
        return values
