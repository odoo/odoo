# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_discount_product(self):
        return self.env.ref('point_of_sale.product_product_consumable')

    iface_discount = fields.Boolean(string='Order Discounts', help='Allow the cashier to give discounts on the whole order.')
    discount_pc = fields.Float(string='Discount Percentage', default=10, help='The default discount percentage')
    discount_product_id = fields.Many2one('product.product', string='Discount Product', domain="[('available_in_pos', '=', True)]", help='The product used to model the discount.', default=_get_default_discount_product)

    @api.onchange('module_pos_discount')
    def _onchange_module_pos_discount(self):
        if self.module_pos_discount:
            self.discount_product_id = self.env['product.product'].search([('available_in_pos', '=', True)], limit=1)
            self.discount_pc = 10.0
        else:
            self.discount_product_id = False
            self.discount_pc = 0.0
