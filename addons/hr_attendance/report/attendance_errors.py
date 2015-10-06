# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import time
from odoo import api, models


class ReportHrAttendanceerrors(models.AbstractModel):
    _name = 'report.hr_attendance.report_attendanceerrors'
    _inherit = 'report.abstract_report'
    _template = 'hr_attendance.report_attendanceerrors'

    def _get_employees(self, emp_ids):
        return self.env['hr.employee'].browse(emp_ids)

<<<<<<< HEAD
=======
    @api.multi
>>>>>>> 5f2cea5... [IMP] hr_attendance: imporved the attendace error report
    def _lst(self, employee_id, dt_from, dt_to, max):
        self.env.cr.execute("select name as date, create_date, action, create_date-name as delay from hr_attendance where employee_id=%s and to_char(name, 'YYYY-mm-dd')<=%s and to_char(name, 'YYYY-mm-dd')>=%s and action IN (%s, %s) order by name", (employee_id, dt_to, dt_from, 'sign_in', 'sign_out'))
        res = self.env.cr.dictfetchall()
        for r in res:
            if r['action'] == 'sign_out':
                r['delay'] = -r['delay']
            temp = r['delay'].seconds
            r['delay'] = str(r['delay']).split('.')[0]
            if abs(temp) < max*60:
                r['delay2'] = r['delay']
            else:
                r['delay2'] = '/'
        return res

<<<<<<< HEAD
=======
    @api.multi
>>>>>>> 5f2cea5... [IMP] hr_attendance: imporved the attendace error report
    def _lst_total(self, employee_id, dt_from, dt_to, max):
        self.env.cr.execute("select name as date, create_date, action, create_date-name as delay from hr_attendance where employee_id=%s and to_char(name, 'YYYY-mm-dd')<=%s and to_char(name, 'YYYY-mm-dd')>=%s and action IN (%s, %s) order by name", (employee_id, dt_to, dt_from, 'sign_in', 'sign_out'))
        res = self.env.cr.dictfetchall()
        if not res:
            return ('/', '/')
        total2 = datetime.timedelta(seconds=0, minutes=0, hours=0)
        total = datetime.timedelta(seconds=0, minutes=0, hours=0)
        for r in res:
            if r['action'] == 'sign_out':
                r['delay'] = -r['delay']
            total += r['delay']
            if abs(r['delay'].seconds) < max*60:
                total2 += r['delay']

        result_dict = {'total': total and str(total).split('.')[0],
                       'total2': total2 and str(total2).split('.')[0]}
        return [result_dict]

    @api.multi
    def render_html(self, data):
        Report = self.env['report']
        report = Report._get_report_from_name('hr_attendance.report_attendanceerrors')
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'time': time,
            'lst': self._lst,
            'total': self._lst_total,
            'get_employees': self._get_employees,
        }
        return Report.render('hr_attendance.report_attendanceerrors', docargs)
