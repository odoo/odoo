# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('bom_line_id')
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.bom_line_id and move.bom_line_id.bom_id.type == 'phantom':
                move.packaging_uom_id = move.uom_id

    def _get_cost_ratio(self, quantity):
        self.ensure_one()
        if self.bom_line_id.bom_id.type == "phantom" and self.purchase_line_id.product_id != self.product_id:
            uom_quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            if not self.product_id.uom_id.is_zero(uom_quantity):
                unit_kit_purchase = 1
                if self.purchase_line_id:
                    # A same component may be exploded by several bom lines: only the moves
                    # sharing this move's bom line and cost share carry the same demand.
                    active_moves = self.purchase_line_id.move_ids.filtered(lambda m:
                        m.state != 'cancel'
                        and m.product_id == self.product_id
                        and m.picking_id != self.picking_id
                        and m.bom_line_id == self.bom_line_id
                        and float_compare(m.cost_share, self.cost_share, precision_digits=6) == 0,
                    )
                    active_quantity = quantity + sum(
                        move.uom_id._compute_quantity(move.quantity, self.product_id.uom_id)
                        for move in active_moves
                    )
                    if active_quantity:
                        purchase_qty = self.purchase_line_id.uom_id._compute_quantity(
                            self.purchase_line_id.product_qty,
                            self.purchase_line_id.product_id.uom_id,
                        )
                        unit_kit_purchase = (quantity / active_quantity) * purchase_qty
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

    def _merge_moves_fields(self):
        res = super()._merge_moves_fields()
        if not self.env.context.get('merge_extra'):
            res['cost_share'] = sum(self.mapped('cost_share'))
        return res

    def _get_qty_received_without_self(self):
        line = self.purchase_line_id
        if line and line.qty_received_method == 'stock_moves' and line.state != 'cancel' and any(move.product_id != line.product_id for move in line.move_ids):
            kit_bom = self.env['mrp.bom']._bom_find(line.product_id, company_id=line.company_id.id, bom_type='phantom').get(line.product_id)
            if kit_bom:
                return line._compute_kit_quantities_from_moves(line.move_ids - self, kit_bom)
        return super()._get_qty_received_without_self()
