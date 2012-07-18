# -*- coding: utf-8 -*-
###############################################################################
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

import time

from osv import osv, fields

class salary_rule_bymonth(osv.osv_memory):
    _name = 'salary.rule.month'
#    _inherit = 'hr.employee'
    _description = 'Print Monthly Salary Rule Report'
    _columns = {
        'start_date': fields.date('Starting Date', required=True),
        'end_date': fields.date('Ending Date', required=True),
        'employee_ids': fields.many2many('hr.employee', 'payroll_year_rel','payroll_year_id','emp_id', 'Employees',required=True),
#        'rule_id': fields.many2one('hr.salary.rule.category', 'Rule Category', required=True),
    }
    _defaults = {
         'start_date': lambda *a: time.strftime('%Y-01-01'),
         'end_date': lambda *a: time.strftime('%Y-%m-%d'),
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

        res = self.read(cr, uid, ids, ['employee_ids',  'start_date', 'end_date', ], context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['ids'] = res.get('employee_ids',[])
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'salary.rule.bymonth',
            'datas': datas,
       }

salary_rule_bymonth()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: