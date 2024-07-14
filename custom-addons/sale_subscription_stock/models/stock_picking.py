# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        for move in self.move_ids:
            sale_order = move.picking_id.sale_id
            # Creates new SO line only when pickings linked to a sale order and
            # for moves with qty. done and not already linked to a SO line.
            if not sale_order or move.location_dest_id.usage != 'customer' or not move.picked:
                continue

            if sale_order.subscription_state == "7_upsell":
                # we need to compute the parent id, because it was not computed when we created the SOL in _subscription_update_line_data
                self.env.add_to_compute(self.env['sale.order.line']._fields['parent_line_id'], move.sale_line_id)
                for line in move.sale_line_id:
                    if line.parent_line_id:
                        line.parent_line_id.qty_delivered += line.qty_delivered
        return res
