# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw


class attendance_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(attendance_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'lst': self._lst,
            'total': self._lst_total,
            'get_employees':self._get_employees,
        })

    def _get_employees(self, emp_ids):
        emp_obj_list = self.pool.get('hr.employee').browse(self.cr, self.uid, emp_ids)
        return emp_obj_list

    def _lst(self, employee_id, dt_from, dt_to, max, *args):
        self.cr.execute("select name as date, create_date, action, create_date-name as delay from hr_attendance where employee_id=%s and to_char(name,'YYYY-mm-dd')<=%s and to_char(name,'YYYY-mm-dd')>=%s and action IN (%s,%s) order by name", (employee_id, dt_to, dt_from, 'sign_in', 'sign_out'))
        res = self.cr.dictfetchall()
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

    def _lst_total(self, employee_id, dt_from, dt_to, max, *args):
        self.cr.execute("select name as date, create_date, action, create_date-name as delay from hr_attendance where employee_id=%s and to_char(name,'YYYY-mm-dd')<=%s and to_char(name,'YYYY-mm-dd')>=%s and action IN (%s,%s) order by name", (employee_id, dt_to, dt_from, 'sign_in', 'sign_out'))
        res = self.cr.dictfetchall()
        if not res:
            return ('/','/')
        total2 = datetime.timedelta(seconds = 0, minutes = 0, hours = 0)
        total = datetime.timedelta(seconds = 0, minutes = 0, hours = 0)
        for r in res:
            if r['action'] == 'sign_out':
                r['delay'] = -r['delay']
            total += r['delay']
            if abs(r['delay'].seconds) < max*60:
                total2 += r['delay']

        result_dict = {
                'total': total and str(total).split('.')[0],
                'total2': total2  and str(total2).split('.')[0]
                }
        return [result_dict]


class report_hr_attendanceerrors(osv.AbstractModel):
    _name = 'report.hr_attendance.report_attendanceerrors'
    _inherit = 'report.abstract_report'
    _template = 'hr_attendance.report_attendanceerrors'
    _wrapped_report_class = attendance_print
