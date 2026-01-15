# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertimeLine(models.Model):
    _name = 'hr.attendance.overtime.line'
    _inherit = 'hr.attendance.overtime.line'

    compensable_as_leave = fields.Boolean("Compensable as Time Off")
