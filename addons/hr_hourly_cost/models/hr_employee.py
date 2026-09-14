from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    hourly_cost = fields.Monetary(
        default=0.0,
        aggregator="avg",
        tracking=True,
        groups="hr.group_hr_user",
        help="What one hour of this employee's work costs the company. It values "
        "timesheets and worked time; it is not the employee's wage.",
    )

    _hourly_cost_positive = models.Constraint(
        "CHECK(hourly_cost >= 0)",
        "The hourly cost cannot be negative.",
    )

    def write(self, vals):
        converted = self._get_hourly_costs_in_new_company_currency(vals)
        result = super().write(vals)
        if _debug.lifecycle.enabled and converted:
            _debug.lifecycle(
                "hourly_cost_reconverted",
                employees=len(converted),
                company=vals.get("company_id"),
            )
        for employee, hourly_cost in converted.items():
            employee.write({"hourly_cost": hourly_cost})
        return result

    def _get_hourly_costs_in_new_company_currency(self, vals):
        if "company_id" not in vals or "hourly_cost" in vals:
            return {}
        company = self.env["res.company"].browse(vals["company_id"])
        if not company.currency_id:
            _debug.logic("hourly_cost_conversion_skipped", company=company)
            return {}
        date = fields.Date.context_today(self)
        return {
            employee: employee.currency_id._convert(
                employee.hourly_cost, company.currency_id, company, date
            )
            for employee in self.sudo()
            if employee.hourly_cost and employee.currency_id != company.currency_id
        }
