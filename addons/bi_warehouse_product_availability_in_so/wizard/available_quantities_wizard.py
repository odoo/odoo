# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class AvailableQuantitiesWizard(models.TransientModel):
    _name = 'available.quantities.wizard'
    _description = 'Available Quantity Wizard'

    stock_product_id = fields.Many2one("product.product", string="Product", readonly=True)
    stock_location_id = fields.Many2many("stock.quant")

    @api.model
    def default_get(self, fields):
        res = super(AvailableQuantitiesWizard, self).default_get(fields)
        sale_order_line_id = self.env['sale.order.line'].browse(self._context.get('active_id'))
        stock_quant_id = self.env['stock.quant'].search([('product_id','=',sale_order_line_id.product_id.id),('location_id.usage','=','internal')])
        product_details = []
        for product in stock_quant_id:
            product_details.append(product.id)
        res = {
                'stock_product_id' : sale_order_line_id.product_id.id,
                'stock_location_id' : [(6,0,product_details)]
                }
        return res