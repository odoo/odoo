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

import datetime
import time

from report import report_sxw

class report_hr_salary_employee_bymonth(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(report_hr_salary_employee_bymonth, self).__init__(cr, uid, name, context=context)

        self.localcontext.update({
            'time': time,
            'get_employee': self.get_employee,
            'get_periods': self.get_periods,
            'get_months_tol': self.get_months_tol,
            'get_total': self.get_total,
        })

        self.context = context
        self.mnths = []
        self.mnths_total = []
        self.total = 0.0

    def get_periods(self, form):
#       Get start year-month-date and end year-month-date
        first_year = int(form['start_date'][0:4])
        last_year = int(form['end_date'][0:4])

        first_month = int(form['start_date'][5:7])
        last_month = int(form['end_date'][5:7])
        no_months = (last_year-first_year) * 12 + last_month - first_month + 1
        current_month = first_month
        current_year = first_year

#       Get name of the months from integer
        mnth_name = []
        for count in range(0, no_months):
            m = datetime.date(current_year, current_month, 1).strftime('%b')
            mnth_name.append(m)
            self.mnths.append(str(current_month)+'-'+str(current_year))
            if current_month == 12:
                current_month = 0
                current_year = last_year
            current_month = current_month + 1
        for c in range(0, (12-no_months)):
            mnth_name.append('None')
            self.mnths.append('None')
        return [mnth_name]

    def get_employee(self, form):
        list1 = []
        list = []
        total_mnths=['Total', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        emp_obj = self.pool.get('hr.employee')
        emp_ids = form.get('employee_ids', [])
        employees  = emp_obj.browse(self.cr, self.uid, emp_ids, context=self.context)
        cnt = 1
        for emp_id in employees:
            list1.append(emp_id.name)
            total = 0.0
            for mnth in self.mnths:
                if mnth <> 'None':
                    if len(mnth) != 7:
                        mnth = '0' + str(mnth)
                    self.cr.execute('''select  sum(pl.total) 
                            from hr_payslip_line as pl \
                            left join hr_payslip as p on pl.slip_id = p.id \
                            left join hr_employee as emp on emp.id = p.employee_id \
                            left join resource_resource as r on r.id = emp.resource_id  \
                            where pl.code = 'NET' and p.state = 'done' and p.employee_id  = '''+str(emp_id.id)+''' \
                            and to_char(date_to,'mm-yyyy') like '%'''+mnth+'''%'
                            group by r.name, p.date_to,emp.id''')
                    salary = self.cr.fetchall()
                    if salary:
                        list1.append(salary[0][0])
                        total += salary[0][0]
                        total_mnths[cnt] = total_mnths[cnt] + salary[0][0]
                    else:
                        list1.append(0.00)
                else:
                    list1.append('')
                    total_mnths[cnt] = ''
                cnt = cnt + 1
            cnt = 1
            list1.append(total)
            list.append(list1)
            list1 = []
        self.mnths_total.append(total_mnths)
        return list

    def get_months_tol(self):
        return self.mnths_total

    def get_total(self):
        for item in self.mnths_total:
            for count in range(1, len(item)):
              if item[count] == '':
                  continue
              self.total += item[count]
        return self.total

report_sxw.report_sxw('report.salary.employee.bymonth', 'hr.salary.employee.month', 'l10n_in_hr_payroll/report/report_hr_salary_employee_bymonth.rml', parser=report_hr_salary_employee_bymonth, header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: