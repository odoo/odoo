# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_mx(self, companies):
        account_codes = [
            "601.01.01",  # Gross
            "216.01.01",  # ISR
            "216.11.01",  # IMSS
            "210.01.01",  # Net
        ]
        default_account = '210.01.01'
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #          MX Employee Payroll Structure           #
        # ================================================ #

        basic_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary').id),
            ('code', '=', 'GROSS')
        ])
        rules_mapping[basic_rule]['debit'] = '601.01.01'

        isr_rule = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_isr')
        rules_mapping[isr_rule]['debit'] = '216.01.01'

        imss_rule = self.env.ref('l10n_mx_hr_payroll.l10n_mx_social_security_total_employee')
        rules_mapping[imss_rule]['credit'] = '216.11.01'

        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net_rule]['credit'] = '210.01.01'

        # ================================================ #
        #          MX Christmas Pay Payroll Structure      #
        # ================================================ #

        basic_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_christmas_bonus').id),
            ('code', '=', 'GROSS')
        ])
        rules_mapping[basic_rule]['debit'] = '601.01.01'

        isr_rule = self.env.ref('l10n_mx_hr_payroll.l10n_mx_christmas_bonus_isr')
        rules_mapping[isr_rule]['debit'] = '216.01.01'

        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_christmas_bonus').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net_rule]['credit'] = '210.01.01'

        self._configure_payroll_account(
            companies,
            "MX",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
