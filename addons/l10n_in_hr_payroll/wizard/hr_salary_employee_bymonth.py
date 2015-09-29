#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import fields, osv

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
        category_ids = self.pool.get('hr.salary.rule.category').search(cr, uid, [('code', '=', 'NET')], context=context)
        return category_ids and category_ids[0] or False

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

        res = self.read(cr, uid, ids, context=context)
        res = res and res[0] or {}
        datas.update({'form': res})
        return self.pool['report'].get_action(cr, uid, ids, 
                        'l10n_in_hr_payroll.report_hrsalarybymonth', 
                        data=datas, context=context)
