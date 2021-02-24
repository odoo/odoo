# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockInventoryConflict(models.TransientModel):
    _name = 'stock.inventory.conflict'
    _description = 'Conflict in Inventory'

    quant_ids = fields.Many2many(
        'stock.quant', 'stock_conflict_quant_rel', string='Quants')
    quant_to_fix_ids = fields.Many2many(
        'stock.quant', string='Conflicts')

    def action_validate(self):
        for conflict in self:
            quant_to_fix_ids = conflict.quant_to_fix_ids.filtered(
                lambda q: q.quantity != (q.inventory_quantity - q.inventory_diff_quantity))
            if quant_to_fix_ids:
                if self.user_has_groups('stock.group_stock_multi_locations'):
                    message = '\n'.join([_('%s at location %s', q.product_id.display_name, q.location_id.display_name) for q in quant_to_fix_ids])
                else:
                    message = '\n'.join([_('%s', q.product_id.display_name) for q in quant_to_fix_ids])
                raise UserError(
                    _('You still have conflicts to resolve:\n') + message)
            conflict.quant_ids.action_apply_inventory()
