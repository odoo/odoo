# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_hk(self, companies):
        account_codes = [
            '221001',   # MPF (Employer)
            '221002',   # MPF (Employee)
            '2211',     # Account Payable
            '52',       # Expenses
            '5215',     # Sales Commission
            '5217',     # MPF Contribution
            '5218',     # Wages & Salaries
            '5219',     # Bonus Payment
        ]
        default_account = '5218'
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #          HK Employee Payroll Structure          #
        # ================================================ #

        basic_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id),
            ('code', '=', 'BASIC')
        ])
        rules_mapping[basic_rule]['credit'] = '5218'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_fixed_commission')
        rules_mapping[rule]['credit'] = '5215'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_back_pay')
        rules_mapping[rule]['credit'] = '5218'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_internet')
        rules_mapping[rule]['credit'] = '52'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_end_of_year_payment')
        rules_mapping[rule]['credit'] = '5219'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_eemc')
        rules_mapping[rule]['credit'] = '221002'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_ermc')
        rules_mapping[rule]['credit'] = '221001'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_eevc')
        rules_mapping[rule]['credit'] = '221002'

        rule = self.env.ref('l10n_hk_hr_payroll.cap57_employees_salary_ervc')
        rules_mapping[rule]['credit'] = '221001'

        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net_rule]['credit'] = '2211'

        self._configure_payroll_account(
            companies,
            "HK",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
