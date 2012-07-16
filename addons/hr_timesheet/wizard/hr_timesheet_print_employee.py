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

from osv import osv, fields
from tools.translate import _

class analytical_timesheet_employee(osv.osv_memory):
    _name = 'hr.analytical.timesheet.employee'
    _description = 'Print Employee Timesheet & Print My Timesheet'
    _columns = {
        'month': fields.selection([(x, datetime.date(2000, x, 1).strftime('%B')) for x in range(1, 13)],
                                  'Month', required=True),
        'year': fields.integer('Year', required=True),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True)

                }

    def _get_user(self, cr, uid, context=None):

        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        if not emp_id:
            raise osv.except_osv(_("Warning"), _("No employee defined for this user!"))
        return emp_id and emp_id[0] or False

    _defaults = {
         'month': lambda *a: datetime.date.today().month,
         'year': lambda *a: datetime.date.today().year,
         'employee_id': _get_user
             }

    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        data['employee_id'] = data['employee_id'][0]
        datas = {
             'ids': [],
             'model': 'hr.employee',
             'form': data
                 }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr.analytical.timesheet',
            'datas': datas,
            }
analytical_timesheet_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
