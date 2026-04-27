# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('ke')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.ke'),
            structure=cls.env.ref('l10n_ke_hr_payroll.hr_payroll_structure_ken_employee_salary'),
            structure_type=cls.env.ref('l10n_ke_hr_payroll.structure_type_employee_ken'),
            contract_fields={
                'wage': 100000.0,
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 100000.0, 'GROSS': 100000.0, 'NSSF_EMPLOYEE_TIER_1': 360.0, 'NSSF_EMPLOYEE_TIER_2': 720.0, 'GROSS_TAXABLE': 98920.0, 'INCOME_TAX': 24459.35, 'NHIF_AMOUNT_HIDDEN': 1700.0, 'NHIF_RELIEF': -255.0, 'AHL_AMOUNT': 1500.0, 'INSURANCE_RELIEF': -255.0, 'PERS_RELIEF': -2400.0, 'PAYE': 21804.35, 'NSSF_AMOUNT': 1080.0, 'NHIF_AMOUNT': 1700.0, 'STATUTORY_DED': 26084.35, 'TOTAL_DED': 26084.35, 'NITA': 50.0, 'NSSF_EMP': 1080.0, 'AHL_AMOUNT_EMP': 1500.0, 'NET': 73915.65}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_2(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        self._add_other_inputs(payslip, {
            'l10n_ke_hr_payroll.input_fixed_bonus': 2000.0,
            'l10n_ke_hr_payroll.input_fixed_commission': 10000.0,
            'l10n_ke_hr_payroll.input_helb': 3000.0,
            'l10n_ke_hr_payroll.input_fringe_benefit': 4000.0,
            'l10n_ke_hr_payroll.input_fixed_non_cash': 2500.0,
        })
        payslip_results = {'BASIC': 100000.0, 'BONUS': 2000.0, 'COMMISSION': 10000.0, 'GROSS': 112000.0, 'NSSF_EMPLOYEE_TIER_1': 360.0, 'NSSF_EMPLOYEE_TIER_2': 720.0, 'GROSS_TAXABLE': 110920.0, 'INCOME_TAX': 28059.35, 'NHIF_AMOUNT_HIDDEN': 1700.0, 'NHIF_RELIEF': -255.0, 'AHL_AMOUNT': 1500.0, 'INSURANCE_RELIEF': -255.0, 'PERS_RELIEF': -2400.0, 'PAYE': 25404.35, 'NSSF_AMOUNT': 1080.0, 'NHIF_AMOUNT': 1700.0, 'STATUTORY_DED': 29684.35, 'HELB': 3000.0, 'OTHER_DED': 3000.0, 'FRINGE_BENEFIT': 4000.0, 'TOTAL_DED': 32684.35, 'NITA': 50.0, 'NSSF_EMP': 1080.0, 'AHL_AMOUNT_EMP': 1500.0, 'NON_CASH_BENEFIT': 2500.0, 'NET': 81815.65}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_new_paye_computation(self):
        if self.env['ir.module.module']._get('l10n_ke_hr_payroll_shif').state != 'installed':
            self.skipTest("New PAYE computation is not installed")
        payslip = self._generate_payslip(date(2025, 1, 1), date(2025, 1, 31))
        payslip_results = {'BASIC': 100000.0, 'GROSS': 100000.0, 'NSSF_EMPLOYEE_TIER_1': 420.0, 'NSSF_EMPLOYEE_TIER_2': 1740.0, 'GROSS_TAXABLE': 93590.0, 'INCOME_TAX': 22860.35, 'AHL_AMOUNT': 1500.0, 'PERS_RELIEF': -2400.0, 'PAYE': 20460.35, 'NSSF_AMOUNT': 2160.0, 'SHIF_AMOUNT': 2750.0, 'STATUTORY_DED': 26870.35, 'TOTAL_DED': 26870.35, 'NITA': 50.0, 'NSSF_EMP': 2160.0, 'AHL_AMOUNT_EMP': 1500.0, 'NET': 73129.65}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_secondary_contract(self):
        self.contract.l10n_ke_is_secondary = True
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 100000.0, 'GROSS': 100000.0, 'AHL_AMOUNT': 1500.0, 'GROSS_TAXABLE': 100000.0, 'INCOME_TAX': 35000.0, 'PAYE': 35000.0, 'STATUTORY_DED': 36500.0, 'TOTAL_DED': 36500.0, 'NITA': 50.0, 'AHL_AMOUNT_EMP': 1500.0, 'NET': 63500.0}
        self._validate_payslip(payslip, payslip_results)
