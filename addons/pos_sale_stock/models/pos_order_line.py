# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _get_qty_to_move(self):
        # Override to only ship what the linked sale order still owes.
        sale_line = self.sale_order_line_id.sudo()
        if not sale_line or self.qty < 0:
            return super()._get_qty_to_move()
        qty_left = sale_line.product_uom_qty - sale_line.qty_delivered
        return min(self.qty, max(sale_line._convert_qty(sale_line, qty_left, 's2p'), 0))

    @api.depends('order_id.state', 'order_id.picking_ids', 'order_id.picking_ids.state', 'order_id.picking_ids.move_ids.quantity')
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()
        product_qty_left_to_assign = {}
        for order, order_lines in self.grouped('order_id').items():
            if order.state in ['paid', 'done']:
                outgoing_pickings = order.picking_ids.filtered(
                    lambda pick: pick.state == 'done' and pick.picking_type_code == 'outgoing'
                )
                if not outgoing_pickings:
                    order_lines.qty_delivered = 0
                    continue

                for order_line in order_lines:
                    if not order.shipping_date:
                        # If the order is not delivered later, and in a "paid", "done" or "invoiced"
                        # state, it is considered as delivered
                        order_line.qty_delivered = order_line._get_qty_to_move()
                        continue
                    if order_line.product_id.type != 'consu':
                        order_line.qty_delivered = 0
                        continue

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

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped('order_id')
        for order in orders:
            self.env['stock.move'].browse(order.lines.sale_order_line_id.move_ids._rollup_move_origs()).filtered(lambda ml: ml.state not in ['cancel', 'done'])._action_cancel()
        return super()._launch_stock_rule_from_pos_order_lines()
