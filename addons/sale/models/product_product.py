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
        sale_order_lines = self.env['sale.order.line'].search(domain)
        for product in self:
            product.sales_count = len(sale_order_lines.filtered(lambda r: r.product_id == product).mapped('order_id'))

    sales_count = fields.Integer(compute='_sales_count', string='# Sales')

    def _get_invoice_policy(self):
        return self.invoice_policy
