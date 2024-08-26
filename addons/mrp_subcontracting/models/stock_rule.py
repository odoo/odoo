# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals["is_subcontract"] = False
        return new_move_vals

    def _prepare_procurement_values(self, move_vals, product, old_values):
        res = super()._prepare_procurement_values(move_vals, product, old_values)
        production = self.env['mrp.production'].browse(move_vals.get('raw_material_production_id', False))
        if production and production.subcontractor_id:
            res['warehouse_id'] = self.env['stock.picking.type'].browse(move_vals['picking_type_id']).warehouse_id.id
        return res
