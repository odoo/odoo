from collections import defaultdict

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    timesheet_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="timesheet_invoice_id",
        string="Timesheets",
        export_string_translation=False,
        copy=False,
        readonly=True,
    )
    timesheet_count = fields.Integer(
        string="Number of timesheets",
        export_string_translation=False,
        compute="_compute_timesheet_count",
        compute_sudo=True,
    )
    timesheet_encode_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="company_id.timesheet_encode_uom_id",
        export_string_translation=False,
    )
    timesheet_total_duration = fields.Integer(
        compute="_compute_timesheet_total_duration",
        compute_sudo=True,
        help="Total recorded duration, expressed in the encoding UoM, and rounded to the unit",
    )

    @api.depends("timesheet_ids", "company_id.timesheet_encode_uom_id")
    def _compute_timesheet_total_duration(self):
        if not self.env.user.has_group("hr_timesheet.group_hr_timesheet_user"):
            self.timesheet_total_duration = 0
            return
        group_data = self.env["account.analytic.line"]._read_group(
            [("timesheet_invoice_id", "in", self.ids)],
            ["timesheet_invoice_id"],
            ["unit_amount:sum"],
        )
        timesheet_unit_amount_dict = defaultdict(float)
        timesheet_unit_amount_dict.update(
            {timesheet_invoice.id: amount for timesheet_invoice, amount in group_data}
        )
        for invoice in self:
            total_time = invoice.company_id.project_time_mode_id._get_quantity_in_unit(
                timesheet_unit_amount_dict[invoice.id],
                invoice.timesheet_encode_uom_id,
                rounding_method="HALF-UP",
                raise_if_failure=False,
            )
            invoice.timesheet_total_duration = round(total_time)

    @api.depends("timesheet_ids")
    def _compute_timesheet_count(self):
        timesheet_data = self.env["account.analytic.line"]._read_group(
            [("timesheet_invoice_id", "in", self.ids)],
            ["timesheet_invoice_id"],
            ["__count"],
        )
        mapped_data = {
            timesheet_invoice.id: count for timesheet_invoice, count in timesheet_data
        }
        for invoice in self:
            invoice.timesheet_count = mapped_data.get(invoice.id, 0)

    def action_view_timesheet(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Timesheets"),
            "domain": [("project_id", "!=", False)],
            "res_model": "account.analytic.line",
            "view_id": False,
            "view_mode": "list,form",
            "help": _("""
                <p class="o_view_nocontent_smiling_face">
                    Record timesheets
                </p><p>
                    You can register and track your workings hours by project every
                    day. Every time spent on a project will become a cost and can be re-invoiced to
                    customers if required.
                </p>
            """),
            "limit": 80,
            "context": {
                "default_project_id": self.id,
                "search_default_project_id": [self.id],
            },
        }

    def _link_timesheets_to_invoice(self, start_date=None, end_date=None):
        for line in self.filtered(
            lambda i: i.move_type == "out_invoice" and i.state == "draft"
        ).invoice_line_ids:
            sale_line_delivery = line.sale_line_ids.filtered(
                lambda sol: (
                    sol.product_id.invoice_policy == "transferred"
                    and sol.product_id.service_type == "timesheet"
                )
            )
            if not start_date and not end_date:
                start_date, end_date = self._get_range_dates(
                    sale_line_delivery.order_id
                )
            if sale_line_delivery:
                domain = Domain(
                    line._timesheet_domain_get_invoiced_lines(sale_line_delivery)
                )
                if start_date:
                    domain &= Domain("date", ">=", start_date)
                if end_date:
                    domain &= Domain("date", "<=", end_date)
                timesheets = self.env["account.analytic.line"].sudo().search(domain)  # noqa: E8507 - one query per invoiced line, on its own timesheet domain
                _debug.lifecycle(
                    "timesheets_invoiced",
                    move=line.move_id,
                    line=line,
                    timesheets=timesheets,
                )
                timesheets.write({"timesheet_invoice_id": line.move_id.id})

    def _get_range_dates(self, order):
        return None, None

    def action_post(self):
        result = super().action_post()
        credit_notes = self.filtered(
            lambda move: move.move_type == "out_refund" and move.reversed_entry_id
        )
        timesheets_sudo = (
            self.env["account.analytic.line"]
            .sudo()
            .search(
                [
                    ("timesheet_invoice_id", "in", credit_notes.reversed_entry_id.ids),
                    ("so_line", "in", credit_notes.invoice_line_ids.sale_line_ids.ids),
                    ("project_id", "!=", False),
                ]
            )
        )
        timesheets_sudo.write({"timesheet_invoice_id": False})
        return result
