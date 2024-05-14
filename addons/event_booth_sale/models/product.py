# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('detailed_type')
    def _onchange_type_event_booth(self):
        if self.detailed_type == 'event_booth' and self.is_event_booth:
            self.invoice_policy = 'order'


class Product(models.Model):
    _inherit = 'product.product'

    is_event_booth = fields.Boolean(compute="_compute_is_event_booth")

    def _compute_is_event_booth(self):
        has_event_booth_per_product = {
            product.id: bool(count)
            for product, count in self.env['event.booth.category']._read_group(
                domain=[
                    ('booth_ids.is_available', '=', True),
                ],
                groupby=['product_id'],
                aggregates=['__count'],
            )
        }
        for product in self:
            product.is_event_booth = has_event_booth_per_product.get(product.id, False)

    @api.onchange('detailed_type')
    def _onchange_type_event_booth(self):
        if self.detailed_type == 'event_booth' and self.is_event_booth:
            self.invoice_policy = 'order'
