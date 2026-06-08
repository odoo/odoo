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

    sale_order_line_name = fields.Text(related="sale_order_line_id.name")
    has_default_product = fields.Boolean(
        compute='_compute_has_default_product',
        help="To check whether the product is default product from pos.config or not. In case of "
        "description only SOLs we use default product from pos.config."
    )

    @api.depends('product_id')
    def _compute_has_default_product(self):
        for line in self:
            line.has_default_product = line.product_id == line.order_id.config_id.default_product_id

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
        params += [
            'sale_order_origin_id',
            'sale_order_line_id',
            'down_payment_details',
            'has_default_product',
            'sale_order_line_name'
        ]
        return params
