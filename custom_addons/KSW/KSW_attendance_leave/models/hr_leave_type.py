from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_attendance_issue = fields.Boolean(
        string='Depends on Attendance Issue',
        default=False,
        help='Check this box if this leave type requires linking to '
             'specific attendance records (late, early leave, or absence).',
    )

