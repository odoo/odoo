# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockInventoryAdjustmentName(models.TransientModel):
    _name = 'stock.inventory.adjustment.name'
    _description = 'Inventory Adjustment Reference / Reason'

    quant_ids = fields.Many2many('stock.quant')
    inventory_adjustment_name = fields.Char(default="Physical Inventory", string="Inventory Reason")
    counting_date = fields.Datetime(default=fields.Datetime.now, help="Date at which the resulting moves will be dated.")

    def _get_quants_context(self):
        return {
            'inventory_name': self.inventory_adjustment_name,
            'counting_date': self.counting_date,
        }

    def action_apply(self):
        quants = self.quant_ids.filtered('inventory_quantity_set')
        return quants.with_context(self._get_quants_context()).action_apply_inventory(self.counting_date)
