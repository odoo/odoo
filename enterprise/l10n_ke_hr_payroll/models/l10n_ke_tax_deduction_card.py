# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, _
from odoo.tools import format_date
from odoo.fields import Datetime


class L10nKeTaxDeductionCard(models.Model):
    _name = 'l10n_ke.tax.deduction.card'
    _inherit = 'hr.payroll.declaration.mixin'
    _description = 'HR Tax Deduction Card Report By Employee'

    name = fields.Char(
        string="Description", required=True, compute='_compute_name', readonly=False, store=True)

    def _country_restriction(self):
        return 'KE'

    @api.depends('year')
    def _compute_name(self):
        for sheet in self:
            sheet.name = _('Tax Deduction Cards - Year %s', sheet.year)

    def action_generate_declarations(self):
        for sheet in self:
            all_payslips = self.env['hr.payslip'].search([
                ('date_to', '<=', datetime.date(int(sheet.year), 12, 31)),
                ('date_from', '>=', datetime.date(int(sheet.year), 1, 1)),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', sheet.company_id.id),
            ])
            all_employees = all_payslips.employee_id
            sheet.write({
                'line_ids': [(5, 0, 0)] + [(0, 0, {
                    'employee_id': employee.id,
                    'res_model': 'l10n_ke.tax.deduction.card',
                    'res_id': sheet.id,
                }) for employee in all_employees]
            })
        return super().action_generate_declarations()

    def _get_rendering_data(self, employees):
        self.ensure_one()

        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', Datetime.now().replace(month=1, day=1, year=int(self.year))),
            ('date_from', '<=', Datetime.now().replace(month=12, day=31, year=int(self.year))),
            '|',
            ('struct_id.country_id', '=', False),
            ('struct_id.country_id.code', '=', "KE"),
        ])
        employees = payslips.employee_id
        result = {
            employee: {
                'p9_lines': [{
                    'month': format_date(self.env, Datetime.now().replace(day=1, month=i + 1, year=int(self.year)), date_format='MMMM') if i < 12 else _('TOTAL'),
                    'basic_salary': 0,
                    'benefits_non_cash': 0,
                    'value_of_quarter': 0,
                    'total_gross_pay': 0,
                    'defined_contribution_retirement_scheme_1': 0,
                    'defined_contribution_retirement_scheme_2': 0,
                    'defined_contribution_retirement_scheme_3': 0,
                    'owner_occupied_interest': 0,
                    'retirement_contribution_and_owner_occupied_interest': 0,
                    'chargeable_pay': 0,
                    'tax_charged': 0,
                    'personal_relief': 0,
                    'insurance_relief': 0,
                    'paye_tax': 0,
                } for i in range(13)],  # one line per month + one line stating the total
                'year': int(self.year),
            } for employee in employees
        }

        payslip_line_values = payslips._get_line_values([
            'BASIC',
            'NON_CASH_BENEFIT',
            'UNTAXED_ALLOWANCE',
            'TAXED_ALLOWANCE',
            'GROSS',
            'NSSF_AMOUNT',
            'MORTGAGE',
            'PENSION',
            'GROSS_TAXABLE',
            'INSURANCE_RELIEF',
            'PERS_RELIEF',
            'PAYE',
            'INCOME_TAX'])
        for payslip in payslips:
            pension_max = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_ke_pension_alw_max', payslip.date_to)
            line = result[payslip.employee_id]['p9_lines'][payslip.date_from.month - 1]
            line_total = result[payslip.employee_id]['p9_lines'][12]
            pid = payslip.id
            values_dict = {
                'month': format_date(self.env, payslip.date_from, date_format='MMMM'),
                'basic_salary': payslip_line_values['BASIC'][pid]['total'],
                'benefits_non_cash': payslip_line_values['NON_CASH_BENEFIT'][pid]['total'],
                'value_of_quarter': payslip_line_values['UNTAXED_ALLOWANCE'][pid]['total'] + payslip_line_values['TAXED_ALLOWANCE'][pid]['total'],
                'total_gross_pay': payslip_line_values['GROSS'][pid]['total'],
                'defined_contribution_retirement_scheme_1': 0.3 * payslip_line_values['BASIC'][pid]['total'],
                'defined_contribution_retirement_scheme_2': payslip_line_values['NSSF_AMOUNT'][pid]['total'],
                'defined_contribution_retirement_scheme_3': pension_max,
                'owner_occupied_interest': payslip_line_values['MORTGAGE'][pid]['total'],
                'retirement_contribution_and_owner_occupied_interest': payslip_line_values['PENSION'][pid]['total'],
                'chargeable_pay': payslip_line_values['GROSS_TAXABLE'][pid]['total'],
                'tax_charged': payslip_line_values['INCOME_TAX'][pid]['total'],
                'personal_relief': -payslip_line_values['PERS_RELIEF'][pid]['total'],
                'insurance_relief': -payslip_line_values['INSURANCE_RELIEF'][pid]['total'],
                'paye_tax': payslip_line_values['PAYE'][pid]['total'],
            }
            for value in values_dict:
                if value == 'month':
                    line[value] = values_dict[value]
                    line_total[value] = 'TOTAL'
                else:
                    line[value] += values_dict[value]
                    line_total[value] += values_dict[value]

        return result

    def _get_pdf_report(self):
        return self.env.ref('l10n_ke_hr_payroll.action_report_tax_deduction_card')

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        return _('%(employee)s-tax-deduction-card-%(year)s', employee=employee.name, year=self.year)
