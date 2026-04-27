# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('eg')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.eg'),
            structure=cls.env.ref('l10n_eg_hr_payroll.hr_payroll_structure_eg_employee_salary'),
            structure_type=cls.env.ref('l10n_eg_hr_payroll.structure_type_employee_eg'),
            contract_fields={
                'wage': 10000,
                'l10n_eg_housing_allowance': 100,
                'l10n_eg_transportation_allowance': 110,
                'l10n_eg_other_allowances': 80,
                'l10n_eg_social_insurance_reference': 1000,
                'l10n_eg_number_of_days': 5,
                'l10n_eg_total_number_of_days': 20,
            }
        )

    def test_basic_payslip(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 10000.0, 'TA': 110.0, 'OA': 80.0, 'SIEMP': -110.0, 'SICOMP': 187.5, 'SITOT': 297.5, 'GROSS': 10190.0, 'GROSSY': 122280.0, 'TAXBLEAM': 107280.0, 'TOTTB': -1100.5, 'NET': 8979.5}
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_service_payslip(self):
        self.employee.departure_date = date(2024, 1, 31)
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 10000.0, 'TA': 110.0, 'OA': 80.0, 'SIEMP': -110.0, 'SICOMP': 187.5, 'SITOT': 297.5, 'EOSP': 141.53, 'EOSB': 6793.33, 'GROSS': 16983.33, 'GROSSY': 203800.0, 'TAXBLEAM': 188800.0, 'TOTTB': -2459.17, 'NET': 14414.17}
        self._validate_payslip(payslip, payslip_results)
