# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    schedule_count = fields.Integer('Schedules', compute='_compute_schedule_count')

    def _compute_schedule_count(self):
        grouped_data = self.env['mrp.production.schedule']._read_group(
            [('product_id', 'in', self.ids)], ['product_id'], ['__count'])
        schedule_counts = {product.id: count for product, count in grouped_data}
        for product in self:
            product.schedule_count = schedule_counts.get(product.id, 0)
