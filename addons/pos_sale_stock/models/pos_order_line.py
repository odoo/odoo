# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.depends('order_id.state', 'order_id.picking_ids', 'order_id.picking_ids.state', 'order_id.picking_ids.move_ids.quantity')
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()
        product_qty_left_to_assign = {}
        for order_line in self:
            if order_line.order_id.state in ['paid', 'done']:
                outgoing_pickings = order_line.order_id.picking_ids.filtered(
                    lambda pick: pick.state == 'done' and pick.picking_type_code == 'outgoing'
                )

                if outgoing_pickings and order_line.order_id.shipping_date:
                    moves = outgoing_pickings.move_ids.filtered(
                        lambda m: m.state == 'done' and m.product_id == order_line.product_id
                    )
                    qty_left = product_qty_left_to_assign.get(order_line.product_id.id, False)
                    if (qty_left):
                        order_line.qty_delivered = min(order_line.qty, qty_left)
                        product_qty_left_to_assign[order_line.product_id.id] -= order_line.qty_delivered
                    else:
                        order_line.qty_delivered = min(order_line.qty, sum(moves.mapped('quantity')))
                        product_qty_left_to_assign[order_line.product_id.id] = sum(moves.mapped('quantity')) - order_line.qty_delivered

                elif outgoing_pickings:
                    # If the order is not delivered later, and in a "paid", "done" or "invoiced" state, it fully delivered
                    order_line.qty_delivered = order_line.qty
                else:
                    order_line.qty_delivered = 0

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped('order_id')
        for order in orders:
            self.env['stock.move'].browse(order.lines.sale_order_line_id.move_ids._rollup_move_origs()).filtered(lambda ml: ml.state not in ['cancel', 'done'])._action_cancel()
        return super()._launch_stock_rule_from_pos_order_lines()
