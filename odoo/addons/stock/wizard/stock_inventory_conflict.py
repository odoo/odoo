# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockInventoryConflict(models.TransientModel):
    _name = 'stock.inventory.conflict'
    _description = 'Conflict in Inventory'

    quant_ids = fields.Many2many(
        'stock.quant', 'stock_conflict_quant_rel', string='Quants')
    quant_to_fix_ids = fields.Many2many(
        'stock.quant', string='Conflicts')

    def action_keep_counted_quantity(self):
        for quant in self.quant_ids:
            quant.inventory_diff_quantity = quant.inventory_quantity - quant.quantity
        return self.quant_ids.action_apply_inventory()

    def action_keep_difference(self):
        for quant in self.quant_ids:
            quant.inventory_quantity = quant.quantity + quant.inventory_diff_quantity
        return self.quant_ids.action_apply_inventory()
