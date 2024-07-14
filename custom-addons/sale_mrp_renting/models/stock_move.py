# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _should_ignore_rented_qty(self, sibling):
        return super()._should_ignore_rented_qty(sibling) or self.bom_line_id != sibling.bom_line_id

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        if self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            for sale_line in self.sale_line_id:
                if not sale_line.is_rental or 'phantom' not in sale_line.product_id.bom_ids.mapped('type'):
                    continue
                bom = self.env['mrp.bom']._bom_find(sale_line.product_id, bom_type='phantom')[sale_line.product_id]

                # To calculate qty_delivered and qty_returned, we need to consider all done moves due to the possibility of partial kits being moved
                filters = {
                    'incoming_moves': lambda m: m.location_id == m.company_id.rental_loc_id,
                    'outgoing_moves': lambda m: m.location_dest_id == m.company_id.rental_loc_id
                }
                outgoing_done_moves = sale_line.move_ids.filtered(lambda m: m.location_dest_id == m.company_id.rental_loc_id and m.state == 'done')
                incoming_done_moves = sale_line.move_ids.filtered(lambda m: m.location_id == m.company_id.rental_loc_id and m.state == 'done')
                if outgoing_done_moves:
                    amount_kits_delivered = outgoing_done_moves._compute_kit_quantities(sale_line.product_id, sale_line.product_uom_qty, bom, filters)
                    sale_line.qty_delivered = -amount_kits_delivered    # because we only use outgoing moves, it will always return a negative value
                if incoming_done_moves:
                    amount_kits_returned = incoming_done_moves._compute_kit_quantities(sale_line.product_id, sale_line.product_uom_qty, bom, filters)
                    current_qty_returned = amount_kits_returned - sale_line.qty_returned
                    if current_qty_returned and sale_line.order_id.is_late:
                        sale_line._generate_delay_line(current_qty_returned)
                    sale_line.qty_returned = amount_kits_returned
        return res
