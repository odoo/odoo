# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from dateutil.relativedelta import relativedelta
from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('mx')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.mx'),
            structure=cls.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary'),
            structure_type=cls.env.ref('l10n_mx_hr_payroll.structure_type_employee_mx'),
            contract_fields={
                'wage': 50000.0,
                'date_start': date(2021, 5, 31),
            }
        )

    def test_regular_payslip(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 50000.0, 'HOLIDAY_TO_SUB': 0.0, 'GROSS_WITHOUT_HOLIDAY': 50000.0, 'HOLIDAYS_ON_TIME': 0.0, 'GROSS': 50000.0, 'ISR': -9466.99, 'INT_DAY_WAGE_BASE': 1734.97, 'INT_DAY_WAGE_OTHER': 0.0, 'INT_DAY_WAGE_COMMISSIONS': 0.0, 'INT_DAY_WAGE': 1734.97, 'RISK_IMSS_EMPLOYER': 268.92, 'DIS_FIX_IMSS_EMPLOYER': 656.05, 'DIS_ADD_IMSS_EMPLOYER': 485.5, 'DIS_ADD_IMSS_EMPLOYEE': -176.55, 'DIS_MED_IMSS_EMPLOYER': 564.73, 'DIS_MED_IMSS_EMPLOYEE': -201.69, 'DIS_MON_IMSS_EMPLOYER': 376.49, 'DIS_MON_IMSS_EMPLOYEE': -134.46, 'DIS_LIF_IMSS_EMPLOYER': 941.22, 'DIS_LIF_IMSS_EMPLOYEE': -336.15, 'RETIRE_IMSS_EMPLOYER': 1075.68, 'CEAV_IMSS_EMPLOYER': 2867.23, 'CEAV_IMSS_EMPLOYEE': -605.07, 'NURSERY_IMSS_EMPLOYER': 537.84, 'INFONAVIT_IMSS_EMPLOYER': 2689.21, 'IMSS_EMPLOYEE_TOTAL': 1453.92, 'IMSS_EMPLOYER_TOTAL': 10462.88, 'NET': 39079.09, 'PROVISIONS_CHRISTMAS_BONUS': 2117.49, 'PERIOD_PROVISIONS_CHRISTMAS_BONUS': 2117.49, 'PROVISIONS_HOLIDAY_BONUS': 0.0, 'PERIOD_PROVISIONS_HOLIDAY_BONUS': 0.0, 'PROVISIONS_VACATIONS_BONUS': 17850.64, 'PERIOD_PROVISIONS_VACATIONS_BONUS': 17850.64}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_isr_monthly_adjustment(self):
        self.contract.write({'l10n_mx_schedule_pay_temp': 'bi_weekly'})

        previous_payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 15))
        previous_payslip_results = {'BASIC': 25000.0, 'HOLIDAY_TO_SUB': 0.0, 'GROSS_WITHOUT_HOLIDAY': 25000.0, 'HOLIDAYS_ON_TIME': 0.0, 'GROSS': 25000.0, 'ISR': -4769.95, 'INT_DAY_WAGE_BASE': 1734.97, 'INT_DAY_WAGE_OTHER': 0.0, 'INT_DAY_WAGE_COMMISSIONS': 0.0, 'INT_DAY_WAGE': 1734.97, 'RISK_IMSS_EMPLOYER': 130.12, 'DIS_FIX_IMSS_EMPLOYER': 317.44, 'DIS_ADD_IMSS_EMPLOYER': 234.92, 'DIS_ADD_IMSS_EMPLOYEE': -85.43, 'DIS_MED_IMSS_EMPLOYER': 273.26, 'DIS_MED_IMSS_EMPLOYEE': -97.59, 'DIS_MON_IMSS_EMPLOYER': 182.17, 'DIS_MON_IMSS_EMPLOYEE': -65.06, 'DIS_LIF_IMSS_EMPLOYER': 455.43, 'DIS_LIF_IMSS_EMPLOYEE': -162.65, 'RETIRE_IMSS_EMPLOYER': 520.49, 'CEAV_IMSS_EMPLOYER': 1387.37, 'CEAV_IMSS_EMPLOYEE': -292.78, 'NURSERY_IMSS_EMPLOYER': 260.25, 'INFONAVIT_IMSS_EMPLOYER': 1301.23, 'IMSS_EMPLOYEE_TOTAL': 703.51, 'IMSS_EMPLOYER_TOTAL': 5062.69, 'NET': 19526.54, 'PROVISIONS_CHRISTMAS_BONUS': 1024.59, 'PERIOD_PROVISIONS_CHRISTMAS_BONUS': 1024.59, 'PROVISIONS_HOLIDAY_BONUS': 0.0, 'PERIOD_PROVISIONS_HOLIDAY_BONUS': 0.0, 'PROVISIONS_VACATIONS_BONUS': 16684.88, 'PERIOD_PROVISIONS_VACATIONS_BONUS': 16684.88}
        previous_payslip.action_payslip_done()
        self._validate_payslip(previous_payslip, previous_payslip_results)

        payslip = self._generate_payslip(date(2024, 1, 16), date(2024, 1, 31))
        payslip_results = {'BASIC': 25000.0, 'HOLIDAY_TO_SUB': 0.0, 'GROSS_WITHOUT_HOLIDAY': 25000.0, 'HOLIDAYS_ON_TIME': 0.0, 'GROSS': 25000.0, 'ISR': -4697.04, 'INT_DAY_WAGE_BASE': 1734.97, 'INT_DAY_WAGE_OTHER': 0.0, 'INT_DAY_WAGE_COMMISSIONS': 0.0, 'INT_DAY_WAGE': 1734.97, 'RISK_IMSS_EMPLOYER': 138.8, 'DIS_FIX_IMSS_EMPLOYER': 338.61, 'DIS_ADD_IMSS_EMPLOYER': 250.58, 'DIS_ADD_IMSS_EMPLOYEE': -91.12, 'DIS_MED_IMSS_EMPLOYER': 291.48, 'DIS_MED_IMSS_EMPLOYEE': -104.1, 'DIS_MON_IMSS_EMPLOYER': 194.32, 'DIS_MON_IMSS_EMPLOYEE': -69.4, 'DIS_LIF_IMSS_EMPLOYER': 485.79, 'DIS_LIF_IMSS_EMPLOYEE': -173.5, 'RETIRE_IMSS_EMPLOYER': 555.19, 'CEAV_IMSS_EMPLOYER': 1479.86, 'CEAV_IMSS_EMPLOYEE': -312.3, 'NURSERY_IMSS_EMPLOYER': 277.6, 'INFONAVIT_IMSS_EMPLOYER': 1387.98, 'IMSS_EMPLOYEE_TOTAL': 750.41, 'IMSS_EMPLOYER_TOTAL': 5400.2, 'NET': 19552.55, 'PROVISIONS_CHRISTMAS_BONUS': 2117.49, 'PERIOD_PROVISIONS_CHRISTMAS_BONUS': 1092.9, 'PROVISIONS_HOLIDAY_BONUS': 0.0, 'PERIOD_PROVISIONS_HOLIDAY_BONUS': 0.0, 'PROVISIONS_VACATIONS_BONUS': 17850.64, 'PERIOD_PROVISIONS_VACATIONS_BONUS': 1165.76}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_isr_yearly_adjustment(self):
        self.contract.write({'l10n_mx_schedule_pay_temp': 'bi_weekly'})

        for i in range(12):
            first_half_month_payslip = self._generate_payslip(date(2024, i+1, 1), date(2024, i+1, 15))
            first_half_month_payslip.action_payslip_done()
            if i != 11:
                second_half_month_payslip = self._generate_payslip(date(2024, i+1, 16), date(2024, i+1, 1) + relativedelta(months=1, days=-1))
                second_half_month_payslip.action_payslip_done()

        payslip = self._generate_payslip(date(2024, 12, 16), date(2024, 12, 31))
        payslip_results = {'BASIC': 25000.0, 'HOLIDAY_TO_SUB': 0.0, 'GROSS_WITHOUT_HOLIDAY': 25000.0, 'HOLIDAYS_ON_TIME': 0.0, 'GROSS': 25000.0, 'ISR': -4697.04, 'INT_DAY_WAGE_BASE': 1734.97, 'INT_DAY_WAGE_OTHER': 0.0, 'INT_DAY_WAGE_COMMISSIONS': 0.0, 'INT_DAY_WAGE': 1734.97, 'RISK_IMSS_EMPLOYER': 138.8, 'DIS_FIX_IMSS_EMPLOYER': 354.37, 'DIS_ADD_IMSS_EMPLOYER': 248.03, 'DIS_ADD_IMSS_EMPLOYEE': -90.19, 'DIS_MED_IMSS_EMPLOYER': 291.48, 'DIS_MED_IMSS_EMPLOYEE': -104.1, 'DIS_MON_IMSS_EMPLOYER': 194.32, 'DIS_MON_IMSS_EMPLOYEE': -69.4, 'DIS_LIF_IMSS_EMPLOYER': 485.79, 'DIS_LIF_IMSS_EMPLOYEE': -173.5, 'RETIRE_IMSS_EMPLOYER': 555.19, 'CEAV_IMSS_EMPLOYER': 1479.86, 'CEAV_IMSS_EMPLOYEE': -312.3, 'NURSERY_IMSS_EMPLOYER': 277.6, 'INFONAVIT_IMSS_EMPLOYER': 1387.98, 'IMSS_EMPLOYEE_TOTAL': 749.48, 'IMSS_EMPLOYER_TOTAL': 5413.41, 'NET': 19553.48, 'PROVISIONS_CHRISTMAS_BONUS': 25000.0, 'PERIOD_PROVISIONS_CHRISTMAS_BONUS': 1092.9, 'PROVISIONS_HOLIDAY_BONUS': 0.0, 'PERIOD_PROVISIONS_HOLIDAY_BONUS': 0.0, 'PROVISIONS_VACATIONS_BONUS': 17540.98, 'PERIOD_PROVISIONS_VACATIONS_BONUS': 1311.47}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_paid_holiday(self):
        # 1/3 of the month is paid holidays
        self.env['hr.leave.allocation'].create({
            'name': 'Paid Time Off Allocation',
            'employee_id': self.employee.id,
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id,
            'number_of_days': 20,
            'state': 'confirm',
            'date_from': '2024-01-01',
            'date_to': '2024-12-31',
        }).action_validate()
        self._generate_leave(date(2024, 1, 1), date(2024, 1, 10), 'hr_holidays.holiday_status_cl')
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 50000.0, 'HOLIDAY_TO_SUB': 13333.33, 'GROSS_WITHOUT_HOLIDAY': 36666.67, 'HOLIDAYS_ON_TIME': 13333.33, 'GROSS': 50000.0, 'ISR': -9466.99, 'INT_DAY_WAGE_BASE': 1734.97, 'INT_DAY_WAGE_OTHER': 0.0, 'INT_DAY_WAGE_COMMISSIONS': 0.0, 'INT_DAY_WAGE': 1734.97, 'RISK_IMSS_EMPLOYER': 268.92, 'DIS_FIX_IMSS_EMPLOYER': 656.05, 'DIS_ADD_IMSS_EMPLOYER': 485.5, 'DIS_ADD_IMSS_EMPLOYEE': -176.55, 'DIS_MED_IMSS_EMPLOYER': 564.73, 'DIS_MED_IMSS_EMPLOYEE': -201.69, 'DIS_MON_IMSS_EMPLOYER': 376.49, 'DIS_MON_IMSS_EMPLOYEE': -134.46, 'DIS_LIF_IMSS_EMPLOYER': 941.22, 'DIS_LIF_IMSS_EMPLOYEE': -336.15, 'RETIRE_IMSS_EMPLOYER': 1075.68, 'CEAV_IMSS_EMPLOYER': 2867.23, 'CEAV_IMSS_EMPLOYEE': -605.07, 'NURSERY_IMSS_EMPLOYER': 537.84, 'INFONAVIT_IMSS_EMPLOYER': 2689.21, 'IMSS_EMPLOYEE_TOTAL': 1453.92, 'IMSS_EMPLOYER_TOTAL': 10462.88, 'NET': 39079.09, 'PROVISIONS_CHRISTMAS_BONUS': 2117.49, 'PERIOD_PROVISIONS_CHRISTMAS_BONUS': 2117.49, 'PROVISIONS_HOLIDAY_BONUS': 0.0, 'PERIOD_PROVISIONS_HOLIDAY_BONUS': 0.0, 'PROVISIONS_VACATIONS_BONUS': 17850.64, 'PERIOD_PROVISIONS_VACATIONS_BONUS': 17850.64}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_complete_case(self):
        self.contract.write({
            'l10n_mx_schedule_pay_temp': 'bi_weekly',
            'l10n_mx_meal_voucher_amount': 3000,
            'l10n_mx_transport_amount': 2000,
            'l10n_mx_gasoline_amount': 1000,
            'l10n_mx_savings_fund': 4000,
            'l10n_mx_holiday_bonus_rate': 25,
        })
        payslip = self._generate_payslip(date(2024, 9, 16), date(2024, 9, 30))
        payslip_results = {'BASIC': 25000.0, 'HOLIDAY_TO_SUB': 0.0, 'GROSS_WITHOUT_HOLIDAY': 25000.0, 'HOLIDAYS_ON_TIME': 0.0, 'ANNUAL_SOCIAL_PROVISION': 277244.35, 'EXEMPTION_SOCIAL_SECURITY': 3300.53, 'GAS_PERIOD': 1000.0, 'TRANSPORT_PERIOD': 2000.0, 'MEAL_VOUCHER_PERIOD': 3000.0, 'NO_TAX_GAS': 550.09, 'NO_TAX_TRANSPORT': 1100.18, 'NO_TAX_MEAL_VOUCHER': 1650.26, 'TAX_GAS': 449.91, 'TAX_TRANSPORT': 899.82, 'TAX_MEAL_VOUCH': 1349.74, 'SAVINGS_FUND_SALARY_LIMIT': 3250.0, 'SAVINGS_FUND_LIMIT_UMA': 2145.34, 'SAVINGS_FUND_EMPLOYER_ALW': 2000.0, 'GROSS': 27699.47, 'ISR': -4248.61, 'SAVINGS_FUND_EMPLOYEE': -2000.0, 'SAVINGS_FUND_EMPLOYER_DED': -2000.0, 'INT_DAY_WAGE_BASE': 1755.46, 'INT_DAY_WAGE_OTHER': 0.0, 'INT_DAY_WAGE_COMMISSIONS': 0.0, 'INT_DAY_WAGE': 1755.46, 'RISK_IMSS_EMPLOYER': 131.66, 'DIS_FIX_IMSS_EMPLOYER': 332.22, 'DIS_ADD_IMSS_EMPLOYER': 235.91, 'DIS_ADD_IMSS_EMPLOYEE': -85.79, 'DIS_MED_IMSS_EMPLOYER': 276.49, 'DIS_MED_IMSS_EMPLOYEE': -98.74, 'DIS_MON_IMSS_EMPLOYER': 184.32, 'DIS_MON_IMSS_EMPLOYEE': -65.83, 'DIS_LIF_IMSS_EMPLOYER': 460.81, 'DIS_LIF_IMSS_EMPLOYEE': -164.57, 'RETIRE_IMSS_EMPLOYER': 526.64, 'CEAV_IMSS_EMPLOYER': 1403.76, 'CEAV_IMSS_EMPLOYEE': -296.23, 'NURSERY_IMSS_EMPLOYER': 263.32, 'INFONAVIT_IMSS_EMPLOYER': 1316.6, 'IMSS_EMPLOYEE_TOTAL': 711.17, 'IMSS_EMPLOYER_TOTAL': 5131.73, 'NET': 24040.22, 'PROVISIONS_CHRISTMAS_BONUS': 18715.85, 'PERIOD_PROVISIONS_CHRISTMAS_BONUS': 18715.85, 'PROVISIONS_HOLIDAY_BONUS': 2500.0, 'PERIOD_PROVISIONS_HOLIDAY_BONUS': 2500.0, 'PROVISIONS_VACATIONS_BONUS': 10000.0, 'PERIOD_PROVISIONS_VACATIONS_BONUS': 10000.0}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_subsidy(self):
        self.contract.write({
            'wage': 10000,
            'l10n_mx_schedule_pay_temp': 'bi_weekly',
            'l10n_mx_savings_fund': 5000,
            'l10n_mx_holiday_bonus_rate': 25,
        })
        payslip = self._generate_payslip(date(2025, 2, 1), date(2025, 2, 28))
        payslip_results = {'BASIC': 5000.0, 'HOLIDAY_TO_SUB': 0.0, 'GROSS_WITHOUT_HOLIDAY': 5000.0, 'HOLIDAYS_ON_TIME': 0.0, 'SAVINGS_FUND_SALARY_LIMIT': 650.0, 'SAVINGS_FUND_LIMIT_UMA': 2235.65, 'SAVINGS_FUND_EMPLOYER_ALW': 650.0, 'GROSS': 5000.0, 'ISR': -286.57, 'SAVINGS_FUND_EMPLOYEE': -650.0, 'SAVINGS_FUND_EMPLOYER_DED': -650.0, 'SUBSIDY_CURRENT_MONTH': 437.17, 'SUBSIDY_ADJUSTMENT': 0.0, 'SUBSIDY': 437.17, 'INT_DAY_WAGE_BASE': 351.14, 'INT_DAY_WAGE_OTHER': 0.0, 'INT_DAY_WAGE_COMMISSIONS': 0.0, 'INT_DAY_WAGE': 351.14, 'RISK_IMSS_EMPLOYER': 49.16, 'DIS_FIX_IMSS_EMPLOYER': 646.26, 'DIS_ADD_IMSS_EMPLOYER': 3.61, 'DIS_ADD_IMSS_EMPLOYEE': -1.31, 'DIS_MED_IMSS_EMPLOYER': 103.24, 'DIS_MED_IMSS_EMPLOYEE': -36.87, 'DIS_MON_IMSS_EMPLOYER': 68.82, 'DIS_MON_IMSS_EMPLOYEE': -24.58, 'DIS_LIF_IMSS_EMPLOYER': 172.06, 'DIS_LIF_IMSS_EMPLOYEE': -61.45, 'RETIRE_IMSS_EMPLOYER': 196.64, 'CEAV_IMSS_EMPLOYER': 546.56, 'CEAV_IMSS_EMPLOYEE': -110.61, 'NURSERY_IMSS_EMPLOYER': 98.32, 'INFONAVIT_IMSS_EMPLOYER': 491.6, 'IMSS_EMPLOYEE_TOTAL': 234.82, 'IMSS_EMPLOYER_TOTAL': 2376.26, 'NET': 4265.78, 'PROVISIONS_CHRISTMAS_BONUS': 808.22, 'PERIOD_PROVISIONS_CHRISTMAS_BONUS': 808.22, 'PROVISIONS_HOLIDAY_BONUS': 1121.92, 'PERIOD_PROVISIONS_HOLIDAY_BONUS': 1121.92, 'PROVISIONS_VACATIONS_BONUS': 4487.67, 'PERIOD_PROVISIONS_VACATIONS_BONUS': 4487.67}
        self._validate_payslip(payslip, payslip_results)

    def test_christmas_bonus_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 12, 31), self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_christmas_bonus').id)
        payslip_results = {'BASIC': 25000.0, 'EXEMPT': 1628.55, 'GROSS': 23371.45, 'ISR': -7011.44, 'NET': 17988.57}
        self._validate_payslip(payslip, payslip_results)

    def test_christmas_bonus_2(self):
        self._add_rule_parameter_value('l10n_mx_christmas_bonus', 30, date(2024, 1, 1))
        self._generate_leave(date(2024, 1, 1), date(2024, 1, 10), 'hr_holidays.holiday_status_unpaid')
        self._generate_leave(date(2024, 2, 5), date(2024, 2, 7), 'l10n_mx_hr_payroll.holiday_type_work_risk_imss')
        self._generate_leave(date(2024, 3, 4), date(2024, 3, 6), 'l10n_mx_hr_payroll.holiday_type_maternity_imss')
        self._generate_leave(date(2024, 4, 1), date(2024, 4, 3), 'l10n_mx_hr_payroll.holiday_type_disability_due_to_illness_imss')

        last_christmas_provision = 0
        for i in range(12):
            monthly_payslip = self._generate_payslip(date(2024, i+1, 1), date(2024, i+1, 1) + relativedelta(months=1, days=-1))
            monthly_payslip.action_payslip_done()

            last_christmas_provision = monthly_payslip._get_line_values(['PROVISIONS_CHRISTMAS_BONUS'], compute_sum=True)['PROVISIONS_CHRISTMAS_BONUS']['sum']['total']

        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 12, 31), self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_christmas_bonus').id)
        payslip_results = {'BASIC': 47677.6, 'EXEMPT': 1628.55, 'GROSS': 46049.05, 'ISR': -13814.71, 'NET': 33862.88}
        self._validate_payslip(payslip, payslip_results)

        christmas_bonus = payslip._get_line_values(['BASIC'], compute_sum=True)['BASIC']['sum']['total']
        self.assertEqual(last_christmas_provision, christmas_bonus)

    def test_christmas_bonus_3(self):
        self._add_rule_parameter_value('l10n_mx_christmas_bonus', 30, date(2024, 1, 1))
        self._generate_leave(date(2024, 1, 2), date(2024, 1, 2), 'hr_holidays.holiday_status_unpaid')
        self._generate_leave(date(2024, 1, 3), date(2024, 1, 3), 'l10n_mx_hr_payroll.holiday_type_work_risk_imss')
        self._generate_leave(date(2024, 1, 4), date(2024, 1, 4), 'l10n_mx_hr_payroll.holiday_type_maternity_imss')
        self._generate_leave(date(2024, 1, 5), date(2024, 1, 5), 'l10n_mx_hr_payroll.holiday_type_disability_due_to_illness_imss')

        last_christmas_provision = 0
        for i in range(12):
            monthly_payslip = self._generate_payslip(date(2024, i+1, 1), date(2024, i+1, 1) + relativedelta(months=1, days=-1))
            monthly_payslip.action_payslip_done()

            last_christmas_provision = monthly_payslip._get_line_values(['PROVISIONS_CHRISTMAS_BONUS'], compute_sum=True)['PROVISIONS_CHRISTMAS_BONUS']['sum']['total']

        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 12, 31), self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_christmas_bonus').id)
        payslip_results = {'BASIC': 49453.55, 'EXEMPT': 1628.55, 'GROSS': 47825.0, 'ISR': -14347.5, 'NET': 35106.05}
        self._validate_payslip(payslip, payslip_results)

        christmas_bonus = payslip._get_line_values(['BASIC'], compute_sum=True)['BASIC']['sum']['total']
        self.assertEqual(last_christmas_provision, christmas_bonus)

    def test_christmas_bonus_4(self):
        self.contract.date_start = date(2024, 6, 18)
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 12, 31), self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_christmas_bonus').id)
        payslip_results = {'BASIC': 13456.28, 'EXEMPT': 1628.55, 'GROSS': 11827.73, 'ISR': -3548.32, 'NET': 9907.96}
        self._validate_payslip(payslip, payslip_results)

    def test_weekly_schedule_pay_no_code(self):
        structure = self.env['hr.payroll.structure'].create({
            'name': 'Test Structure',
            'country_id': self.env.ref('base.mx').id,
            'type_id': self.env.ref('l10n_mx_hr_payroll.structure_type_employee_mx').id,
            'report_id': self.env.ref('l10n_mx_hr_payroll.action_report_payslip_mx').id,
        })
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 12, 31), struct_id=structure.id)
        payslip_results = {'BASIC': 50000.0, 'GROSS': 50000.0, 'NET': 50000.0}
        self._validate_payslip(payslip, payslip_results)
