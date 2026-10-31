from odoo import _, api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    purchase_order_count = fields.Integer(
        "Number of Purchase Order Generated",
        compute="_compute_purchase_order_count",
        groups="purchase.group_purchase_user",
    )

    @api.depends("stock_reference_ids", "stock_reference_ids.purchase_ids")
    def _compute_purchase_order_count(self):
        for order in self:
            order.purchase_order_count = len(order._get_purchase_orders())

    def _get_purchase_orders(self):
        return self.stock_reference_ids.purchase_ids

    def _create_order_picking(self):
        if self.picking_ids:
            return
        super()._create_order_picking()
        if self.refunded_order_id.shipping_date:
            self._reduce_refunded_purchase_orders()

    def _reduce_refunded_purchase_orders(self):
        purchase_orders = self.sudo().refunded_order_id._get_purchase_orders().filtered(
            lambda po: po.state != "cancel" and not po.locked
        )
        refund_lines = self.lines.grouped("product_id")
        for product, po_lines in purchase_orders.order_line.grouped("product_id").items():
            if product in refund_lines:
                po_lines._reduce_product_qty(-sum(refund_lines[product].mapped(lambda line: line._get_qty_to_move())))
        purchase_orders.filtered(
            lambda po: all(line.uom_id.is_zero(line.product_qty) for line in po.order_line)
        ).button_cancel()

    def action_view_purchase_orders(self):
        self.ensure_one()
        return self._get_purchase_orders()._get_records_action(name=_("Purchase Orders generated from %s", self.name))
