# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_portal.controllers.main import website_account


class website_sale_stock(website_account):

    @http.route([
        '/account/orders/<int:order>',
    ], type='http', auth='user', website=True)
    def orders_followup(self, page=1, order=None, **post):
        response = super(website_sale_stock, self).orders_followup(page=page, order=order, **post)

        order_shipping_lines = {}
        for o in response.qcontext['orders']:
            shipping_lines = request.env['stock.move'].sudo().search([('picking_id', 'in', o.picking_ids.ids)])
            order_shipping_lines[o.id] = {sl.product_id.id: sl.picking_id for sl in shipping_lines}

        response.qcontext.update({
            'order_shipping_lines': order_shipping_lines,
        })
        return response
