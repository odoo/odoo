from odoo import fields, models


class AccountAnalyticLineCalendarEmployee(models.Model):
    _name = "account.analytic.line.calendar.employee"
    _description = "Personal Filters on Employees for the Calendar view"

    user_id = fields.Many2one(
        comodel_name="res.users",
        export_string_translation=False,
        default=lambda self: self.env.user,
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        export_string_translation=False,
    )
    checked = fields.Boolean(
        export_string_translation=False,
        default=True,
    )
    active = fields.Boolean(
        export_string_translation=False,
        default=True,
    )
