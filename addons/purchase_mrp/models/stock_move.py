# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, fields
from odoo.tools.float_utils import float_is_zero, float_round
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_cost_ratio(self, quantity):
        self.ensure_one()
        if self.bom_line_id.bom_id.type == "phantom":
            uom_quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            if not self.uom_id.is_zero(uom_quantity):
                return (self.cost_share / 100) * quantity / uom_quantity
        return super()._get_cost_ratio(quantity)

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super()._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.purchase_line_id:
            vals['purchase_line_id'] = self.purchase_line_id.id
        return vals
