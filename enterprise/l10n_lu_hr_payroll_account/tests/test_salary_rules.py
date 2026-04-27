# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('lu')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.lu'),
            structure=cls.env.ref('l10n_lu_hr_payroll.hr_payroll_structure_lux_employee_salary'),
            structure_type=cls.env.ref('l10n_lu_hr_payroll.structure_type_employee_lux'),
            tz="Europe/Brussels",
            contract_fields={
                'wage': 4000,
                'l10n_lu_meal_voucher_amount': 50.4,
                'date_start': date(2024, 1, 1),
            },
            employee_fields={
                'l10n_lu_tax_credit_cis': True,
                'l10n_lu_tax_id_number': '123',
            }
        )

    def test_basic_payslip(self):
        self.contract.wage = 4250
        self.contract.l10n_lu_meal_voucher_amount = 0
        self.employee.l10n_lu_tax_credit_cis = False
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 4250.0, 'GROSS': 4250.0, 'HEALTH_FUND': 119.0, 'CASH_SICKNESS_FUND': 10.63, 'RETIREMENT_FUND': 340.0, 'DEPENDENCY_INSURANCE': 50.5, 'TOTAL_CONTRIBUTIONS': 520.13, 'TOTAL_ALLOWANCES': 0.0, 'TAXABLE_AMOUNT': 3780.38, 'TAXES': 534.6, 'CISSM': 0.0, 'NET_TEMP': 3195.27, 'NET': 3195.27}
        self._validate_payslip(payslip, payslip_results)

    def test_basic_payslip_with_benefits(self):
        self.contract.write({
            'wage': 4250,
            'l10n_lu_meal_voucher_amount': 2.80,
            'l10n_lu_alw_vehicle': 300,
            'l10n_lu_bik_vehicle': 500,
            'l10n_lu_bik_vehicle_vat_included': False,
        })
        self.employee.write({
            'l10n_lu_deduction_ac_ae_daily': 7.26,
            'l10n_lu_deduction_fd_daily': 8.58,
            'l10n_lu_tax_credit_cis': True,
        })
        self.contract.wage = 4250
        self.contract.l10n_lu_meal_voucher_amount = 2.80
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        self.env['hr.payslip.input'].create({
            'payslip_id': payslip.id,
            'input_type_id': self.env.ref('l10n_lu_hr_payroll.input_wage_supplement_70').id,
            'amount': 10,
        })
        self.env['hr.payslip.input'].create({
            'payslip_id': payslip.id,
            'input_type_id': self.env.ref('l10n_lu_hr_payroll.input_overtime').id,
            'amount': 10,
        })
        self.env['hr.payslip.input'].create({
            'payslip_id': payslip.id,
            'input_type_id': self.env.ref('l10n_lu_hr_payroll.input_overtime_supplement_40').id,
            'amount': 10,
        })
        payslip.compute_sheet()
        payslip_results = {'BASIC': 4250.0, 'VEHICLE_ALLOWANCE': 300.0, 'BIK_VEHICLE': 500.0, 'WAGE_SUPPLEMENT_70': 171.97, 'OVERTIME': 245.66, 'OVERTIME_SUPPLEMENT_40': 98.27, 'GROSS': 5565.9, 'CASH_SICKNESS_FUND': 11.8, 'DEPENDENCY_INSURANCE': 67.55, 'HEALTH_FUND': 153.09, 'RETIREMENT_FUND': 417.76, 'TOTAL_CONTRIBUTIONS': 650.2, 'AC_AE': 181.5, 'FD': 214.5, 'OVERTIME_ALW': 238.79, 'OVERTIME_SUPPLEMENT_40_ALW': 98.27, 'WAGE_SUPPLEMENT_70_ALW': 171.97, 'TOTAL_ALLOWANCES': 905.02, 'TAXABLE_AMOUNT': 4078.22, 'TAXES': 644.5, 'CIS': -16.51, 'CISSM': 0.0, 'CIS_CI_CO2': -4.62, 'NET_TEMP': 4292.33, 'BIK_VEHICLE_NET': 500.0, 'MEAL_VOUCHERS': 50.4, 'NET': 3741.93}
        self._validate_payslip(payslip, payslip_results)

    def test_basic_payslip_incomplete_month(self):
        self.contract.wage = 4250
        self.contract.l10n_lu_meal_voucher_amount = 0
        self.employee.write({
            'l10n_lu_deduction_ac_ae_daily': 7.26,
            'l10n_lu_deduction_fd_daily': 8.58,
            'l10n_lu_tax_credit_cis': True,
        })
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 15))
        payslip_results = {'BASIC': 2032.61, 'GROSS': 2032.61, 'HEALTH_FUND': 56.91, 'CASH_SICKNESS_FUND': 5.08, 'RETIREMENT_FUND': 162.61, 'DEPENDENCY_INSURANCE': 23.88, 'TOTAL_CONTRIBUTIONS': 248.48, 'FD': 103.28, 'AC_AE': 87.39, 'TOTAL_ALLOWANCES': 190.67, 'TAXABLE_AMOUNT': 1617.34, 'TAXES': 168.8, 'CIS': -21.51, 'CIS_CI_CO2': -6.02, 'CISSM': 0.0, 'NET_TEMP': 1642.86, 'NET': 1642.86}
        self._validate_payslip(payslip, payslip_results)
