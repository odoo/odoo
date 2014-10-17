# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_sale.controllers.main import website_sale


class website_sale_stock(website_sale):

    @http.route([
        '/shop/history',
        '/shop/history/page/<int:page>',
    ], type='http', auth='user', website=True)
    def orders_followup(self, **post):
        response = super(website_sale_stock, self).orders_followup(**post)

        order_shipping_lines = {}
        for o in response.qcontext['orders']:
            shipping_lines = request.env['stock.move'].sudo().search([('picking_id', 'in', o.picking_ids.ids)])
            order_shipping_lines[o.id] = {sl.product_id.id: sl.picking_id for sl in shipping_lines}

        response.qcontext.update({
            'order_shipping_lines': order_shipping_lines,
        })
        return response