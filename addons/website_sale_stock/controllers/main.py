# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import UserError
from odoo.http import request


class WebsiteSale(WebsiteSale):
    def _get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist, **kw):
        """deprecated, use product method"""
        combination = request.env['product.template.attribute.value'].browse(combination)
        return request.env['product.template'].browse(int(product_template_id))._get_combination_info(combination, product_id, add_qty, pricelist)

    @http.route()
    def get_combination_info_website(self, product_template_id, product_id, combination, add_qty, **kw):
        kw['context'] = kw.get('context', {})
        kw['context'].update(website_sale_stock_get_quantity=True)
        return super(WebsiteSale, self).get_combination_info_website(product_template_id, product_id, combination, add_qty, **kw)

    @http.route()
    def payment_transaction(self, *args, **kwargs):
        """ Payment transaction override to double check cart quantities before
        placing the order
        """
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.product_id.type == 'product' and line.product_id.inventory_availability in ['always', 'threshold']:
                cart_qty = sum(order.order_line.filtered(lambda p: p.product_id.id == line.product_id.id).mapped('product_uom_qty'))
                avl_qty = line.product_id.virtual_available
                if cart_qty > avl_qty:
                    values.append(_('You ask for %s products but only %s is available') % (cart_qty, avl_qty if avl_qty > 0 else 0))
        if values:
            raise UserError('. '.join(values) + '.')
        return super(WebsiteSale, self).payment_transaction(*args, **kwargs)
