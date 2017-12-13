# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw


def format_timedelta(td):
    if td < datetime.timedelta(0):
        return '-' + format_timedelta(-td)
    else:
        return str(td).split('.')[0]

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
            delay = r['delay']
            # Remove microseconds from the delay
            delay = datetime.timedelta(delay.days, delay.seconds, 0)

            temp = delay.total_seconds()
            if r['action'] == 'sign_out':
                delay = -delay

            r['delay'] = format_timedelta(delay)

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
            delay = r['delay']
            # Remove the microseconds from the delay
            delay = datetime.timedelta(delay.days, delay.seconds, 0)

            if r['action'] == 'sign_out' and delay != datetime.timedelta(0):
                delay = -delay
            total += delay
            if abs(delay.total_seconds()) < max*60:
                total2 += delay

        result_dict = {
                'total': format_timedelta(total),
                'total2': format_timedelta(total2)
                }
        return [result_dict]



class report_hr_attendanceerrors(osv.AbstractModel):
    _name = 'report.hr_attendance.report_attendanceerrors'
    _inherit = 'report.abstract_report'
    _template = 'hr_attendance.report_attendanceerrors'
    _wrapped_report_class = attendance_print

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
