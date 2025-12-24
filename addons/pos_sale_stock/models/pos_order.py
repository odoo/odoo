# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def sync_from_ui(self, orders):
        data = super().sync_from_ui(orders)
        pos_orders = self.browse([o['id'] for o in data["pos.order"]])
        for pos_order in pos_orders:
            # Confirm the unconfirmed sale orders that are linked to the sale order lines.
            so_lines = pos_order.lines.mapped('sale_order_line_id')

            # update the demand qty in the stock moves related to the sale order line
            # flush the qty_delivered to make sure the updated qty_delivered is used when
            # updating the demand value
            so_lines.flush_recordset(['qty_delivered'])
            # track the waiting pickings
            waiting_picking_ids = set()
            for so_line in so_lines:
                so_line_stock_move_ids = so_line.move_ids.reference_ids.move_ids
                for stock_move in so_line.move_ids:
                    picking = stock_move.picking_id
                    if not picking.state in ['waiting', 'confirmed', 'assigned']:
                        continue

                    def get_expected_qty_to_ship_later():
                        pos_pickings = so_line.pos_order_line_ids.order_id.picking_ids
                        if pos_pickings and all(pos_picking.state in ['confirmed', 'assigned'] for pos_picking in pos_pickings):
                            return sum((so_line._convert_qty(so_line, pos_line.qty, 'p2s') for pos_line in
                                        so_line.pos_order_line_ids if so_line.product_id.type != 'service'), 0)
                        return 0

                    qty_delivered = max(so_line.qty_delivered, get_expected_qty_to_ship_later())
                    new_qty = so_line.product_uom_qty - qty_delivered
                    if stock_move.uom_id.compare(new_qty, 0) <= 0:
                        new_qty = 0
                    stock_move.product_uom_qty = so_line.compute_uom_qty(new_qty, stock_move, False)
                    # If the product is delivered with more than one step, we need to update the quantity of the other steps
                    for move in so_line_stock_move_ids.filtered(lambda m: m.state in ['waiting', 'confirmed', 'assigned'] and m.product_id == stock_move.product_id):
                        move.product_uom_qty = stock_move.product_uom_qty
                        waiting_picking_ids.add(move.picking_id.id)
                    waiting_picking_ids.add(picking.id)

            def is_product_uom_qty_zero(move):
                return move.uom_id.is_zero(move.product_uom_qty)

            # cancel the waiting pickings if each product_uom_qty of move is zero
            for picking in self.env['stock.picking'].browse(waiting_picking_ids):
                if all(is_product_uom_qty_zero(move) for move in picking.move_ids):
                    picking.action_cancel()
                else:
                    # We make sure that the original picking still has the correct quantity reserved
                    picking.action_assign()

        return data

    def _force_create_picking_real_time(self):
        result = super()._force_create_picking_real_time()
        return result or any(self.lines.mapped('sale_order_origin_id'))
