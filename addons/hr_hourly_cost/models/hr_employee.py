from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    hourly_cost = fields.Monetary(
        currency_field="currency_id",
        groups="hr.group_hr_user",
        default=0.0,
        tracking=True,
    )

    @api.constrains("hourly_cost")
    def _check_hourly_cost(self):
        for employee in self:
            if employee.hourly_cost < 0:
                raise ValidationError(self.env._("The hourly cost cannot be negative."))
