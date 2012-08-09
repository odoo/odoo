#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

import time

from osv import osv, fields

class hr_salary_employee_bymonth(osv.osv_memory):

    _name = 'hr.salary.employee.month'
    _description = 'Hr Salary Employee By Month Report'
    _columns = {
        'start_date': fields.date('Start Date', required=True),
        'end_date': fields.date('End Date', required=True),
        'employee_ids': fields.many2many('hr.employee', 'payroll_year_rel', 'payroll_year_id', 'employee_id', 'Employees', required=True),
        'category_id': fields.many2one('hr.salary.rule.category', 'Category', required=True),
    }

    def _get_default_category(self, cr, uid, context=None):
        return self.pool.get('hr.salary.rule.category').search(cr, uid, [('code', '=', 'NET')], context=context)

    _defaults = {
         'start_date': lambda *a: time.strftime('%Y-01-01'),
         'end_date': lambda *a: time.strftime('%Y-%m-%d'),
         'category_id': _get_default_category
    }

    def print_report(self, cr, uid, ids, context=None):
        """
         To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: return report
        """
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}

        res = self.read(cr, uid, ids, ['employee_ids', 'start_date', 'end_date'], context=context)
        res = res and res[0] or {}
        datas.update({'form': res})
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'salary.employee.bymonth',
            'datas': datas,
       }

hr_salary_employee_bymonth()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: