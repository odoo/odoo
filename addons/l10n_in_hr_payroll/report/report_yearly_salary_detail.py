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
import datetime
from report import report_sxw

class employees_yearly_salary_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(employees_yearly_salary_report, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_employee': self.get_employee,
            'get_employee_detail': self.get_employee_detail,
            'cal_monthly_amt': self.cal_monthly_amt,
            'get_periods': self.get_periods,
            'get_total': self.get_total,
            'get_allow': self.get_allow,
            'get_deduct': self.get_deduct,
        })

        self.context = context
        self.mnths = []
        self.allow_list = []
        self.deduct_list = []
        self.total = 0.00

    def get_periods(self, form):
#       Get start year-month-date and end year-month-date
        first_year = int(form['date_from'][0:4])
        last_year = int(form['date_to'][0:4])

        first_month = int(form['date_from'][5:7])
        last_month = int(form['date_to'][5:7])
        no_months = (last_year-first_year) * 12 + last_month - first_month + 1
        current_month = first_month
        current_year = first_year

#       Get name of the months from integer
        mnth_name = []
        for count in range(0, no_months):
            m = datetime.date(current_year, current_month, 1).strftime('%b')
            mnth_name.append(m)
            self.mnths.append(str(current_month) + '-' + str(current_year))
            if current_month == 12:
                current_month = 0
                current_year = last_year
            current_month = current_month + 1
        for c in range(0, (12-no_months)):
            mnth_name.append('None')
            self.mnths.append('None')
        return [mnth_name]

    def get_employee(self, form):
        result = []
        emp_obj = self.pool.get('hr.employee')
        emp_ids = form.get('employee_ids', [])
        result = emp_obj.browse(self.cr,self.uid, emp_ids, context=self.context)
        return result

    def get_employee_detail(self, form, obj):
        self.allow_list = []
        self.deduct_list = []
        self.total = 0.00

        #for Basic Salary
        res = self.cal_monthly_amt(form, obj.id)
        basic = res[0]
        self.total += basic[0][len(basic[0])-1]
        self.allow_list.append(basic[0])

        #for allowance
        allow = res[1]
        gross = res[3]
        for i in range(1, len(allow)+1):
            self.allow_list.append(allow[i-1])
            self.total += allow[i-1][len(allow[i-1])-1]
        self.total += gross[0][len(gross[0])-1]
        self.allow_list.append(gross[0])

        #for Deduction
        deduct = res[2] 
        net = res[4]
        for i in range(1, len(deduct)+1):
            self.deduct_list.append(deduct[i-1])
            self.total -= deduct[i-1][len(deduct[i-1])-1]
        self.total += net[0][len(net[0])-1]
        self.deduct_list.append(net[0])
        return None

    def cal_monthly_amt(self, form, emp_id):

        result = []
        salaries = {}
        tot = 0.0

        payslip_line_obj = self.pool.get('hr.payslip.line')

        line_ids = payslip_line_obj.search(self.cr, self.uid, [], context=self.context)
        lines  = payslip_line_obj.browse(self.cr, self.uid, line_ids, context=self.context)

        self.cr.execute('''SELECT rc.code, pl.name, sum(pl.total), \
                to_char(date_to,'mm-yyyy') as to_date  FROM hr_payslip_line as pl \
                LEFT JOIN hr_salary_rule_category AS rc on (pl.category_id = rc.id) \
                LEFT JOIN hr_payslip as p on pl.slip_id = p.id \
                LEFT JOIN hr_employee as emp on emp.id = p.employee_id \
                WHERE pl.id in %s and p.employee_id = %s \
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id,pl.name,p.date_to,rc.code \
                ORDER BY pl.sequence, rc.parent_id''',(tuple(line_ids),emp_id))
        sal = self.cr.fetchall()

        for x in sal:
            if x[0] == 'BASIC':
                if x[0] not in salaries:
                    salaries[x[0]] = {}
                    salaries[x[0]].update({x[1]: {x[3]: x[2]}})
                elif x[1] not in salaries[x[0]]:
                    salaries[x[0]][x[1]] = {}
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
                else:
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
            if x[0] == 'ALW':
                if x[0] not in salaries:
                    salaries[x[0]] = {}
                    salaries[x[0]].update({x[1]: {x[3]: x[2]}})
                elif x[1] not in salaries[x[0]]:
                    salaries[x[0]][x[1]] = {}
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
                else:
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
            if x[0] == 'DED':
                if x[0] not in salaries:
                    salaries[x[0]] = {}
                    salaries[x[0]].update({x[1]: {x[3]: x[2]}})
                elif x[1] not in salaries[x[0]]:
                    salaries[x[0]][x[1]] = {}
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
                else:
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
            if x[0] == 'GROSS':
                if x[0] not in salaries:
                    salaries[x[0]] = {}
                    salaries[x[0]].update({x[1]: {x[3]: x[2]}})
                elif x[1] not in salaries[x[0]]:
                    salaries[x[0]][x[1]] = {}
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
                else:
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
            if x[0] == 'NET':
                if x[0] not in salaries:
                    salaries[x[0]] = {}
                    salaries[x[0]].update({x[1]: {x[3]: x[2]}})
                elif x[1] not in salaries[x[0]]:
                    salaries[x[0]][x[1]] = {}
                    salaries[x[0]][x[1]].update({x[3]: x[2]})
                else:
                    salaries[x[0]][x[1]].update({x[3]: x[2]})

        for code in ['BASIC', 'ALW', 'DED', 'GROSS', 'NET']:
            if code in salaries:
                res = self.salary_list(salaries[code])
            else:
                res = []
            result.append(res)
        return result

    def salary_list(self, salaries):
        cnt = 0
        cat_salary_all = []
        for category_name,amount in salaries.items():
            cat_salary = []
            cnt += 1
            tot = 0.0
            cat_salary.append(category_name)
            for mnth in self.mnths:
                if mnth <> 'None':
                    if len(mnth) != 7:
                        mnth = '0' + str(mnth)
                    if mnth in amount and amount[mnth]:
                        cat_salary.append(amount[mnth])
                        tot += amount[mnth]
                    else:
                        cat_salary.append(0.00)
                else:
                    cat_salary.append('')
            cat_salary.append(tot)
            cat_salary_all.append(cat_salary)
        cnt = 1
        return cat_salary_all

    def get_allow(self):
        return self.allow_list

    def get_deduct(self):
        return self.deduct_list

    def get_total(self):
        return self.total

report_sxw.report_sxw('report.salary.detail.byyear', 'yearly.salary.detail', 'hr_payroll/report/report_yearly_salary_detail.rml', parser=employees_yearly_salary_report, header='internal landscape')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
