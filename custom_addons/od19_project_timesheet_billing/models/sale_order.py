from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_unbilled_timesheet_count = fields.Integer(
        string="Unbilled Timesheets",
        compute="_compute_od19_unbilled_timesheet",
        compute_sudo=True,
    )
    od19_unbilled_timesheet_hours = fields.Float(
        string="Unbilled Hours",
        compute="_compute_od19_unbilled_timesheet",
        compute_sudo=True,
    )

    @api.depends("order_line")
    def _compute_od19_unbilled_timesheet(self):
        grouped = self.env["account.analytic.line"]._read_group(
            [
                ("od19_is_billable_unbilled", "=", True),
                ("order_id", "in", self.ids),
            ],
            ["order_id"],
            ["__count", "unit_amount:sum"],
        )
        mapped = {order.id: (count, hours) for order, count, hours in grouped if order}
        for order in self:
            count, hours = mapped.get(order.id, (0, 0))
            order.od19_unbilled_timesheet_count = count
            order.od19_unbilled_timesheet_hours = hours

    def _od19_unbilled_timesheet_domain(self):
        self.ensure_one()
        return [
            ("od19_is_billable_unbilled", "=", True),
            ("order_id", "=", self.id),
        ]

    def action_od19_view_unbilled_timesheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Unbilled Timesheets / Timesheet รอเรียกเก็บ"),
            "res_model": "account.analytic.line",
            "view_mode": "list,form",
            "domain": self._od19_unbilled_timesheet_domain(),
        }

    def action_od19_open_timesheet_invoice_wizard(self):
        """Open the date-filtered Timesheet → Invoice wizard for this order."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoice Timesheets / เรียกเก็บจาก Timesheet"),
            "res_model": "od19.timesheet.invoice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_sale_order_ids": [(6, 0, self.ids)]},
        }

    def action_od19_create_invoice_from_timesheets(self):
        """Invoice every billable, not-yet-invoiced timesheet of this order.

        Uses the core ``sale_timesheet`` machinery (``_create_invoices``) so the
        invoices, quantities and timesheet links stay consistent with the
        standard "Timesheet → Invoice" flow.
        """
        self.ensure_one()
        if self.state != "sale":
            raise UserError(_("ต้องยืนยันใบสั่งขายก่อนจึงจะเรียกเก็บเงินได้"))
        timesheets = self.env["account.analytic.line"].search(
            self._od19_unbilled_timesheet_domain()
        )
        if not timesheets:
            raise UserError(
                _("ไม่พบ Timesheet ที่ยังไม่เรียกเก็บสำหรับ %s") % self.display_name
            )
        invoices = self._create_invoices()
        if not invoices:
            raise UserError(_("ไม่สามารถสร้างใบแจ้งหนี้ได้ (ไม่พบรายการที่เรียกเก็บได้)"))
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices / ใบแจ้งหนี้"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", invoices.ids)],
        }
