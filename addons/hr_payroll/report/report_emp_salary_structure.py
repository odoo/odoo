#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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
from report import report_sxw

class salary_structure_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
          super(salary_structure_report, self).__init__(cr, uid, name, context)
          self.localcontext.update({
            'time': time,
            'get_type':self.get_type,
            #'get_contract':self.get_contract,
            'get_line_amount_type':self.get_line_amount_type,
            'get_line_type':self.get_line_type,
            'get_line_amount_symbol':self.get_line_amount_symbol
          })

#    def get_contract(self,emp):
#        curr_date = "'"+time.strftime("%Y-%m-%d")+"'"
#        sql_req= '''
#            SELECT c.id as id, c.wage as wage, struct_id as struct
#            FROM hr_contract c
#              LEFT JOIN hr_employee emp on (c.employee_id=emp.id)
#              LEFT JOIN hr_contract_wage_type cwt on (cwt.id = c.wage_type_id)
#              LEFT JOIN hr_contract_wage_type_period p on (cwt.period_id = p.id)
#            WHERE
#              (emp.id=%s) AND
#              (date_start <= %s) AND
#              (date_end IS NULL OR date_end >= %s)
#            LIMIT 1
#            '''%(emp.id, curr_date, curr_date)
#        self.cr.execute(sql_req)
#        contract_id = self.cr.dictfetchone()
#        if not contract_id:
#            return []
#        contract = self.pool.get('hr.contract').browse(self.cr, self.uid, [contract_id['id']])
#        return contract

    def get_type(self,type):
        return type[0].swapcase() + type[1:] +' Salary'

    def get_line_amount_type(self,amount_type):
        if amount_type == 'per':
            return 'Percent(%)'
        else:
            return 'Fixed'

    def get_line_amount_symbol(self,amount_type):
        if amount_type != 'per':
            return self.pool.get('res.users').browse(self.cr, self.uid,self.uid).company_id.currency_id.symbol

    def get_line_type(self,type):
        if type == 'allounce':
            return 'Allowance'
        elif type == 'deduction':
            return 'Deduction'
        elif type == 'advance':
            return 'Advance'
        elif type == 'loan':
            return 'Loan'
        elif type == 'otherpay':
            return 'Other Payment'
        else:
            return 'Other Deduction'

report_sxw.report_sxw('report.salary.structure', 'hr.employee', 'hr_payroll/report/report_emp_salary_structure.rml', parser=salary_structure_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
