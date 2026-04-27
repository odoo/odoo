# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('tr')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.tr'),
            structure=cls.env.ref('l10n_tr_hr_payroll.hr_payroll_structure_tr_employee_salary'),
            structure_type=cls.env.ref('l10n_tr_hr_payroll.structure_type_employee_tr'),
            contract_fields={
                'wage': 50000,
            }
        )

    def test_basic_payslip(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 50000.0, 'SSIEDED': -7000.0, 'SSIDED': -500.0, 'SSICDED': 10250.0, 'SSIUCDED': 1000.0, 'GROSS': 50000.0, 'TAXB': 42500.0, 'TOTTB': 6375.0, 'BTAXNET': -3824.68, 'STAX': -227.68, 'NETTAX': -4052.36, 'NET': 38447.64}
        self._validate_payslip(payslip, payslip_results)
