# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_discount = fields.Boolean(string='Order Discounts', help='Allow the cashier to give discounts on the whole order.')
    discount_pc = fields.Float(string='Discount Percentage', help='The default discount percentage')
    discount_product_id = fields.Many2one('product.product', string='Discount Product',
        domain="[('available_in_pos', '=', True), ('sale_ok', '=', True)]", help='The product used to model the discount.')

    @api.onchange('module_pos_discount')
    def _onchange_module_pos_discount(self):
        if self.module_pos_discount:
            self.discount_product_id = self.env.ref('point_of_sale.product_product_consumable', raise_if_not_found=False)
            if not self.discount_product_id or not self.discount_product_id.available_in_pos or not self.discount_product_id.sale_ok:
                domain = [('available_in_pos', '=', True), ('sale_ok', '=', True)]
                self.discount_product_id = self.env['product.product'].search(domain, limit=1)
            self.discount_pc = 10.0
        else:
            self.discount_product_id = False
            self.discount_pc = 0.0
