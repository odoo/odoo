from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    purchased_product_qty = fields.Float(
        string="Purchased",
        digits="Product Unit",
        compute="_compute_purchased_product_qty",
    )
    is_in_purchase_order = fields.Boolean(
        compute="_compute_is_in_purchase_order",
        search="_search_is_in_purchase_order",
    )

    def _compute_purchased_product_qty(self):
        self._compute_ordered_qty(
            "purchased_product_qty",
            "purchase.order.line",
            "purchase.group_purchase_user",
            "date_confirmed",
            [("order_id.state", "=", "done")],
        )

    @api.depends_context("order_id")
    def _compute_is_in_purchase_order(self):
        self._compute_is_in_order("purchase.order.line", "is_in_purchase_order")

    def _search_is_in_purchase_order(self, operator, value):
        if operator != "in":
            return NotImplemented
        return self._search_is_in_order("purchase.order.line")

    @api.onchange("type")
    def _onchange_type_purchase_warn(self):
        if self._origin and self.purchased_product_qty > 0:
            return {
                "warning": {
                    "title": self.env._("Warning"),
                    "message": self.env._(
                        "You cannot change the product's type because it is already used in purchase orders."
                    ),
                }
            }
        return None

    @api.readonly
    def action_view_po(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "purchase.action_purchase_history",
        )
        action["domain"] = [
            ("state", "=", "done"),
            ("product_id", "in", self.ids),
        ]
        action["display_name"] = self.env._(
            "Purchase History for %s", self.display_name
        )
        return action

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [
            self.env.ref("purchase.menu_purchase_root").id
        ]

    def _is_uom_change_warning_required(self):
        res = super()._is_uom_change_warning_required()
        if res:
            return res
        return self._has_order_lines("purchase.order.line")

    def _update_uom(self, to_uom_id):
        self._update_uom_on_order_lines("purchase.order.line", to_uom_id)
        return super()._update_uom(to_uom_id)
