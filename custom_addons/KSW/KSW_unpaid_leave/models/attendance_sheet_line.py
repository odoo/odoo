from odoo import fields, models
from odoo.exceptions import UserError


class KswAttendanceSheetLineLeave(models.Model):
    _inherit = 'ksw.attendance.sheet.line'

    x_leave_id = fields.Many2one(
        'hr.leave', string='Linked Leave',
        ondelete='set null', readonly=True, copy=False,
        help='When set, this day is locked by an approved leave '
             'and cannot be toggled by the supervisor.',
    )

    def write(self, vals):
        if 'is_attended' in vals:
            locked_by_leave = self.filtered(lambda l: l.x_leave_id)
            if locked_by_leave:
                raise UserError(
                    'Cannot modify attendance for days locked by an '
                    'approved leave (%s).'
                    % ', '.join(
                        locked_by_leave.mapped(
                            'x_leave_id.holiday_status_id.name'
                        )
                    )
                )
        return super().write(vals)

