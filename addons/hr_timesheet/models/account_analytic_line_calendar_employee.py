from odoo import fields, models


class AccountAnalyticLineCalendarEmployee(models.Model):

    _name = 'account.analytic.line.calendar.employee'
    _description = 'Personal Filters on Employees for the Calendar view'

    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, ondelete='cascade', export_string_translation=False)
    employee_id = fields.Many2one('hr.employee', export_string_translation=False)
    checked = fields.Boolean(default=True, export_string_translation=False)
    active = fields.Boolean(default=True, export_string_translation=False)
