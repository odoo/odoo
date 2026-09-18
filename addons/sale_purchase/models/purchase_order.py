from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

from .exception_activity import group_by_order, notify_orders_of_exception

_debug = DebugLog(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sale_order_count = fields.Integer(
        string="Number of Source Sale",
        compute="_compute_sale_orders",
        groups="sale.group_sale_salesman",
    )
    has_sale_order = fields.Boolean(
        string="Has Source Sale",
        compute="_compute_has_sale_order",
        help="Technical field: whether the purchase order has associated sale orders.",
    )

    @api.depends("line_ids.sale_order_id")
    def _compute_sale_orders(self):
        for purchase in self:
            purchase.sale_order_count = len(purchase._get_sale_orders())

    @api.depends("line_ids.sale_order_id")
    def _compute_has_sale_order(self):
        for purchase in self:
            purchase.has_sale_order = bool(purchase.sudo()._get_sale_orders())

    def action_view_sale_orders(self):
        self.check_singleton()
        sale_orders = self._get_sale_orders()
        title = (
            {"name": _("Sources Sale Orders %s", self.name)}
            if len(sale_orders) > 1
            else {}
        )
        return sale_orders._get_records_action(**title)

    def action_cancel(self):
        result = super().action_cancel()
        _debug.pipeline("sale_notified_of_purchase_cancel", purchase_orders=self)
        self.sudo()._activity_cancel_on_sale()
        return result

    def _get_sale_orders(self):
        return self.line_ids.sale_order_id

    def _activity_cancel_on_sale(self):
        purchase_lines = self.line_ids.filtered("sale_line_id")
        notify_orders_of_exception(
            group_by_order(purchase_lines, lambda pol: pol.sale_line_id.order_id),
            "sale_purchase.exception_sale_on_purchase_cancellation",
            lambda lines: {
                "purchase_orders": lines.order_id,
                "purchase_order_lines": lines,
            },
        )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    sale_order_id = fields.Many2one(
        related="sale_line_id.order_id",
        string="Sale Order",
    )
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Origin Sale Item",
        index="btree_not_null",
        copy=False,
    )
