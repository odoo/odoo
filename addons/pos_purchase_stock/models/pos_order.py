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

    def action_view_purchase_orders(self):
        self.ensure_one()
        purchase_order_ids = self._get_purchase_orders().ids
        action = {
            "res_model": "purchase.order",
            "type": "ir.actions.act_window",
        }
        if len(purchase_order_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": purchase_order_ids[0],
                }
            )
        else:
            action.update(
                {
                    "name": _("Purchase Orders generated from %s", self.name),
                    "domain": [("id", "in", purchase_order_ids)],
                    "view_mode": "list,form",
                }
            )
        return action
