# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class Website_coupon(http.Controller):

    @http.route(['/shop/apply_coupon'], type='json', auth="public", website=True)
    def shop_apply_coupon(self, promo_code, **post):
        order = request.website.sale_get_order()
        coupon_status = request.env['sale.coupon.apply.code'].sudo().apply_coupon(order, promo_code)
        return coupon_status
