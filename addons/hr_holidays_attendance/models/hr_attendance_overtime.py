from odoo import fields, models


class HrAttendanceOvertimeLine(models.Model):
    _name = "hr.attendance.overtime.line"
    _inherit = "hr.attendance.overtime.line"

    compensable_as_leave = fields.Boolean(string="Compensable as Time Off")
