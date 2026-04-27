# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('jo')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.jo'),
            structure=cls.env.ref('l10n_jo_hr_payroll.hr_payroll_structure_jo_employee_salary'),
            structure_type=cls.env.ref('l10n_jo_hr_payroll.structure_type_employee_jo'),
            contract_fields={
                'wage': 40000.0,
                'l10n_jo_housing_allowance': 400.0,
                'l10n_jo_transportation_allowance': 220.0,
                'l10n_jo_other_allowances': 100.0,
                'l10n_jo_tax_exemption': 15.0,
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 40000.0, 'HOUALLOW': 400.0, 'TRAALLOW': 220.0, 'OTALLOW': 100.0, 'GROSS': 40720.0, 'SSE': -251.175, 'SSC': -477.233, 'GROSSY': 488625.0, 'TXB': -9971.354, 'NET': 30497.471}
        self._validate_payslip(payslip, payslip_results)
