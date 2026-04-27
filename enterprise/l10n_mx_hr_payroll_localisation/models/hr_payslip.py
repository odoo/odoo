# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from dateutil.relativedelta import relativedelta
from datetime import date
import calendar

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_mx_daily_salary = fields.Float('MX: Daily Salary', compute='_compute_daily_salary')
    l10n_mx_years_worked = fields.Integer('MX: Years Worked', compute='_compute_integration_factor')
    l10n_mx_days_of_year = fields.Integer('MX: Days of the Year', compute='_compute_days_of_year')
    l10n_mx_integration_factor = fields.Float('MX: Integration Factor', compute='_compute_integration_factor')

    @api.depends('contract_id')
    def _compute_daily_salary(self):
        for payslip in self:
            payslip.l10n_mx_daily_salary = payslip.contract_id._get_contract_wage() / payslip._rule_parameter('l10n_mx_days_per_month')

    @api.depends('date_to')
    def _compute_days_of_year(self):
        for payslip in self:
            year = payslip.date_to.year
            payslip.l10n_mx_days_of_year = (date(year, 12, 31) - date(year, 1, 1)).days + 1

    @api.depends('l10n_mx_days_of_year', 'date_from', 'date_to', 'contract_id')
    def _compute_integration_factor(self):
        for payslip in self:
            start_date = payslip.employee_id.first_contract_date
            if not start_date:
                payslip.l10n_mx_integration_factor = 1
                payslip.l10n_mx_years_worked = 0
                continue
            payslip.l10n_mx_years_worked = payslip.date_to.year - start_date.year
            if start_date <= payslip.date_to + relativedelta(year=start_date.year):
                payslip.l10n_mx_years_worked += 1
            holidays_count = payslip._rule_parameter('l10n_mx_holiday_tables')[payslip.l10n_mx_years_worked]
            holiday_bonus_factor = holidays_count * payslip.contract_id.l10n_mx_holiday_bonus_rate / 100

            number_of_days_year = payslip.l10n_mx_days_of_year
            payslip.l10n_mx_integration_factor = (holiday_bonus_factor + payslip._rule_parameter('l10n_mx_christmas_bonus') + number_of_days_year) / number_of_days_year

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_mx_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/salary_rules/hr_salary_rule_christmas_bonus_data.xml',
                'data/salary_rules/hr_salary_rule_regular_pay_data.xml',
            ])]

    def _get_paid_amount(self):
        self.ensure_one()
        mx_payslip = self.struct_id.country_id.code == "MX"
        if not mx_payslip:
            return super()._get_paid_amount()

        if self.struct_id.code == "MX_REGULAR":
            coefficients = self._rule_parameter('l10n_mx_schedule_table')
            days_in_period = coefficients[self.contract_id.l10n_mx_schedule_pay_temp or 'monthly']

            start_date = max(self.date_from, self.contract_id.date_start)
            end_date = min(self.date_to, self.contract_id.date_end) if self.contract_id.date_end else self.date_to
            in_contract_days = (end_date - start_date).days + 1
            actual_period_days = (self.date_to - self.date_from).days + 1
            salary_factor = in_contract_days / actual_period_days

            return self.l10n_mx_daily_salary * days_in_period * salary_factor
        return super()._get_paid_amount()

    def _get_schedule_timedelta(self):
        if self.country_code == 'MX':

            if self.struct_id.code == "MX_REGULAR":
                schedule = self.contract_id.l10n_mx_schedule_pay_temp
                if schedule == '10_days':
                    return relativedelta(days=9)
                elif schedule == '14_days':
                    return relativedelta(days=13)
                elif schedule == 'bi_weekly':
                    days_in_month = calendar.monthrange(self.date_from.year, self.date_from.month)[1]
                    return relativedelta(day=15 if self.date_from.day <= 15 else days_in_month)
                elif schedule == 'bi_monthly':
                    return relativedelta(months=2, days=-1)

            elif self.struct_id.code in ["MX_CHRISTMAS", "MX_PTU"]:
                return relativedelta(day=31, month=12)

        return super()._get_schedule_timedelta()

    def _get_schedule_period_start(self):
        if self.country_code == 'MX':
            today = date.today()

            if self.struct_id.code == "MX_REGULAR":
                schedule = self.contract_id.l10n_mx_schedule_pay_temp
                if schedule == '14_days':
                    week_day = today.weekday()
                    return today + relativedelta(days=-week_day)
                elif schedule == 'bi_weekly':
                    is_second_half = math.floor((today.day - 1) / 15)
                    return today.replace(day=16) if is_second_half else today.replace(day=1)
                elif schedule == 'bi_monthly':
                    current_year_slice = math.ceil(today.month / 2)
                    return today.replace(day=1, month=(current_year_slice - 1) * 2 + 1)

            elif self.struct_id.code in ["MX_CHRISTMAS", "MX_PTU"]:
                return today.replace(day=1, month=1)

        return super()._get_schedule_period_start()
