# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count = fields.Float(compute='_compute_sales_count', string='Sold')

    @api.multi
    def _compute_sales_count(self):
        r = {}
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r

        date_from = fields.Datetime.to_string(fields.datetime.now() - timedelta(days=365))
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('product_id', 'in', self.ids),
            ('date', '>', date_from)
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            product.sales_count = float_round(r.get(product.id, 0), precision_rounding=product.uom_id.rounding)
        return r

    @api.multi
    def action_view_sales(self):
        action = self.env.ref('sale.report_all_channels_sales_action').read()[0]
        action['domain'] = [('product_id', 'in', self.ids)]
        action['context'] = {
            'search_default_last_year': 1,
            'pivot_measures': ['product_qty'],
            'search_default_team_id': 1
        }
        return action

    def _get_invoice_policy(self):
        return self.invoice_policy
