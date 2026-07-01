# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    sale_order_origin_id = fields.Many2one('sale.order', string="Linked Sale Order", index='btree_not_null')
    sale_order_line_id = fields.Many2one('sale.order.line', string="Source Sale Order Line", index='btree_not_null')
    down_payment_details = fields.Text(string="Down Payment Details")
    qty_delivered = fields.Float(
        string="Delivery Quantity",
        compute='_compute_qty_delivered',
        store=True, readonly=False, copy=False)

    @api.depends('order_id.state')
    def _compute_qty_delivered(self):
        for order_line in self:
            if order_line.order_id.state in ['paid', 'done']:
                order_line.qty_delivered = order_line.qty
            else:
                order_line.qty_delivered = 0

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['sale_order_origin_id', 'sale_order_line_id', 'down_payment_details']
        return params
<<<<<<< a991a76192d153c993d6900ea4564b8e667f068e
||||||| 62b4977f2cc0605a8632475c8217d8cc66684082

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped('order_id')
        for order in orders:
            self.env['stock.move'].browse(order.lines.sale_order_line_id.move_ids._rollup_move_origs()).filtered(lambda ml: ml.state not in ['cancel', 'done'])._action_cancel()
        return super()._launch_stock_rule_from_pos_order_lines()
=======

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped('order_id')
        for order in orders:
            self.env['stock.move'].browse(order.lines.sale_order_line_id.move_ids._rollup_move_origs()).filtered(lambda ml: ml.state not in ['cancel', 'done'])._action_cancel()
        return super()._launch_stock_rule_from_pos_order_lines()

    def _prepare_refund_data(self, refund_order, PosOrderLineLot):
        data = super()._prepare_refund_data(refund_order, PosOrderLineLot)
        data.update({
            'sale_order_line_id': False,  # Remove the sale order line id to be coherent with frontend refund
        })
        return data
>>>>>>> cffd8cc82456604ba6b74f157380a78cd2e17afc
