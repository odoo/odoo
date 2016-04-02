#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw

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
            self.mnths.append(str(current_month) + '-' + str(current_year))
            if current_month == 12:
                current_month = 0
                current_year = last_year
            current_month = current_month + 1
        for c in range(0, (12-no_months)):
            mnth_name.append('')
            self.mnths.append('')
        return [mnth_name]

    def get_salary(self, form, emp_id, emp_salary, total_mnths):
        category_id = form.get('category_id', [])
        category_id = category_id and category_id[0] or False
        self.cr.execute("select to_char(date_to,'mm-yyyy') as to_date ,sum(pl.total) \
                             from hr_payslip_line as pl \
                             left join hr_payslip as p on pl.slip_id = p.id \
                             left join hr_employee as emp on emp.id = p.employee_id \
                             left join resource_resource as r on r.id = emp.resource_id  \
                            where p.state = 'done' and p.employee_id = %s and pl.category_id = %s \
                            group by r.name, p.date_to,emp.id",(emp_id, category_id,))
        sal = self.cr.fetchall()
        salary = dict(sal)
        total = 0.0
        cnt = 0

        for month in self.mnths:
            if month <> '':
                if len(month) != 7:
                    month = '0' + str(month)
                if month in salary and salary[month]:
                    emp_salary.append(salary[month])
                    total += salary[month]
                    total_mnths[cnt] = total_mnths[cnt] + salary[month]
                else:
                    emp_salary.append(0.00)
            else:
                emp_salary.append('')
                total_mnths[cnt] = ''
            cnt = cnt + 1
        return emp_salary, total, total_mnths

    def get_employee(self, form):
        emp_salary = []
        salary_list = []
        total_mnths=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        emp_obj = self.pool.get('hr.employee')
        emp_ids = form.get('employee_ids', [])
        employees  = emp_obj.browse(self.cr, self.uid, emp_ids, context=self.context)

        for emp_id in employees:
            emp_salary.append(emp_id.name)
            total = 0.0
            emp_salary, total, total_mnths = self.get_salary(form, emp_id.id, emp_salary, total_mnths)
            emp_salary.append(total)
            salary_list.append(emp_salary)
            emp_salary = []
        self.mnths_total.append(total_mnths)
        return salary_list

    def get_months_tol(self):
        return self.mnths_total

    def get_total(self):
        for item in self.mnths_total:
            for count in range(1, len(item)):
              if item[count] == '':
                  continue
              self.total += item[count]
        return self.total

class wrapped_report_employee_salary_bymonth(osv.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_hrsalarybymonth'
    _inherit = 'report.abstract_report'
    _template = 'l10n_in_hr_payroll.report_hrsalarybymonth'
    _wrapped_report_class = report_hr_salary_employee_bymonth
