from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import format_duration

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_transferred_method = fields.Selection(
        selection_add=[("timesheet", "Timesheets")]
    )
    analytic_line_ids = fields.One2many(domain=[("project_id", "=", False)])
    remaining_hours_available = fields.Boolean(
        compute="_compute_remaining_hours_available",
        compute_sudo=True,
    )
    remaining_hours = fields.Float(
        string="Time Remaining on SO",
        compute="_compute_remaining_hours",
        compute_sudo=True,
        store=True,
    )
    has_displayed_warning_upsell = fields.Boolean(
        export_string_translation=False,
        copy=False,
    )
    timesheet_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="so_line",
        string="Timesheets",
        export_string_translation=False,
        domain=[("project_id", "!=", False)],
    )

    @api.depends("remaining_hours_available", "remaining_hours")
    @api.depends_context("with_remaining_hours", "company")
    def _compute_display_name(self):
        super()._compute_display_name()
        with_remaining_hours = self.env.context.get(
            "with_remaining_hours"
        ) and not self.env.context.get("skip_remaining_hours", False)
        if with_remaining_hours and any(
            line.remaining_hours_available for line in self
        ):
            company = self.env.company
            encoding_uom = company.timesheet_encode_uom_id
            is_hour = is_day = False
            unit_label = ""
            if encoding_uom == self.env.ref("uom.product_uom_hour"):
                is_hour = True
                unit_label = _("remaining")
            elif encoding_uom == self.env.ref("uom.product_uom_day"):
                is_day = True
                unit_label = _("days remaining")
            for line in self:
                if line.remaining_hours_available:
                    remaining_time = ""
                    if is_hour:
                        remaining_time = (
                            f" ({format_duration(line.remaining_hours)} {unit_label})"
                        )
                    elif is_day:
                        remaining_days = (
                            company.project_time_mode_id._get_quantity_in_unit(
                                line.remaining_hours, encoding_uom, round=False
                            )
                        )
                        remaining_time = f" ({remaining_days:.02f} {unit_label})"
                    name = f"{line.display_name}{remaining_time}"
                    line.display_name = name

    @api.depends("product_id.service_policy")
    def _compute_remaining_hours_available(self):
        for line in self:
            is_ordered_prepaid = line.product_id.service_policy == "ordered_prepaid"
            is_time_product = (
                line.product_uom_id
                and line.product_uom_id._has_common_reference(
                    self.env.ref("uom.product_uom_hour")
                )
            )
            line.remaining_hours_available = is_ordered_prepaid and is_time_product

    @api.depends("qty_transferred", "product_qty", "analytic_line_ids")
    def _compute_remaining_hours(self):
        uom_hour = self.env.ref("uom.product_uom_hour")
        for line in self:
            remaining_hours = None
            if line.remaining_hours_available:
                qty_left = line.product_qty - line.qty_transferred
                remaining_hours = line.product_uom_id._get_quantity_in_unit(
                    qty_left, uom_hour, round=False
                )
            line.remaining_hours = remaining_hours

    @api.depends("product_id")
    def _compute_qty_transferred_method(self):
        super()._compute_qty_transferred_method()
        for line in self:
            if (
                not line.is_expense
                and line.product_id.type == "service"
                and line.product_id.service_type == "timesheet"
            ):
                line.qty_transferred_method = "timesheet"
                _debug.logic("qty_method_timesheet", line=line)

    @api.depends("analytic_line_ids.project_id", "project_id.pricing_type")
    def _compute_qty_transferred(self):
        super()._compute_qty_transferred()
        lines_by_timesheet = self.filtered(
            lambda sol: sol.qty_transferred_method == "timesheet"
        )
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        mapping = lines_by_timesheet.sudo()._get_qty_delivered_by_analytic(domain)
        _debug.perf.count(
            "qty_from_timesheets",
            lines=len(lines_by_timesheet),
            rows=len(mapping),
        )
        for line in lines_by_timesheet:
            line.qty_transferred = mapping.get(line.id or line._origin.id, 0.0)

    def _prepare_qty_transferred(self):
        delivered_qties = super()._prepare_qty_transferred()
        lines_by_timesheet = self.filtered(
            lambda sol: sol.qty_transferred_method == "timesheet"
        )
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        mapping = lines_by_timesheet.sudo()._get_qty_delivered_by_analytic(domain)
        for line in lines_by_timesheet:
            delivered_qties[line] = mapping.get(line.id or line._origin.id, 0.0)
        return delivered_qties

    def _timesheet_compute_delivered_quantity_domain(self):
        domain = [("project_id", "!=", False)]
        if self.env.context.get("accrual_entry_date"):
            domain += [("date", "<=", self.env.context["accrual_entry_date"])]
        return domain

    def _convert_qty_company_hours(self, dest_company):
        company_time_uom_id = dest_company.project_time_mode_id
        allocated_hours = 0.0
        product_uom_id = self.product_uom_id
        if product_uom_id == self.env.ref("uom.product_uom_unit"):
            product_uom_id = self.env.ref("uom.product_uom_hour")
        if (
            product_uom_id != company_time_uom_id
            and product_uom_id._has_common_reference(company_time_uom_id)
        ):
            allocated_hours = product_uom_id._get_quantity_in_unit(
                self.product_qty, company_time_uom_id, rounding_method="HALF-UP"
            )
        else:
            allocated_hours = self.product_qty
        return allocated_hours

    def _timesheet_create_project(self):
        project = super()._timesheet_create_project()
        if self.product_id.project_template_id.allocated_hours:
            _debug.logic("project_hours", line=self, by="template")
            project.write(
                {
                    "allocated_hours": self.product_id.project_template_id.allocated_hours,
                    "allow_timesheets": True,
                }
            )
            return project
        project_uom = self.company_id.project_time_mode_id
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_hour = self.env.ref("uom.product_uom_hour")

        factor_per_id = {
            uom.id: uom.factor for uom in self.order_id.line_ids.product_uom_id
        }
        factor_per_id[uom_unit.id] = uom_hour.factor

        allocated_hours = 0.0
        for line in self.order_id.line_ids:
            if (
                line.is_service
                and line.product_id.service_tracking
                in ["task_in_project", "project_only"]
                and line.product_id.project_template_id
                == self.product_id.project_template_id
                and line.product_uom_id.id in factor_per_id
            ):
                uom_factor = factor_per_id[line.product_uom_id.id] / project_uom.factor
                allocated_hours += line.product_qty * uom_factor

        _debug.logic(
            "project_hours", line=self, by="order_lines", hours=allocated_hours
        )
        project.write(
            {
                "allocated_hours": allocated_hours,
                "allow_timesheets": True,
            }
        )
        return project

    def _timesheet_create_project_prepare_values(self):
        values = super()._timesheet_create_project_prepare_values()
        values["allow_billable"] = True
        return values

    def _recompute_qty_to_invoice(self, start_date, end_date):
        lines_by_timesheet = self.filtered(
            lambda sol: sol.product_id and sol.product_id._is_delivered_timesheet()
        )
        domain = Domain(
            lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        )
        refund_account_moves = self.order_id.invoice_ids.filtered(
            lambda am: am.state == "posted" and am.move_type == "out_refund"
        ).reversed_entry_id
        timesheet_domain = Domain("timesheet_invoice_id", "=", False) | Domain(
            "timesheet_invoice_id.state", "=", "cancel"
        )
        if refund_account_moves:
            credited_timesheet_domain = Domain(
                "timesheet_invoice_id.state", "=", "posted"
            ) & Domain("timesheet_invoice_id", "in", refund_account_moves.ids)
            timesheet_domain |= credited_timesheet_domain
        domain &= timesheet_domain
        if start_date:
            domain &= Domain("date", ">=", start_date)
        if end_date:
            domain &= Domain("date", "<=", end_date)
        mapping = lines_by_timesheet.sudo()._get_qty_delivered_by_analytic(domain)
        _debug.pipeline(
            "qty_to_invoice_recomputed",
            lines=lines_by_timesheet,
            rows=len(mapping),
            refunds=refund_account_moves,
        )

        for line in lines_by_timesheet:
            qty_to_invoice = mapping.get(line.id, 0.0)
            if qty_to_invoice:
                line.qty_to_invoice = qty_to_invoice
            else:
                prev_inv_status = line.invoice_state
                line.qty_to_invoice = qty_to_invoice
                line.invoice_state = prev_inv_status
                _debug.logic(
                    "invoice_state_preserved", line=line, state=prev_inv_status
                )

    def _get_action_per_item(self):
        action_per_sol = super()._get_action_per_item()
        timesheet_action = self.env.ref(
            "sale_timesheet.timesheet_action_from_sales_order_item"
        ).id
        timesheet_ids_per_sol = {}
        if self.env.user.has_group("hr_timesheet.group_hr_timesheet_user"):
            timesheet_read_group = self.env["account.analytic.line"]._read_group(
                [("so_line", "in", self.ids), ("project_id", "!=", False)],
                ["so_line"],
                ["id:array_agg"],
            )
            timesheet_ids_per_sol = {
                so_line.id: ids for so_line, ids in timesheet_read_group
            }
            _debug.perf.count(
                "timesheets_per_line", lines=len(self), rows=len(timesheet_ids_per_sol)
            )
        for sol in self:
            timesheet_ids = timesheet_ids_per_sol.get(sol.id, [])
            if sol.is_service and len(timesheet_ids) > 0:
                action_per_sol[sol.id] = (
                    timesheet_action,
                    timesheet_ids[0] if len(timesheet_ids) == 1 else False,
                )
        return action_per_sol

    @api.model
    def _get_product_service_policy(self):
        return super()._get_product_service_policy() + ["delivered_timesheet"]
