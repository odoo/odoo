# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('pk')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.pk'),
            structure=cls.env.ref('l10n_pk_hr_payroll.hr_payroll_structure_pk_employee_salary'),
            structure_type=cls.env.ref('l10n_pk_hr_payroll.structure_type_employee_pk'),
            contract_fields={
                'wage': 800000,
            }
        )

    def test_basic_payslip(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 800000.0, 'GROSS': 800000.0, 'GROSSY': 9600000.0, 'TXB': 1920000.0, 'TXW': -160000.0, 'NET': 640000.0}
        self._validate_payslip(payslip, payslip_results)
        self.employee.contract_ids.wage = 833333.42
        payslip_2026 = self._generate_payslip(date(2026, 1, 1), date(2026, 1, 31))
        payslip_results_2026 = {'BASIC': 833333.42, 'GROSS': 833333.42, 'GROSSY': 10000001.04, 'TXB': 2922290.40, 'TXW': -243524.20, 'NET': 589809.22}
        self._validate_payslip(payslip_2026, payslip_results_2026)

    def test_end_of_service_payslip(self):
        self.employee.departure_date = date(2024, 1, 31)
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 800000.0, 'GROSS': 800000.0, 'GROSSY': 9600000.0, 'TXB': 1920000.0, 'EOS': 7384616.0, 'TXW': -160000.0, 'NET': 8024616.0}
        self._validate_payslip(payslip, payslip_results)
        self.employee.contract_ids.wage = 833333.42
        payslip_2026 = self._generate_payslip(date(2026, 1, 1), date(2026, 1, 31))
        payslip_results_2026 = {'BASIC': 833333.42, 'GROSS': 833333.42, 'GROSSY': 10000001.04, 'TXB': 2922290.40, 'EOS': 7692309.0, 'TXW': -243524.20, 'NET': 8282118.22}
        self._validate_payslip(payslip_2026, payslip_results_2026)
