# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from openerp.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSale(WebsiteSale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        order = request.website.sale_get_order()
        carrier_id = post.get('carrier_id')
        if carrier_id:
            carrier_id = int(carrier_id)
        if order:
            order._check_carrier_quotation(force_carrier_id=carrier_id)
            if carrier_id:
                return request.redirect("/shop/payment")
        return super(WebsiteSale, self).payment(**post)

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        order_lines_not_delivery = [line for line in order_lines if not line.is_delivery]
        return super(WebsiteSale, self).order_lines_2_google_api(order_lines_not_delivery)
