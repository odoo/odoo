from odoo import api, fields, models, _


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    sale_order_origin_id = fields.Many2one('sale.order', string="Linked Sale Order")
    sale_order_line_id = fields.Many2one('sale.order.line', string="Source Sale Order Line")
    down_payment_details = fields.Text(string="Down Payment Details")
    qty_delivered = fields.Float(
        string="Delivery Quantity",
        compute="_compute_qty_delivered",
        store=True, readonly=False, copy=False)

    @api.depends('order_id.state', 'order_id.picking_ids', 'order_id.picking_ids.state', 'order_id.picking_ids.move_ids.quantity')
    def _compute_qty_delivered(self):
        for order_line in self:
            if order_line.order_id.state in ['paid', 'done']:
                outgoing_pickings = order_line.order_id.picking_ids.filtered(
                    lambda pick: pick.state == 'done' and pick.picking_type_code == 'outgoing'
                )

                if outgoing_pickings:
                    moves = outgoing_pickings.move_ids.filtered(
                        lambda m: m.state == 'done' and m.product_id == order_line.product_id
                    )
                    order_line.qty_delivered = sum(moves.mapped('quantity'))
                else:
                    order_line.qty_delivered = 0

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['sale_order_origin_id', 'sale_order_line_id', 'down_payment_details']
        return params

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped('order_id')
        for order in orders:
            self.env['stock.move'].browse(order.lines.sale_order_line_id.move_ids._rollup_move_origs()).filtered(lambda ml: ml.state not in ['cancel', 'done'])._action_cancel()
        return super()._launch_stock_rule_from_pos_order_lines()
