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

from osv import fields, osv

class yearly_salary_detail(osv.osv_memory):

   _name ='yearly.salary.detail'
   _description = 'Hr Salary Employee By Category Report'
   _columns = {
        'employee_ids': fields.many2many('hr.employee', 'payroll_emp_rel', 'payroll_id', 'emp_id', 'Employees', required=True),
        'date_from': fields.date('Start Date', required=True),
        'date_to': fields.date('End Date', required=True),
    }

   _defaults = {
        'date_from': lambda *a: time.strftime('%Y-01-01'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),

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

        res = self.read(cr, uid, ids, ['employee_ids', 'date_from', 'date_to'], context=context)
        res = res and res[0] or {}
        datas.update({'form': res})
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'salary.detail.byyear',
            'datas': datas,
       }

yearly_salary_detail()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
