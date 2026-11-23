from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_is_attendance_sheet = fields.Boolean(
        string='Uses Attendance Sheet',
        default=False,
        groups='hr.group_hr_user',
        help='If checked, this employee\'s attendance is managed via '
             'the monthly attendance sheet by their manager, instead of '
             'biometric device punch-in/punch-out.',
    )

    def write(self, vals):
        """Auto-create current-month attendance sheet when the flag is turned ON."""
        # Detect employees that are being switched ON
        newly_enabled = self.env['hr.employee']
        if 'x_is_attendance_sheet' in vals and vals['x_is_attendance_sheet']:
            newly_enabled = self.filtered(lambda e: not e.x_is_attendance_sheet)

        res = super().write(vals)

        if newly_enabled:
            Sheet = self.env['ksw.attendance.sheet']
            today = fields.Date.context_today(self)
            month = str(today.month)
            year = today.year

            existing = Sheet.search([
                ('employee_id', 'in', newly_enabled.ids),
                ('month', '=', month),
                ('year', '=', year),
            ])
            existing_emp_ids = set(existing.mapped('employee_id').ids)

            for emp in newly_enabled:
                if emp.id not in existing_emp_ids:
                    Sheet.create({
                        'employee_id': emp.id,
                        'month': month,
                        'year': year,
                    })

        return res

