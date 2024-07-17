# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Product(models.Model):
    _inherit = "product.product"

    def _count_returned_sn_products(self, sn_lot):
        remove_count = self.env['repair.line'].search_count([
            ('type', '=', 'remove'),
            ('product_uom_qty', '=', 1),
            ('lot_id', '=', sn_lot.id),
            ('state', '=', 'done'),
            ('location_dest_id.usage', '=', 'internal'),
        ])
        add_count = self.env['repair.line'].search_count([
            ('type', '=', 'add'),
            ('product_uom_qty', '=', 1),
            ('lot_id', '=', sn_lot.id),
            ('state', '=', 'done'),
            ('location_dest_id.usage', '=', 'production'),
        ])
        return super()._count_returned_sn_products(sn_lot) + (remove_count - add_count)
