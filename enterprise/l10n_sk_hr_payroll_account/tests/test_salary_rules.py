# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('sk')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.sk'),
            structure=cls.env.ref('l10n_sk_hr_payroll.hr_payroll_structure_sk_employee_salary'),
            structure_type=cls.env.ref('l10n_sk_hr_payroll.structure_type_employee_sk'),
            contract_fields={
                'wage': 1100.0,
                'l10n_sk_meal_voucher_employee': 8.0,
                'l10n_sk_meal_voucher_employer': 12.0,
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 1100.0, 'MEALEMPLOYEE': 184.0, 'MEALEMPLOYER': -276.0, 'GROSS': 1284.0, 'SICK': -17.98, 'SICKEMPLOYER': 17.98, 'PENSION': -51.36, 'PENSIONEMPLOYER': 179.76, 'DISABILITY': -38.52, 'DISABILITYEMPLOYER': 38.52, 'UNEMPLOYMENT': -12.84, 'UNEMPLOYMENTEMPLOYER': 6.42, 'SHORTTIMEEMPLOYER': 6.42, 'GUARANTEEEMPLOYER': 3.21, 'ACCIDENT': 10.27, 'RESERVEFUNDEMPLOYER': 60.99, 'HEALTH': -51.36, 'HEALTHEMPLOYER': 128.4, 'INCOMETAX19': -243.96, 'INCOMETAX25': 0.0, 'NET': 959.98, 'SOCIALEMPLOYEETOTAL': -172.06, 'SOCIALEMPLOYERTOTAL': 451.97, 'INCOMETAXTOTAL': 243.96}
        self._validate_payslip(payslip, payslip_results)
