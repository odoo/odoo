# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSale(WebsiteSale):

    @http.route(['/shop/pricelist'])
    def pricelist(self, promo, **post):
        order = request.website.sale_get_order()
        coupon_status = request.env['sale.coupon.apply.code'].sudo().apply_coupon(order, promo)
        if coupon_status.get('error', False):
            return super(WebsiteSale, self).pricelist(promo, **post)
        return request.redirect(post.get('r', '/shop/cart'))

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        order = request.website.sale_get_order()
        order.recompute_coupon_lines()
        return super(WebsiteSale, self).payment(**post)
