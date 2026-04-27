# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from collections import OrderedDict, defaultdict
from odoo import api, fields, models, _
from odoo.fields import Datetime



class L10nChIndividualAccount(models.Model):
    _inherit = 'l10n.ch.individual.account'

    def _get_rendering_data(self, employees):
        self.ensure_one()

        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', Datetime.now().replace(month=1, day=1, year=int(self.year))),
            ('date_from', '<=', Datetime.now().replace(month=12, day=31, year=int(self.year))),
            ('struct_id.code', '=', 'CHMONTHLYELM'),
        ])
        employees = list(payslips.employee_id) + [self.env['hr.employee']]
        lines = payslips.line_ids.filtered(lambda l: l.salary_rule_id.l10n_ch_code)
        is_lines = payslips.l10n_ch_is_log_line_ids

        rules = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
        rules_company = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for line in lines:
            employee_id = line.slip_id.employee_id
            if line.salary_rule_id.l10n_ch_code == "9041":
                rules[employee_id]["9041"][f'LAAC Salary - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["9041"][f'LAAC Salary - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
            elif line.salary_rule_id.l10n_ch_code == "9043":
                rules[employee_id]["9041"][f'LAAC Salary - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["9041"][f'LAAC Salary - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total
            elif line.salary_rule_id.l10n_ch_code == "5041":
                rules[employee_id]["5041"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["5041"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
            elif line.salary_rule_id.l10n_ch_code == "5043":
                rules[employee_id]["5041"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["5041"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_additional_accident_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total
            elif line.salary_rule_id.l10n_ch_code == "5045":
                rules[employee_id]["5045"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["5045"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
            elif line.salary_rule_id.l10n_ch_code == "5047":
                rules[employee_id]["5045"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["5045"][f'{line.name[:-2]} - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total

            elif line.salary_rule_id.l10n_ch_code == "9051":
                rules[employee_id]["9051"][f'IJM Salary - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["9051"][f'IJM Salary - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[0].solution_code}'][line.slip_id.date_from.month - 1] += line.total
            elif line.salary_rule_id.l10n_ch_code == "9053":
                rules[employee_id]["9051"][f'IJM Salary - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total
                rules_company["9051"][f'IJM Salary - Code {line.slip_id.l10n_ch_sickness_insurance_line_ids[1].solution_code}'][line.slip_id.date_from.month - 1] += line.total
            else:
                if line.salary_rule_id.l10n_ch_code not in ["9070", "9072", "9071", "9073", "9075", "5061", "5062", "5060"]:
                    rules[employee_id][line.salary_rule_id.l10n_ch_code][line.name][line.slip_id.date_from.month - 1] += line.total
                    rules_company[line.salary_rule_id.l10n_ch_code][line.name][line.slip_id.date_from.month - 1] += line.total

        for line in is_lines:
            employee_id = line.payslip_id.employee_id
            if line.code == "ISSALARY":
                rules[employee_id]["9070"][f'Source-Tax Salary - {line.source_tax_canton}-{line.is_code}'][line.payslip_id.date_from.month - 1] += line.amount
                rules_company["9070"][f'Source-Tax Salary - {line.source_tax_canton}-{line.is_code}'][line.payslip_id.date_from.month - 1] += line.amount
            if line.code == "ISDTSALARY":
                rules[employee_id]["9073"][f'Source-Tax Rate Determinant Salary - {line.source_tax_canton}'][line.payslip_id.date_from.month - 1] += line.amount
                rules_company["9073"][f'Source-Tax Rate Determinant Salary - {line.source_tax_canton}'][line.payslip_id.date_from.month - 1] += line.amount
            if line.code == "IS":
                rules[employee_id]["5060"][f'Source-Tax Amount - {line.source_tax_canton}-{line.is_code}'][line.payslip_id.date_from.month - 1] += -line.amount
                rules_company["5060"][f'Source-Tax Amount - {line.source_tax_canton}-{line.is_code}'][line.payslip_id.date_from.month - 1] += -line.amount

        result = {
            employee: {
                'year': self.year,
                'company': employee.company_id or self.company_id,
                'contract_type': employee.contract_id.contract_type_id.name or '',
                'job_title': employee.contract_id.job_id.name or '',
                'entry_date': employee.contract_id.date_start or '',
                'withdrawal_date': employee.contract_id.date_end or '',
                'work_adress': employee.contract_id.l10n_ch_location_unit_id.partner_id or '',
                'activity_rate': employee.contract_id.l10n_ch_current_occupation_rate or 0,
                'rules': sorted(
                    [
                        {
                            'code': code,
                            'name': name,
                            'monthly_values': [round(months.get(month, 0.0), 2) for month in range(12)] + [round(sum([months.get(month, 0.0) for month in range(12)]), 2)]
                        }
                        for code, names in (rules[employee].items() if employee else rules_company.items())
                        for name, months in names.items()
                    ],
                    key=lambda rule: rule['code']
                ),
            } for employee in employees
        }

        return result


    def _get_pdf_report(self):
        return self.env.ref('l10n_ch_hr_payroll.action_report_individual_account')
