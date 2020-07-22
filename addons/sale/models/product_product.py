# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _sales_count(self):
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('product_id', 'in', self.ids),
        ]
        self.update({'sales_count': 0})
        uom = self.env['product.uom']
        for group in self.env['sale.order.line'].read_group(
                domain, ['product_id', 'product_uom', 'product_uom_qty'],
                ['product_id', 'product_uom'], lazy=False):
            product = self.browse(group['product_id'][0])
            uom = uom.browse(group['product_uom'][0])
            if uom != product.uom_id:
                group['product_uom_qty'] = uom._compute_quantity(
                    group['product_uom_qty'], product.uom_id)
            product['sales_count'] += group['product_uom_qty']

    sales_count = fields.Integer(compute='_sales_count', string='# Sales')


