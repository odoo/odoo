# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockInventoryAdjustmentName(models.TransientModel):
    _name = 'stock.inventory.adjustment.name'
    _description = 'Inventory Adjustment Name'

    def _default_inventory_adjustment_name(self):
        return _("Inventory Adjustment") + " - " + fields.Date.to_string(fields.Date.today())

    quant_ids = fields.Many2many('stock.quant')
    inventory_adjustment_name = fields.Char(default=_default_inventory_adjustment_name)

    def action_apply(self):
        return self.quant_ids.with_context(
            inventory_name=self.inventory_adjustment_name).action_apply_inventory()
