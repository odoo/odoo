# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta


from odoo import api, fields, models, _
from odoo.tools import format_date, SQL
from odoo.exceptions import UserError

class EmployeesYearlySalaryReport(models.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_hryearlysalary'
    _description = "Indian Yearly Salary Report"

    # YTI: This mess deserves a good cleaning

    def _get_periods_new(self, form):
        months = []
        # Get start year-month-date and end year-month-date
        first_year = int(form['year'])
        first_month = 1

        # Get name of the months from integer
        month_name = []
        for count in range(0, 12):
            m = format_date(self.env, date(first_year, first_month, 1), date_format='MMM')
            month_name.append(m)
            months.append(f"{first_month:02d}-{first_year}")
            if first_month == 12:
                first_month = 0
                first_year += 1
            first_month += 1
        return [month_name], months

    def _get_employee(self, form):
        return self.env['hr.employee'].browse(form.get('employee_ids', []))

    def _get_employee_detail_new(self, form, employee_id, months, date_from, date_to):
        structures_data = {}
        payslip_lines = self._cal_monthly_amt(form, employee_id, months, date_from, date_to)
        for structure_name, payslip_data in payslip_lines.items():
            allow_list = []
            deduct_list = []
            total = 0.0
            gross = False
            net = False
            for line in payslip_data:
                code = line[0]
                subline = line[1:]
                if code == "GROSS":
                    gross = [code, subline]
                elif code == "NET":
                    net = [code, subline]
                elif subline[-1] > 0.0 and code != "NET":
                    total += subline[-1]
                    allow_list.append([code, subline])
                elif subline[-1] < 0.0:
                    total += subline[-1]
                    deduct_list.append([code, subline])

            if gross:
                allow_list.append(gross)
            if net:
                deduct_list.append(net)

            structures_data[structure_name] = {
                'allow_list': allow_list,
                'deduct_list': deduct_list,
                'total': total,
            }

        return structures_data

    def _cal_monthly_amt(self, form, emp_id, months, date_from, date_to):
        result = {}
        salaries = {}

        self.env.cr.execute(SQL(
            """
                  SELECT src.code, pl.name, sum(pl.total), to_char(p.date_to,'mm-yyyy') as to_date, ps.name
                    FROM hr_payslip_line as pl
                    LEFT JOIN hr_salary_rule AS sr on sr.id = pl.salary_rule_id
                    LEFT JOIN hr_salary_rule_category AS src on (sr.category_id = src.id)
                    LEFT JOIN hr_payslip as p on pl.slip_id = p.id
                    LEFT JOIN hr_employee as e on e.id = p.employee_id
                    LEFT JOIN hr_payroll_structure as ps on ps.id = p.struct_id
                   WHERE p.employee_id = %(employee_id)s
                     AND p.state = 'paid'
                     AND p.date_from >= %(date_from)s AND p.date_to <= %(date_to)s
                   GROUP BY src.parent_id, pl.sequence, pl.id, sr.category_id, pl.name, p.date_to, src.code, ps.name
                   ORDER BY pl.sequence, src.parent_id
            """, employee_id=emp_id, date_from=date_from, date_to=date_to
        ))

        for category_code, item_name, amount, payslip_date, structure_name in self.env.cr.fetchall():
            salaries.setdefault(structure_name, {}).setdefault(category_code, {}).setdefault(item_name, {}).setdefault(payslip_date, 0.0)
            salaries[structure_name][category_code][item_name][payslip_date] += amount

        result = {key: self.salary_list(value, months) for key, value in salaries.items()}
        return result

    def salary_list(self, salaries, months):
        cat_salary_all = []
        for code, category_amount in salaries.items():
            for category_name, amount in category_amount.items():
                cat_salary = [code, category_name]
                total = 0.0
                for month in months:
                    if month != 'None':
                        if len(month) != 7:
                            month = '0' + str(month)
                        if amount.get(month):
                            cat_salary.append(amount[month])
                            total += amount[month]
                        else:
                            cat_salary.append(0.00)
                    else:
                        cat_salary.append('')
                cat_salary.append(total)
                cat_salary_all.append(cat_salary)
        return cat_salary_all

    @api.model
    def _get_report_values(self, docids, data=None):
        if not self.env.context.get('active_model') or not self.env.context.get('active_id'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        employees = self._get_employee(data['form'])
        month_name, months = self._get_periods_new(data['form'])
        date_from = fields.Date.today() + relativedelta(day=1, month=1, year=int(data['form']['year']))
        date_to = fields.Date.today() + relativedelta(day=31, month=12, year=int(data['form']['year']))

        employee_data = {}
        for employee in employees:
            structures_data = self._get_employee_detail_new(data['form'], employee.id, months, date_from, date_to)
            employee_data[employee.id] = structures_data
        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data,
            'docs': docs,
            'date_from': date_from,
            'date_to': date_to,
            'get_employee': self._get_employee,
            'get_periods': lambda form: month_name,
            'get_employee_detail_new': lambda emp_id: employee_data.get(emp_id, {}),
        }
