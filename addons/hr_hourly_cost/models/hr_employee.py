from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    hourly_cost = fields.Monetary(
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
