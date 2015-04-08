# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
# from openerp.tools.translate import _


class Website_coupon(http.Controller):

    @http.route(['/shop/apply_coupon'], type='json', auth="public", website=True)
    def shop_apply_coupon(self, promo, **post):
        order = request.website.sale_get_order()
        coupons = order.apply_coupon_reward(promo)
        return coupons
