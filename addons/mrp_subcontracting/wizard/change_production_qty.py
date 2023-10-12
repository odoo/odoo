# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    @api.model
    def _need_quantity_propagation(self, move, qty):
        res = super()._need_quantity_propagation(move, qty)
        return res and not any(m.is_subcontract for m in move.move_dest_ids)

    @api.model
    def _update_product_qty(self, move, qty):
        res = super()._update_product_qty(move, qty)
        subcontract_moves = move.move_dest_ids.filtered(lambda m: m.is_subcontract)
        if subcontract_moves:
            subcontract_moves[0].with_context(cancel_backorder=False).write({'product_uom_qty': subcontract_moves[0].product_uom_qty + qty})

        return res
