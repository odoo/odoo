from odoo import api, fields, models
from odoo.exceptions import UserError


class KswAttendanceSheetLine(models.Model):
    _name = 'ksw.attendance.sheet.line'
    _description = 'Attendance Sheet Daily Line'
    _order = 'date'

    sheet_id = fields.Many2one(
        'ksw.attendance.sheet', string='Sheet',
        required=True, ondelete='cascade',
    )
    date = fields.Date(string='Date', required=True)
    day_name = fields.Char(
        string='Day', compute='_compute_day_name', store=True,
    )
    is_workday = fields.Boolean(
        string='Workday', default=True,
        help='False for weekends / non-scheduled days.',
    )
    is_attended = fields.Boolean(
        string='Attended', default=True,
        help='Toggle off to mark the employee as absent on this day.',
    )
    attendance_id = fields.Many2one(
        'hr.attendance', string='Attendance Record',
        readonly=True, ondelete='set null',
        help='Linked hr.attendance record (auto-synced).',
    )

    @api.depends('date')
    def _compute_day_name(self):
        for line in self:
            line.day_name = line.date.strftime('%A') if line.date else False

    def write(self, vals):
        if 'is_attended' in vals:
            for line in self:
                sheet = line.sheet_id
                if sheet.state == 'confirmed' or sheet.is_locked:
                    raise UserError('Cannot modify a locked/confirmed sheet.')
        result = super().write(vals)
        if 'is_attended' in vals:
            # Sync hr.attendance records for changed lines
            for sheet in self.mapped('sheet_id'):
                sheet_lines = self.filtered(lambda l: l.sheet_id == sheet)
                sheet._sync_line_attendance(sheet_lines)
        return result
