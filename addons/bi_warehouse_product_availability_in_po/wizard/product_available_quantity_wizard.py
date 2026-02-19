# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class ProductAvailableQuantityWizard(models.TransientModel):
    _name = "product.available.quantity.wizard"
    _description = "Product Available Quantity Wizard"

    stock_quant_ids = fields.Many2many('stock.quant')
    product_product_id = fields.Many2one('product.product', string='Product Name')

 

    def default_get(self, fields):
        product_list = []
        active_id = self._context.get('active_ids')
        purchase_order_obj = self.env['purchase.order']
        purchase_line_ids = purchase_order_obj.order_line.browse(active_id)
        stock_quant_obj = self.env['stock.quant']
        stock_quant_search_ids = stock_quant_obj.search([('product_id', '=', purchase_line_ids.product_id.id),
                                                          ('location_id.usage', '=', 'internal')])
        for record in stock_quant_search_ids:
            product_list.append(record.id)

        return {
            'product_product_id': purchase_line_ids.product_id.id,
            'stock_quant_ids': [(6, 0, product_list)]
        }
