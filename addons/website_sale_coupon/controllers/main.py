# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.website_sale.controllers import main
from odoo.exceptions import UserError
from odoo.http import request

from werkzeug.urls import url_encode, url_parse


class WebsiteSale(main.WebsiteSale):

    @http.route(['/shop/pricelist'])
    def pricelist(self, promo, **post):
        order = request.website.sale_get_order()
        coupon_status = request.env['sale.coupon.apply.code'].sudo().apply_coupon(order, promo)
        if coupon_status.get('not_found'):
            return super(WebsiteSale, self).pricelist(promo, **post)
        elif coupon_status.get('error'):
            request.session['error_promo_code'] = coupon_status['error']
        return request.redirect(post.get('r', '/shop/cart'))

    @http.route()
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        order.recompute_coupon_lines()
        return super(WebsiteSale, self).shop_payment(**post)

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        order.recompute_coupon_lines()
        return super(WebsiteSale, self).cart(**post)

    @http.route(['/coupon/<string:code>'], type='http', auth='public', website=True, sitemap=False)
    def activate_coupon(self, code, r='/shop', **kw):
        url_parts = url_parse(r)
        url_query = url_parts.decode_query()
        url_query.pop('coupon_error', False)  # trust only Odoo error message

        request.session['pending_coupon_code'] = code
        order = request.website.sale_get_order()
        if order:
            result = order._try_pending_coupon()
            order.recompute_coupon_lines()
            if isinstance(result, UserError):
                url_query['coupon_error'] = result
            else:
                url_query['notify_coupon'] = code
        else:
            url_query['coupon_error'] = _("The coupon will be automatically applied when you add something in your cart.")
        redirect = url_parts.replace(query=url_encode(url_query))
        return request.redirect(redirect.to_url())

    # Override
    # Add in the rendering the free_shipping_line
    def _get_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSale, self)._get_shop_payment_values(order, **kwargs)
        values['free_shipping_lines'] = order._get_free_shipping_lines()
        return values
