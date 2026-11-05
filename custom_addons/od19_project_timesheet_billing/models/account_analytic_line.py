from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    """Timesheet helpers for billing on delivered time.

    G-12 (WS-13): make it explicit which timesheet entries are billable but
    not yet invoiced, so the "Timesheet → Invoice" step can be tracked and
    controlled instead of relying on the sales order invoice status alone.
    """

    _inherit = "account.analytic.line"

    od19_is_billable_unbilled = fields.Boolean(
        string="Billable (Unbilled)",
        compute="_compute_od19_is_billable_unbilled",
        search="_search_od19_is_billable_unbilled",
        help="Timesheet ที่ผูกกับรายการขายซึ่งเรียกเก็บตามเวลาที่ใช้ "
             "และยังไม่ได้ออกใบแจ้งหนี้",
    )

    @api.depends("so_line", "so_line.product_id", "timesheet_invoice_id")
    def _compute_od19_is_billable_unbilled(self):
        for line in self:
            line.od19_is_billable_unbilled = line._od19_is_billable_unbilled()

    def _od19_is_billable_unbilled(self):
        self.ensure_one()
        so_line = self.so_line
        if not so_line or not self._is_not_billed():
            return False
        product = so_line.product_id
        return (
            product.invoice_policy == "delivery"
            and product.service_type == "timesheet"
        )

    def _search_od19_is_billable_unbilled(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError(
                _("ไม่รองรับเงื่อนไขการค้นหาสำหรับตัวกรอง 'Billable (Unbilled)'")
            )
        leaves = [
            ("so_line", "!=", False),
            ("so_line.product_id.invoice_policy", "=", "delivery"),
            ("so_line.product_id.service_type", "=", "timesheet"),
            ("timesheet_invoice_id", "=", False),
        ]
        and_expression = [
            "&", "&", leaves[0], leaves[1], "&", leaves[2], leaves[3],
        ]
        want_true = (operator == "=") == value
        return and_expression if want_true else ["!"] + and_expression

    def action_od19_open_sale_order(self):
        """Open the sales order the timesheet will be billed through."""
        self.ensure_one()
        order = self.so_line.order_id
        if not order:
            raise UserError(_("Timesheet นี้ยังไม่ได้ผูกกับรายการขาย"))
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
        }
