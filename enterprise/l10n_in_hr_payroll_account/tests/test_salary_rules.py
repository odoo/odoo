# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.in'),
            structure=cls.env.ref('l10n_in_hr_payroll.hr_payroll_structure_in_employee_salary'),
            structure_type=cls.env.ref('l10n_in_hr_payroll.hr_payroll_salary_structure_type_ind_emp'),
        )

    def test_payslip_1(self):
        self.contract.write({
            'wage': 16000,
            'l10n_in_provident_fund': True
        })
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'HRA': 2800.0, 'STD': 4167.0, 'BONUS': 2100.0, 'LTA': 2100.0, 'SPL': -8567.0, 'P_BONUS': 5527.27, 'GROSS': 9600.0, 'PT': -150.0, 'PF': -840.0, 'PFE': -840.0, 'NET': 21864.27}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_2(self):
        self.contract.write({
            'wage': 32000,
            'l10n_in_provident_fund': True
        })
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'HRA': 2800.0, 'STD': 4167.0, 'BONUS': 2100.0, 'LTA': 2100.0, 'SPL': 1033.0, 'P_BONUS': 11054.55, 'GROSS': 19200.0, 'PT': -200.0, 'PF': -840.0, 'PFE': -840.0, 'NET': 27341.55}
        self._validate_payslip(payslip, payslip_results)
