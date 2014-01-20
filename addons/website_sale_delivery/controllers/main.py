# -*- coding: utf-8 -*-
from openerp.addons.website_sale.controllers.main import Ecommerce
from openerp.addons.web.http import request
from openerp.addons.website.models import website


class Ecommerce(Ecommerce):

    @website.route(['/shop/payment/'], type='http', auth="public", multilang=True)
    def payment(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        order = self.get_order()

        carrier_id = post.get('carrier_id')
        if order and carrier_id:
            # recompute delivery costs
            SaleOrder = request.registry['sale.order']
            SaleOrder.write(cr, uid, [order.id], {'carrier_id': carrier_id}, context=context)
            SaleOrder.delivery_set(cr, uid, [order.id], context=context)

        res = super(Ecommerce, self).payment(**post)
        return res
