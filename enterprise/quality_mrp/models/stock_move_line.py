# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def write(self, vals):
        res = super().write(vals)
        if vals.get('lot_id') and self.sudo().check_ids:
            self.check_ids.filtered(lambda qc: qc.test_type in ('register_consumed_materials', 'register_byproducts')).lot_id = vals['lot_id']
        return res

    def _get_check_values(self, quality_point):
        vals = super(StockMoveLine, self)._get_check_values(quality_point)
        vals.update({'production_id': self.move_id.production_id.id or self.move_id.raw_material_production_id.id})
        return vals

    def _get_quality_points_all_products(self, quality_points_by_product_picking_type):
        if self.move_id.raw_material_production_id:
            return set()
        else:
            return super()._get_quality_points_all_products(quality_points_by_product_picking_type)

    def _create_quality_check_at_write(self, vals):
        if self.move_id.production_id or self.move_id.raw_material_production_id:
            return False
        return super()._create_quality_check_at_write(vals)

    def _filter_move_lines_applicable_for_quality_check(self):
        production_lines = self.filtered(lambda sml: sml.move_id.raw_material_production_id or sml.product_id == sml.move_id.production_id.product_id)
        return super(StockMoveLine, self - production_lines)._filter_move_lines_applicable_for_quality_check()

    def _sorting_move_lines(self):
        self.ensure_one()
        fail_sort = self.check_state == 'fail'
        # `check_ids` are sorted by their existence and then by their ID
        check_ids_sort = self.check_ids and self.check_ids.id or 0
        return (not fail_sort, not bool(check_ids_sort), check_ids_sort, self.id)
