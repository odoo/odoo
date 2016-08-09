# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, models


class EmployeesYearlySalaryReport(models.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_hryearlysalary'

    def get_periods(self, form):
        self.mnths = []
#       Get start year-month-date and end year-month-date
        first_year = int(form['date_from'][0:4])
        last_year = int(form['date_to'][0:4])

        first_month = int(form['date_from'][5:7])
        last_month = int(form['date_to'][5:7])
        no_months = (last_year - first_year) * 12 + last_month - first_month + 1
        current_month = first_month
        current_year = first_year

#       Get name of the months from integer
        mnth_name = []
        for count in range(0, no_months):
            m = date(current_year, current_month, 1).strftime('%b')
            mnth_name.append(m)
            self.mnths.append(str(current_month) + '-' + str(current_year))
            if current_month == 12:
                current_month = 0
                current_year = last_year
            current_month = current_month + 1
        for c in range(0, (12 - no_months)):
            mnth_name.append('')
            self.mnths.append('')
        return [mnth_name]

    def get_employee(self, form):
        return self.env['hr.employee'].browse(form.get('employee_ids', []))

    def get_employee_detail(self, form, obj):
        self.allow_list = []
        self.deduct_list = []
        self.total = 0.00
        gross = False
        net = False

        payslip_lines = self.cal_monthly_amt(form, obj.id)
        for line in payslip_lines:
            for line[0] in line:
                if line[0][0] == "Gross":
                    gross = line[0]
                elif line[0][0] == "Net":
                    net = line[0]
                elif line[0][13] > 0.0 and line[0][0] != "Net":
                    self.total += line[0][len(line[0]) - 1]
                    self.allow_list.append(line[0])
                elif line[0][13] < 0.0:
                    self.total += line[0][len(line[0]) - 1]
                    self.deduct_list.append(line[0])
        if gross:
            self.allow_list.append(gross)
        if net:
            self.deduct_list.append(net)
        return None

    def cal_monthly_amt(self, form, emp_id):
        result = []
        res = []
        salaries = {}
        self.env.cr.execute('''SELECT rc.code, pl.name, sum(pl.total), \
                to_char(date_to,'mm-yyyy') as to_date  FROM hr_payslip_line as pl \
                LEFT JOIN hr_salary_rule_category AS rc on (pl.category_id = rc.id) \
                LEFT JOIN hr_payslip as p on pl.slip_id = p.id \
                LEFT JOIN hr_employee as emp on emp.id = p.employee_id \
                WHERE p.employee_id = %s \
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id,pl.name,p.date_to,rc.code \
                ORDER BY pl.sequence, rc.parent_id''', (emp_id,))
        salary = self.env.cr.fetchall()
        for category in salary:
            if category[0] not in salaries:
                salaries.setdefault(category[0], {})
                salaries[category[0]].update({category[1]: {category[3]: category[2]}})
            elif category[1] not in salaries[category[0]]:
                salaries[category[0]].setdefault(category[1], {})
                salaries[category[0]][category[1]].update({category[3]: category[2]})
            else:
                salaries[category[0]][category[1]].update({category[3]: category[2]})

        categories = self.env['hr.salary.rule.category'].search([]).mapped('code')
        for code in categories:
            if code in salaries:
                res = self.salary_list(salaries[code])
            result.append(res)
        return result

    def salary_list(self, salaries):
        cat_salary_all = []
        for category_name, amount in salaries.items():
            cat_salary = []
            total = 0.0
            cat_salary.append(category_name)
            for mnth in self.mnths:
                if mnth != 'None':
                    if len(mnth) != 7:
                        mnth = '0' + str(mnth)
                    if mnth in amount and amount[mnth]:
                        cat_salary.append(amount[mnth])
                        total += amount[mnth]
                    else:
                        cat_salary.append(0.00)
                else:
                    cat_salary.append('')
            cat_salary.append(total)
            cat_salary_all.append(cat_salary)
        return cat_salary_all

    def get_allow(self):
        return self.allow_list

    def get_deduct(self):
        return self.deduct_list

    def get_total(self):
        return self.total

    @api.model
    def render_html(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': docids,
            'doc_model': model,
            'data': data,
            'docs': docs,
            'get_employee': self.get_employee,
            'get_employee_detail': self.get_employee_detail,
            'cal_monthly_amt': self.cal_monthly_amt,
            'get_periods': self.get_periods,
            'get_total': self.get_total,
            'get_allow': self.get_allow,
            'get_deduct': self.get_deduct,
        }
        return self.env['report'].render('l10n_in_hr_payroll.report_hryearlysalary', docargs)
