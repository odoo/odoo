#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class hr_employee(osv.osv):
    '''
    Employee
    '''

    _inherit = 'hr.employee'
    _description = 'Employee'

    def _calculate_total_wage(self, cr, uid, ids, name, args, context):
        if not ids: return {}
        res = {}
        current_date = datetime.now().strftime('%Y-%m-%d')
        for employee in self.browse(cr, uid, ids, context=context):
            if not employee.contract_ids:
                res[employee.id] = {'basic': 0.0}
                continue
            cr.execute( 'SELECT SUM(wage) '\
                        'FROM hr_contract '\
                        'WHERE employee_id = %s '\
                        'AND date_start <= %s '\
                        'AND (date_end > %s OR date_end is NULL)',
                         (employee.id, current_date, current_date))
            result = dict(cr.dictfetchone())
            res[employee.id] = {'basic': result['sum']}
        return res

    def _payslip_count(self, cr, uid, ids, field_name, arg, context=None):
        Payslip = self.pool['hr.payslip']
        return {
            employee_id: Payslip.search_count(cr,uid, [('employee_id', '=', employee_id)], context=context)
            for employee_id in ids
        }

    _columns = {
        'slip_ids':fields.one2many('hr.payslip', 'employee_id', 'Payslips', required=False, readonly=True),
        'total_wage': fields.function(_calculate_total_wage, method=True, type='float', string='Total Basic Salary', digits_compute=dp.get_precision('Payroll'), help="Sum of all current contract's wage of employee."),
        'payslip_count': fields.function(_payslip_count, type='integer', string='Payslips', groups="base.group_hr_user"),
    }
