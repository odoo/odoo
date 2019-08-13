# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_discount_product_id(self):
        discount_product_id = self.env['product.product'].search([('name', '=', 'Discount')], limit = 1)
        if not discount_product_id:
            discount_product_id = self.env['product.product'].create({
                'sale_ok': False,
                'purchase_ok': False,
                'name': 'Discount',
                'default_code': 'DISC',
                'list_price': 0.0,
                'type': 'consu',
                'to_weight': False,
                'taxes_id': [],
                })
        return discount_product_id

    iface_discount = fields.Boolean(string='Order Discounts', help='Allow the cashier to give discounts on the whole order.')
    discount_pc = fields.Float(string='Discount Percentage', help='The default discount percentage', default=10.0)
    discount_product_id = fields.Many2one('product.product', string='Discount Product',
        domain="[('purchase_ok', '=', False), ('sale_ok', '=', False), ('taxes_id', '=', False)]", 
        help='The product used to model the discount.', default=_default_discount_product_id)

    @api.onchange('module_pos_discount')
    def _onchange_module_pos_discount(self):
        if self.module_pos_discount and not self.discount_product_id:
            self.discount_product_id = self._default_discount_product_id()
