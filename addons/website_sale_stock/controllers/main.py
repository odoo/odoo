# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request
from openerp.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleStock(WebsiteSale):

    @http.route([
        '/shop/orders',
        '/shop/orders/page/<int:page>',
    ], type='http', auth='user', website=True)
    def orders_followup(self, page=1, **post):
        response = super(WebsiteSaleStock, self).orders_followup(**post)

        order_shipping_lines = {}
        for o in response.qcontext['orders']:
            shipping_lines = request.env['stock.move'].sudo().search([('picking_id', 'in', o.picking_ids.ids)])
            order_shipping_lines[o.id] = {sl.product_id.id: sl.picking_id for sl in shipping_lines}

        response.qcontext.update({
            'order_shipping_lines': order_shipping_lines,
        })
        return response
