# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.ro'),
            structure=cls.env.ref('l10n_ro_hr_payroll.hr_payroll_structure_ro_employee_salary'),
            structure_type=cls.env.ref('l10n_ro_hr_payroll.structure_type_employee_ro'),
            contract_fields={
                'wage': 7500.0
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7500.0, 'GROSS': 7500.0, 'CAS': -1875.0, 'CASS': -750.0, 'INCOMETAX': -750.0, 'CAM': 168.75, 'UNEMPDISABLED': 0.0, 'PENSION': 0.0, 'NET': 4125.0}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_particular_1(self):
        self.contract.l10n_ro_work_type = '2'
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7500.0, 'GROSS': 7500.0, 'CAS': -1875.0, 'CASS': -750.0, 'INCOMETAX': -750.0, 'CAM': 168.75, 'UNEMPDISABLED': 0.0, 'PENSION': 300.0, 'NET': 4125.0}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_special_1(self):
        self.contract.l10n_ro_work_type = '3'
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7500.0, 'GROSS': 7500.0, 'CAS': -1875.0, 'CASS': -750.0, 'INCOMETAX': -750.0, 'CAM': 168.75, 'UNEMPDISABLED': 0.0, 'PENSION': 600.0, 'NET': 4125.0}
        self._validate_payslip(payslip, payslip_results)
