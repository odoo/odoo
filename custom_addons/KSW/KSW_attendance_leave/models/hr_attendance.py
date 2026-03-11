# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    x_leave_ids = fields.Many2many(
        'hr.leave',
        'hr_leave_attendance_rel',
        'attendance_id',
        'leave_id',
        string='Related Leaves',
    )

    x_is_covered = fields.Boolean(
        string='Covered by Time Off',
        compute='_compute_is_covered',
        store=True,
        help="Indicates whether this attendance issue has been covered "
             "by an approved time-off request.",
    )

    @api.depends('x_leave_ids', 'x_leave_ids.state')
    def _compute_is_covered(self):
        for att in self:
            att.x_is_covered = bool(
                att.x_leave_ids.filtered(lambda l: l.state == 'validate'))

    def _compute_display_name(self):
        for rec in self:
            date_str = rec.check_in.strftime('%Y-%m-%d') if rec.check_in else 'No Date'
            issues = []
            details = []

            if rec.x_is_absent:
                issues.append('Absent')
                details.append('Full Day')
            if rec.x_late_minutes > 0:
                issues.append('Late')
                details.append(f'{rec.x_late_minutes:.0f} min')
            if rec.x_early_leave_minutes > 0:
                issues.append('Early Leave')
                details.append(f'{rec.x_early_leave_minutes:.0f} min')

            issue_str = ', '.join(issues) if issues else 'No Issue'
            detail_str = ', '.join(details) if details else ''

            rec.display_name = f"{date_str} - {issue_str} - {detail_str}" if detail_str else f"{date_str} - {issue_str}"
