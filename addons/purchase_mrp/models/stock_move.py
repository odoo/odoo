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
                unit_kit_purchase = 1
                if self.purchase_line_id:
                    active_moves = self.purchase_line_id.move_ids.filtered(lambda m:
                        m.state != 'cancel' and m.product_id == self.product_id and m.picking_id != self.picking_id,
                    )
                    active_quantity = quantity + sum(active_moves.mapped('quantity'))
                    if active_quantity:
                        unit_kit_purchase = (quantity / active_quantity) * self.purchase_line_id.product_qty
                return (self.cost_share / 100) * (quantity / uom_quantity) * unit_kit_purchase
        return super()._get_cost_ratio(quantity)

    def _get_value_from_bill(self, aml):
        value = super()._get_value_from_bill(aml)
        if self.bom_line_id.bom_id.type == "phantom":
            value *= (self.cost_share / 100)
        return value

    def _get_quantity_from_bill(self, aml, quantity):
        self.ensure_one()
        if self.bom_line_id.bom_id.type == "phantom":
            return aml.product_uom_id._compute_quantity(quantity, self.product_id.uom_id)
        return super()._get_quantity_from_bill(aml, quantity)

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super()._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.purchase_line_id:
            vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _get_qty_received_without_self(self):
        line = self.purchase_line_id
        if line and line.qty_received_method == 'stock_moves' and line.state != 'cancel' and any(move.product_id != line.product_id for move in line.move_ids):
            kit_bom = self.env['mrp.bom']._bom_find(line.product_id, company_id=line.company_id.id, bom_type='phantom').get(line.product_id)
            if kit_bom:
                return line._compute_kit_quantities_from_moves(line.move_ids - self, kit_bom)
        return super()._get_qty_received_without_self()
