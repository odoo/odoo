# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class HrEmployee(models.Model):
    _inherit = 'hr.payslip'

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_lu_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/hr_salary_rule_data.xml',
            ])]

    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()
        lu_companies = self.env.companies.filtered(lambda c: c.country_id.code == 'LU')
        if lu_companies:
            # Tax Classification
            invalid_employees = self.env['hr.employee'].search([
                ('l10n_lu_tax_classification', '=', False),
                ('company_id', 'in', lu_companies.ids)
            ])
            if invalid_employees:
                invalid_employees_str = _('Employees without a defined tax classification')
                res.append({
                    'string': invalid_employees_str,
                    'count': len(invalid_employees),
                    'action': self._dashboard_default_action(invalid_employees_str, 'hr.employee', invalid_employees.ids),
                })
        return res

    def _get_lux_tax(self, localdict):
        self.ensure_one()
        # Source: https://impotsdirects.public.lu/fr/baremes.html#Ex
        def _find_rate(x, rates):
            for low, high, rate, adjustment in rates:
                if low <= x <= high:
                    return rate, adjustment
            return 0, 0

        categories = localdict['categories']
        employee = self.employee_id
        taxable_amount = categories['TAXABLE']
        # Round to the lower 5 euros multiple
        taxable_amount -= taxable_amount % 5

        tax_amount = 0.0

        if employee.l10n_lu_tax_classification:
            rates = self._rule_parameter(f'l10n_lu_withholding_taxes_{employee.l10n_lu_tax_classification}')
            threshold, threshold_adjustment = self._rule_parameter(f'l10n_lu_withholding_taxes_threshhold_{employee.l10n_lu_tax_classification}')
        else:
            return 0.0

        rate, adjustment = _find_rate(taxable_amount, rates)
        tax_amount = taxable_amount * rate - adjustment
        tax_amount -= tax_amount % 0.10
        if taxable_amount <= threshold:
            tax_amount *= 1.07
        else:
            tax_amount += tax_amount * 0.09 - threshold_adjustment
        tax_amount -= tax_amount % 0.10

        if tax_amount < 1.00:
            return 0.0
        return - tax_amount
