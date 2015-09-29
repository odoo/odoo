#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import fields, osv

class yearly_salary_detail(osv.osv_memory):

   _name ='yearly.salary.detail'
   _description = 'Hr Salary Employee By Category Report'
   _columns = {
        'employee_ids': fields.many2many('hr.employee', 'payroll_emp_rel', 'payroll_id', 'employee_id', 'Employees', required=True),
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

        res = self.read(cr, uid, ids, context=context)
        res = res and res[0] or {}
        datas.update({'form':res})
        return self.pool['report'].get_action(cr, uid, ids, 'l10n_in_hr_payroll.report_hryearlysalary', data=datas, context=context)
