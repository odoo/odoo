from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    margin = fields.Monetary(
        compute="_compute_margins",
        store=True,
        groups="base.group_user",
    )
    margin_percent = fields.Float(
        string="Margin (%)",
        compute="_compute_margins",
        store=True,
        aggregator="avg",
        groups="base.group_user",
    )

    @api.depends("line_ids.margin", "amount_untaxed")
    def _compute_margins(self):
        if not all(self._ids):
            _debug.logic("order_margin", orders=self, by="in_memory_sum")
            for order in self:
                order.margin = sum(order.line_ids.mapped("margin"))
        else:
            grouped_order_lines_data = self.env["sale.order.line"]._read_group(
                [
                    ("order_id", "in", self.ids),
                ],
                ["order_id"],
                ["margin:sum"],
            )
            mapped_data = {
                order.id: margin for order, margin in grouped_order_lines_data
            }
            _debug.perf.count(
                "order_margin_read_group", orders=len(self), rows=len(mapped_data)
            )
            for order in self:
                order.margin = mapped_data.get(order.id, 0.0)
        for order in self:
            order.margin_percent = (
                order.amount_untaxed and order.margin / order.amount_untaxed
            )
