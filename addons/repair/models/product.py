# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Product(models.Model):
    _inherit = "product.product"

    def _count_returned_sn_products(self, sn_lot):
        remove_count = self.env['stock.move'].search_count([
            ('repair_line_type', 'in', ['remove', 'recycle']),
            ('product_uom_qty', '=', 1),
            ('move_line_ids.lot_id', '=', sn_lot.id),
            ('state', '=', 'done'),
            ('location_dest_usage', '=', 'internal'),
        ])
        add_count = self.env['stock.move'].search_count([
            ('repair_line_type', '=', 'add'),
            ('product_uom_qty', '=', 1),
            ('move_line_ids.lot_id', '=', sn_lot.id),
            ('state', '=', 'done'),
            ('location_dest_usage', '=', 'production'),
        ])
        return super()._count_returned_sn_products(sn_lot) + (remove_count - add_count)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    create_repair = fields.Boolean('Create Repair', help="Create a linked Repair Order on Sale Order confirmation of this product.", groups='stock.group_stock_user')

    def copy_data(self, default=None):
        default = dict(default or {})
        default['create_repair'] = (self.env.user.has_group('stock.group_stock_user') or self.env.is_superuser()) and default.get('create_repair', self.create_repair)
        return super().copy_data(default)
