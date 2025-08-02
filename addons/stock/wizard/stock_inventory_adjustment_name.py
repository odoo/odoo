# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockInventoryAdjustmentName(models.TransientModel):
    _name = 'stock.inventory.adjustment.name'
    _description = 'Inventory Adjustment Reference / Reason'

    quant_ids = fields.Many2many('stock.quant')
    inventory_adjustment_name = fields.Char(default="Physical Inventory", string="Inventory Reason")

    def _get_quants_context(self):
        return {
            'inventory_name': self.inventory_adjustment_name,
        }

    def action_apply(self):
        quants = self.quant_ids.filtered('inventory_quantity_set')
        return quants.with_context(self._get_quants_context()).action_apply_inventory()
