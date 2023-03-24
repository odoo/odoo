# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockInventoryAdjustmentName(models.TransientModel):
    _name = 'stock.inventory.adjustment.name'
    _description = 'Inventory Adjustment Reference / Reason'

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_quant_ids'):
            quants = self.env['stock.quant'].browse(self.env.context['default_quant_ids'])
            res['show_info'] = any(not quant.inventory_quantity_set for quant in quants)
        return res

    quant_ids = fields.Many2many('stock.quant')
    inventory_adjustment_name = fields.Char(default="Quantity Updated")
    show_info = fields.Boolean('Show warning')

    def action_apply(self):
        quants = self.quant_ids.filtered('inventory_quantity_set')
        return quants.with_context(inventory_name=self.inventory_adjustment_name).action_apply_inventory()
