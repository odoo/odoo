# -*- coding: utf-8 -*-
import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID

class website_sale(openerp.addons.website_sale.controllers.main.website_sale):

    @http.route(['/shop/payment/'], type='http', auth="public", website=True, multilang=True)
    def payment(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        order = self.get_order()
        carrier_id = post.get('carrier_id')

        if order and carrier_id:
            # recompute delivery costs            
            request.registry['website']._check_carrier_quotation(cr,uid,order,carrier_id,context=context)
            return request.redirect("/shop/payment/")

        res = super(website_sale, self).payment(**post)
        return res
