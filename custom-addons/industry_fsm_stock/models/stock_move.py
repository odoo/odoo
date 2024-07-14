# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_is_zero
from collections import defaultdict


class StockMove(models.Model):
    _inherit = ['stock.move']

    def _update_reserved_quantity(self, need, location_id, quant_ids=None, lot_id=None, package_id=None, owner_id=None, strict=True):
        if self.product_id.tracking == 'none':
            return super()._update_reserved_quantity(need, location_id, quant_ids=quant_ids, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        lot = self.sale_line_id.sudo().fsm_lot_id or lot_id
        if lot and self.product_id.tracking != "serial":
            return super()._update_reserved_quantity(need, location_id, quant_ids=quant_ids, lot_id=lot, package_id=package_id, owner_id=owner_id, strict=strict)

        so_lines_with_fsm_lot = self.group_id.stock_move_ids.sale_line_id.sudo().filtered(lambda l: l.product_id == self.product_id and l.fsm_lot_id)
        if not so_lines_with_fsm_lot:
            return super()._update_reserved_quantity(need, location_id, quant_ids=quant_ids, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)

        already_used_by_lots = defaultdict(float)
        for ml in self.move_dest_ids.move_orig_ids.move_line_ids:
            qty = ml.quantity
            qty = ml.product_uom_id._compute_quantity(qty, ml.product_id.uom_id)
            already_used_by_lots[ml.lot_id] += qty

        reserved = 0
        for so_line in so_lines_with_fsm_lot:
            if float_is_zero(need, precision_rounding=self.product_id.uom_id.rounding):
                return reserved
            lot = so_line.fsm_lot_id
            sol_qty = so_line.product_uom._compute_quantity(so_line.product_uom_qty, so_line.product_id.uom_id)
            lot_need = max(0, sol_qty - already_used_by_lots[lot])
            lot_need = min(need, lot_need)
            taken = super()._update_reserved_quantity(lot_need, location_id, quant_ids=quant_ids, lot_id=lot, package_id=package_id, owner_id=owner_id, strict=strict)
            need -= taken
            reserved += taken

        if float_is_zero(need, precision_rounding=self.product_id.uom_id.rounding):
            return reserved

        reserved += super()._update_reserved_quantity(need, location_id, quant_ids=quant_ids, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        return reserved
