# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('lt')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.lt'),
            structure=cls.env.ref('l10n_lt_hr_payroll.hr_payroll_structure_lt_employee_salary'),
            structure_type=cls.env.ref('l10n_lt_hr_payroll.structure_type_employee_lt'),
            contract_fields={
                'wage': 1600.0
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 1600.0, 'GROSS': 1600.0, 'PIT': -274.49, 'PITSICK': 0.0, 'SSC': -267.63, 'NET': 1057.89, 'SSCEMP': 24.29}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_2(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        self._add_other_inputs(payslip, {'l10n_lt_hr_payroll.input_pit_last_year': 200.0})
        payslip_results = {'BASIC': 1600.0, 'GROSS': 1600.0, 'PIT': -274.49, 'PITSICK': 0.0, 'PITLAST': -64.0, 'SSC': -267.63, 'NET': 993.89, 'SSCEMP': 24.29}
        self._validate_payslip(payslip, payslip_results)
