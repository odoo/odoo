# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class hr_attendance_error(osv.osv_memory):

    _name = 'hr.attendance.error'
    _description = 'Print Error Attendance Report'
    _columns = {
        'init_date': fields.date('Starting Date', required=True),
        'end_date': fields.date('Ending Date', required=True),
        'max_delay': fields.integer('Maximum Tolerance (in minutes)', required=True,
            help="Allowed difference in minutes between the signin/signout and the timesheet computation for one sheet. Set this to 0 for no tolerance.")
    }
    _defaults = {
         'init_date': lambda *a: time.strftime('%Y-%m-%d'),
         'end_date': lambda *a: time.strftime('%Y-%m-%d'),
         'max_delay': 120,
    }

    def print_report(self, cr, uid, ids, context=None):
        emp_ids = []
        data_error = self.read(cr, uid, ids, context=context)[0]
        date_from = data_error['init_date']
        date_to = data_error['end_date']
        cr.execute("SELECT id FROM hr_attendance WHERE employee_id IN %s AND to_char(name,'YYYY-mm-dd')<=%s AND to_char(name,'YYYY-mm-dd')>=%s AND action IN %s ORDER BY name" ,(tuple(context['active_ids']), date_to, date_from, tuple(['sign_in','sign_out'])))
        attendance_ids = [x[0] for x in cr.fetchall()]
        if not attendance_ids:
            raise UserError(_('No records are found for your selection!'))
        attendance_records = self.pool.get('hr.attendance').browse(cr, uid, attendance_ids, context=context)

        for rec in attendance_records:
            if rec.employee_id.id not in emp_ids:
                emp_ids.append(rec.employee_id.id)
        data_error['emp_ids'] = emp_ids
        datas = {
             'ids': [],
             'model': 'hr.employee',
             'form': data_error
        }
        return self.pool['report'].get_action(
            cr, uid, [], 'hr_attendance.report_attendanceerrors', data=datas, context=context
        )
