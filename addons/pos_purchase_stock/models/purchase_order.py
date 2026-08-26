from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pos_order_count = fields.Integer(
        "Number of Source PoS Orders",
        compute="_compute_pos_order_count",
        groups="point_of_sale.group_pos_user",
    )

    @api.depends("reference_ids", "reference_ids.pos_order_ids")
    def _compute_pos_order_count(self):
        for purchase in self:
            purchase.pos_order_count = len(purchase._get_pos_orders())

    def _get_pos_orders(self):
        return self.reference_ids.pos_order_ids

    def action_view_pos_orders(self):
        self.ensure_one()
        return self._get_pos_orders()._get_records_action(name=_("Source PoS Orders of %s", self.name))


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _reduce_product_qty(self, product_qty):
        for line in self.filtered(lambda l: l.uom_id.compare(l.product_qty, max(l.qty_received, l.qty_invoiced)) > 0):
            if line.product_id.uom_id.is_zero(product_qty):
                return
            qty = min(
                line.product_id.uom_id._compute_quantity(product_qty, line.uom_id),
                line.product_qty - max(line.qty_received, line.qty_invoiced),
            )
            line.product_qty -= qty
            product_qty -= line.uom_id._compute_quantity(qty, line.product_id.uom_id)
