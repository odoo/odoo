# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_mx(self, companies):
        account_codes = [
            "110.01.01",  # Employment Subsidy to Apply

            "201.01.02",  # Employee Reimbursement
            "205.06.02",  # Other Various Short-Term Credits (Fonacot)
            "210.01.01",  # Provision for Wages and Salaries to Pay
            "210.02.01",  # Provision for Vacation to Pay
            "210.03.01",  # Provision for Bonus to Pay
            "210.04.01",  # Provision for Savings Fund to Pay
            "211.01.01",  # Provision for Employer IMSS to Pay
            "211.02.01",  # Provision for SAR to Pay
            "211.03.01",  # Provision for Infonavit to Pay
            "216.01.01",  # ISR Income Taxes
            "216.11.01",  # IMSS Withholding for Workers

            "601.01.01",  # Wages and Salaries
            "601.06.01",  # Vacations
            "601.07.01",  # Holiday Bonus
            "601.12.01",  # Bonus
            "601.15.01",  # Pantry
            "601.16.01",  # Transport (Support)
            "601.16.02",  # Transport (Gasoline Vouchers)
            "601.19.01",  # Savings Fund
            "601.26.01",  # IMSS Quota
            "601.27.01",  # Contributions to Infonavit
            "601.28.01",  # Contributions to the SAR
            "601.74.01",  # Commissions on Sales
        ]
        default_account = '210.01.01'
        rules_mapping = defaultdict(dict)

        # =============================== #
        #          MX Regular Pay         #
        # =============================== #

        gross_without_holidays = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_bruto')
        rules_mapping[gross_without_holidays]['debit'] = '601.01.01'

        holidays_on_time = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_holidays_on_time')
        rules_mapping[holidays_on_time]['debit'] = '210.02.01'

        gasoline_period = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_gasoline_period')
        rules_mapping[gasoline_period]['debit'] = '601.16.02'

        transport_period = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_transport_period')
        rules_mapping[transport_period]['debit'] = '601.16.01'

        meal_voucher_period = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_meal_voucher_period')
        rules_mapping[meal_voucher_period]['debit'] = '601.15.01'

        holiday_bonus = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_holiday_bonus')
        rules_mapping[holiday_bonus]['debit'] = '210.02.01'

        discount_absence = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_discount_for_absence')
        rules_mapping[discount_absence]['debit'] = '601.01.01'

        imss_disabilities = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_imss_disabilities')
        rules_mapping[imss_disabilities]['debit'] = '601.01.01'

        savings_fund_employer_alw = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_employer_savings_fund_alw')
        rules_mapping[savings_fund_employer_alw]['debit'] = '601.19.01'

        reimbursement = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary').id),
            ('code', '=', 'REIMBURSEMENT')
        ])
        rules_mapping[reimbursement]['debit'] = '201.01.02'

        expenses = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_expenses')
        rules_mapping[expenses]['debit'] = '201.01.02'

        commissions = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_commissions')
        rules_mapping[commissions]['debit'] = '601.74.01'

        bonus = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_bonus')
        rules_mapping[bonus]['debit'] = '601.01.01'

        isr = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_isr')
        rules_mapping[isr]['debit'] = '216.01.01'

        isr_holiday_bonus = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_isr_holiday_bonus_tax')
        rules_mapping[isr_holiday_bonus]['debit'] = '216.01.01'

        savings_fund_employee = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_savings_fund')
        rules_mapping[savings_fund_employee]['debit'] = '210.04.01'

        savings_fund_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_employer_savings_fund')
        rules_mapping[savings_fund_employer]['debit'] = '210.04.01'

        subsidy = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_subsidy')
        rules_mapping[subsidy]['debit'] = '110.01.01'

        infonavit = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_infonavit')
        rules_mapping[infonavit]['debit'] = '211.03.01'

        fonacot = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_fonacot')
        rules_mapping[fonacot]['debit'] = '205.06.02'

        imss_employee = self.env.ref('l10n_mx_hr_payroll.l10n_mx_social_security_total_employee')
        rules_mapping[imss_employee]['credit'] = '216.11.01'

        imss_work_risk_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_work_risk')
        rules_mapping[imss_work_risk_employer]['debit'] = '601.26.01'
        rules_mapping[imss_work_risk_employer]['credit'] = '211.01.01'

        imss_dis_fix_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_disease_maternity_fixed')
        rules_mapping[imss_dis_fix_employer]['debit'] = '601.26.01'
        rules_mapping[imss_dis_fix_employer]['credit'] = '211.01.01'

        imss_dis_add_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_disease_maternity_additional')
        rules_mapping[imss_dis_add_employer]['debit'] = '601.26.01'
        rules_mapping[imss_dis_add_employer]['credit'] = '211.01.01'

        imss_dis_med_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_disease_maternity_medical')
        rules_mapping[imss_dis_med_employer]['debit'] = '601.26.01'
        rules_mapping[imss_dis_med_employer]['credit'] = '211.01.01'

        imss_dis_mon_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_disease_maternity_money')
        rules_mapping[imss_dis_mon_employer]['debit'] = '601.26.01'
        rules_mapping[imss_dis_mon_employer]['credit'] = '211.01.01'

        imss_dis_lif_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_disability_life')
        rules_mapping[imss_dis_lif_employer]['debit'] = '601.26.01'
        rules_mapping[imss_dis_lif_employer]['credit'] = '211.01.01'

        imss_retire_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_retirement')
        rules_mapping[imss_retire_employer]['debit'] = '601.28.01'
        rules_mapping[imss_retire_employer]['credit'] = '211.02.01'

        imss_ceav_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_ceav')
        rules_mapping[imss_ceav_employer]['debit'] = '601.28.01'
        rules_mapping[imss_ceav_employer]['credit'] = '211.02.01'

        imss_nursery_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_imss_nursery')
        rules_mapping[imss_nursery_employer]['debit'] = '601.26.01'
        rules_mapping[imss_nursery_employer]['credit'] = '211.01.01'

        imss_infonavit_employer = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_infonavit')
        rules_mapping[imss_infonavit_employer]['debit'] = '601.27.01'
        rules_mapping[imss_infonavit_employer]['credit'] = '211.03.01'

        provision_period_christmas = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_period_provisions_christmas_bonus')
        rules_mapping[provision_period_christmas]['debit'] = '601.12.01'
        rules_mapping[provision_period_christmas]['credit'] = '210.03.01'

        provision_period_holiday = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_period_provisions_holiday_bonus')
        rules_mapping[provision_period_holiday]['debit'] = '601.07.01'
        rules_mapping[provision_period_holiday]['credit'] = '210.02.01'

        provision_period_vacation = self.env.ref('l10n_mx_hr_payroll.l10n_mx_regular_pay_period_provisions_vacations_bonus')
        rules_mapping[provision_period_vacation]['debit'] = '601.06.01'
        rules_mapping[provision_period_vacation]['credit'] = '210.02.01'

        net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net]['credit'] = '210.01.01'

        # =============================== #
        #        MX Christmas Bonus       #
        # =============================== #

        basic = self.env.ref('l10n_mx_hr_payroll.l10n_mx_christmas_bonus_basic')
        rules_mapping[basic]['debit'] = '210.03.01'

        isr = self.env.ref('l10n_mx_hr_payroll.l10n_mx_christmas_bonus_isr')
        rules_mapping[isr]['debit'] = '216.01.01'

        basic = self.env.ref('l10n_mx_hr_payroll.l10n_mx_christmas_bonus_net')
        rules_mapping[net]['credit'] = '210.01.01'

        self._configure_payroll_account(
            companies,
            "MX",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
