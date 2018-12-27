# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    @api.model
    def _update_product_to_produce(self, prod, qty, old_qty):
        modification = super(ChangeProductionQty, self)._update_product_to_produce(prod, qty, old_qty)
        for sub_product_line in prod.bom_id.sub_products:
            move = prod.move_finished_ids.filtered(lambda x: x.subproduct_id == sub_product_line and x.state not in ('done', 'cancel'))
            if move:
                product_uom_factor = prod.product_uom_id._compute_quantity(prod.product_qty - prod.qty_produced, prod.bom_id.product_uom_id)
                qty1 = sub_product_line.product_qty
                qty1 *= product_uom_factor / prod.bom_id.product_qty
                modification[move[0]] = (qty1, move[0].product_uom_qty)
                move[0].write({'product_uom_qty': qty1})
            else:
                move = prod._create_byproduct_move(sub_product_line)
                modification[move] = (move.product_uom_qty, 0)
        return modification
