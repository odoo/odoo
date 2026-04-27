# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_in(self, companies):
        account_codes = [
            "2101",   # Salary Expense
            "300001",  # House Rent Allowance Expense"
            "300002",  # Other Allowance Expense"
            "300003",  # Bonus to Employee Expense"
            "300004",  # Supplementary Allowance Expense"
            "300005",  # Performance Bonus"
            "300006",  # Employee Reimbursement Expense"
            "300007",  # Provident fund - Employee Payable"
            "300008",  # Provident fund - Employer Payable"
            "300009",  # Advance to Employee"
            "300010",  # Salary Exp Payable"
            "300011",  # Leave Travel Allowance Expense"
            "300012",  # Professional Tax Payable"
        ]
        default_account = False
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #           IN Employee Payroll Structure          #
        # ================================================ #

        basic_IN_emp_salary_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_in_hr_payroll.hr_payroll_structure_in_employee_salary').id),
            ('code', '=', 'BASIC')
        ], limit=1)
        rules_mapping[basic_IN_emp_salary_rule]['debit'] = '2101'

        hra_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_hra')
        rules_mapping[hra_IN_emp_salary_rule]['debit'] = '300001'

        std_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_std')
        rules_mapping[std_IN_emp_salary_rule]['debit'] = '300002'

        bonus_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_bonus')
        rules_mapping[bonus_IN_emp_salary_rule]['debit'] = '300003'

        spl_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_spl')
        rules_mapping[spl_IN_emp_salary_rule]['debit'] = "300004"

        performance_bolus_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_p_bonus')
        rules_mapping[performance_bolus_IN_emp_salary_rule]['debit'] = '300005'

        lta_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_lta')
        rules_mapping[lta_IN_emp_salary_rule]['debit'] = '300011'

        reimbursement_IN_salary_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_in_hr_payroll.hr_payroll_structure_in_employee_salary').id),
            ('code', '=', 'REIMBURSEMENT')
        ], limit=1)
        rules_mapping[reimbursement_IN_salary_rule]['debit'] = '300006'

        expenses_reimbursement_IN_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_expenses_reimbursement')
        rules_mapping[expenses_reimbursement_IN_salary_rule]['debit'] = '300006'

        pt_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.l10n_in_hr_salary_rule_pt')
        rules_mapping[pt_IN_emp_salary_rule]['debit'] = '300012'

        pf_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.hr_salary_rule_pf_with_pf')
        rules_mapping[pf_IN_emp_salary_rule]['debit'] = '300007'

        epf_IN_emp_salary_rule = self.env.ref('l10n_in_hr_payroll.hr_salary_rule_pfe_with_pf')
        rules_mapping[epf_IN_emp_salary_rule]['debit'] = '300008'

        attach_salary_IN_salary_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_in_hr_payroll.hr_payroll_structure_in_employee_salary').id),
            ('code', '=', 'ATTACH_SALARY')
        ], limit=1)
        rules_mapping[attach_salary_IN_salary_rule]['credit'] = '300009'

        Deduction_IN_salary_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_in_hr_payroll.hr_payroll_structure_in_employee_salary').id),
            ('code', '=', 'DEDUCTION')
        ], limit=1)
        rules_mapping[Deduction_IN_salary_rule]['credit'] = '2101'

        net_IN_salary_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_in_hr_payroll.hr_payroll_structure_in_employee_salary').id),
            ('code', '=', 'NET')
        ], limit=1)
        rules_mapping[net_IN_salary_rule]['credit'] = '300010'

        # ================================================ #
        #           IN Stipend Payroll Structure           #
        # ================================================ #

        net_IN_stipend_salary_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_in_hr_payroll.hr_payroll_structure_in_stipend').id),
            ('code', '=', 'NET')
        ], limit=1)
        rules_mapping[net_IN_stipend_salary_rule]['credit'] = '300010'

        self._configure_payroll_account(
            companies,
            "IN",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
