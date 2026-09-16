from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    timesheet_count = fields.Float(
        string="Timesheet activities",
        export_string_translation=False,
        compute="_compute_timesheet_count",
        groups="hr_timesheet.group_hr_timesheet_user",
    )
    timesheet_encode_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="company_id.timesheet_encode_uom_id",
        export_string_translation=False,
    )
    timesheet_total_duration = fields.Integer(
        export_string_translation=False,
        compute="_compute_timesheet_total_duration",
        compute_sudo=True,
        groups="hr_timesheet.group_hr_timesheet_user",
        help="Total recorded duration, expressed in the encoding UoM, and rounded to the unit",
    )
    show_hours_recorded_button = fields.Boolean(
        export_string_translation=False,
        compute="_compute_show_hours_recorded_button",
        groups="hr_timesheet.group_hr_timesheet_user",
    )

    def _compute_timesheet_count(self):
        timesheets_per_so = {
            order.id: count
            for order, count in self.env["account.analytic.line"]._read_group(
                [("order_id", "in", self.ids), ("project_id", "!=", False)],
                ["order_id"],
                ["__count"],
            )
        }

        for order in self:
            order.timesheet_count = timesheets_per_so.get(order.id, 0)

    @api.depends(
        "company_id.project_time_mode_id",
        "company_id.timesheet_encode_uom_id",
        "line_ids.timesheet_ids",
    )
    def _compute_timesheet_total_duration(self):
        group_data = self.env["account.analytic.line"]._read_group(
            [("order_id", "in", self.ids), ("project_id", "!=", False)],
            ["order_id"],
            ["unit_amount:sum"],
        )
        timesheet_unit_amount_dict = defaultdict(float)
        timesheet_unit_amount_dict.update(
            {order.id: unit_amount for order, unit_amount in group_data}
        )
        for sale_order in self:
            total_time = (
                sale_order.company_id.project_time_mode_id._get_quantity_in_unit(
                    timesheet_unit_amount_dict[sale_order.id],
                    sale_order.timesheet_encode_uom_id,
                    rounding_method="HALF-UP",
                    raise_if_failure=False,
                )
            )
            sale_order.timesheet_total_duration = round(total_time)

    def _compute_field_value(self, field, validate=True):
        if field.name != "invoice_state" or self.env.context.get(
            "mail_activity_automation_skip"
        ):
            super()._compute_field_value(field, validate=validate)
            return

        upsellable_orders = self.filtered(
            lambda so: (
                so.state == "done"
                and so.invoice_state != "over done"
                and so.id
                and (so.user_id or so.partner_id.user_id)
            )
        )
        super(
            SaleOrder,
            upsellable_orders.with_context(mail_activity_automation_skip=True),
        )._compute_field_value(field, validate=validate)
        for order in upsellable_orders:
            upsellable_lines = order._get_prepaid_service_lines_to_upsell()
            if upsellable_lines:
                _debug.pipeline(
                    "prepaid_upsell_detected", order=order, lines=upsellable_lines
                )
                order._create_upsell_activity()
                upsellable_lines.write({"has_displayed_warning_upsell": True})
        super(SaleOrder, self - upsellable_orders)._compute_field_value(
            field, validate=validate
        )

    @api.depends("timesheet_count", "project_count", "line_ids.product_id")
    def _compute_show_hours_recorded_button(self):
        show_button_ids = self._get_order_with_valid_service_product()
        for order in self:
            order.show_hours_recorded_button = order.timesheet_count or (
                order.project_count and order.id in show_button_ids
            )

    @api.model_create_multi
    def create(self, vals_list):
        created_records = super().create(vals_list)
        if self.env.context.get("create_for_employee_mapping"):
            if not next(
                (sol for sol in created_records.line_ids if sol.is_service), False
            ):
                _debug.logic(
                    "employee_mapping_order_refused",
                    orders=created_records,
                    reason="no_service_line",
                )
                raise UserError(
                    _("The Sales Order must contain at least one service product.")
                )
            _debug.pipeline(
                "order_confirmed_for_employee_mapping", orders=created_records
            )
            created_records.with_context(
                disable_project_task_generation=True
            ).action_confirm()
        return created_records

    def _get_order_with_valid_service_product(self):
        SaleOrderLine = self.env["sale.order.line"]
        return SaleOrderLine._read_group(
            Domain.AND(
                [
                    SaleOrderLine._domain_sale_line_service(),
                    [
                        ("order_id", "in", self.ids),
                        "|",
                        ("product_id.service_type", "not in", ["milestones", "manual"]),
                        ("product_id.invoice_policy", "!=", "transferred"),
                    ],
                ]
            ),
            aggregates=["order_id:array_agg"],
        )[0][0]

    def _get_prepaid_service_lines_to_upsell(self):
        self.check_singleton()
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        return self.line_ids.filtered(
            lambda sol: (
                sol.is_service
                and (sol.invoice_state != "done" or sol._is_upsell_opportunity())
                and not sol.has_displayed_warning_upsell
                and sol.product_id.service_policy == "ordered_prepaid"
                and float_compare(
                    sol.qty_transferred,
                    sol.product_qty * (sol.product_id.service_upsell_threshold or 1.0),
                    precision_digits=precision,
                )
                > 0
            )
        )

    def action_view_timesheet(self):
        self.check_singleton()
        if not self.line_ids:
            return {"type": "ir.actions.act_window_close"}

        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale_timesheet.timesheet_action_from_sales_order"
        )
        default_sale_line = next(
            (
                sale_line
                for sale_line in self.line_ids
                if sale_line.is_service
                and sale_line.product_id.service_policy
                in ["ordered_prepaid", "delivered_timesheet"]
            ),
            self.env["sale.order.line"],
        )
        context = {
            "search_default_billable_timesheet": True,
            "default_is_so_line_edited": True,
            "default_so_line": default_sale_line.id,
        }

        tasks = self.line_ids.task_id._filtered_access("write")
        if tasks:
            context["default_task_id"] = tasks[0].id
        else:
            projects = self.line_ids.project_id._filtered_access("write")
            if projects:
                context["default_project_id"] = projects[0].id
            elif self.project_ids:
                context["default_project_id"] = self.project_ids[0].id
        action.update(
            {
                "context": context,
                "domain": [
                    ("so_line", "in", self.line_ids.ids),
                    ("project_id", "!=", False),
                ],
                "help": _("""
                <p class="o_view_nocontent_smiling_face">
                    No activities found. Let's start a new one!
                </p><p>
                    Track your working hours by projects every day and invoice this time to your customers.
                </p>
            """),
            }
        )

        return action

    def _reset_has_displayed_warning_upsell_order_lines(self):
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        for line in self.line_ids:
            if (
                line.has_displayed_warning_upsell
                and line.product_uom_id
                and float_compare(
                    line.qty_transferred, line.product_qty, precision_digits=precision
                )
                == 0
            ):
                _debug.lifecycle("upsell_warning_reset", line=line)
                line.has_displayed_warning_upsell = False

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        _debug.pipeline("timesheets_linked_to_invoices", orders=self, moves=moves)
        moves._link_timesheets_to_invoice(
            self.env.context.get("timesheet_start_date"),
            self.env.context.get("timesheet_end_date"),
        )
        self._reset_has_displayed_warning_upsell_order_lines()
        return moves
