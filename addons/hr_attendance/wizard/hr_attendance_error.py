# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrAttendanceError(models.TransientModel):

    _name = 'hr.attendance.error'
    _description = 'Print Error Attendance Report'

    init_date = fields.Date('Starting Date', required=True, default=lambda *a: fields.Date.today())
    end_date = fields.Date('Ending Date', required=True, default=lambda *a: fields.Date.today())
    max_delay = fields.Integer('Maximum Tolerance (in minutes)', required=True, default=120,
                help="Allowed difference in minutes between the signin/signout and the timesheet computation for one sheet. Set this to 0 for no tolerance.")

    @api.multi
    def print_report(self):
        emp_ids = set()
        date_from = self.init_date
        date_to = self.end_date
        self.env.cr.execute("SELECT id FROM hr_attendance WHERE employee_id IN %s AND to_char(name, 'YYYY-mm-dd')<=%s AND to_char(name, 'YYYY-mm-dd')>=%s AND action IN %s ORDER BY name", (tuple(self.env.context['active_ids']), date_to, date_from, tuple(['sign_in', 'sign_out'])))
        attendance_ids = [x[0] for x in self.env.cr.fetchall()]
        if not attendance_ids:
            raise UserError(_('No records are found for your selection!'))
        for rec in self.env['hr.attendance'].browse(attendance_ids):
            emp_ids.add(rec.employee_id.id)
        datas = {'form': {'init_date': date_from, 'end_date': date_to,
                          'max_delay': self.max_delay, 'emp_ids': list(emp_ids)}}
        return self.env['report'].get_action(self, 'hr_attendance.report_attendanceerrors', data=datas)
