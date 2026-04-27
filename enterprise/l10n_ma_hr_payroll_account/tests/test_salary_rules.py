# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('ma')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.ma'),
            structure=cls.env.ref('l10n_ma_hr_payroll.hr_payroll_salary_ma_structure_base'),
            structure_type=cls.env.ref('l10n_ma_hr_payroll.structure_type_employee_mar'),
            contract_fields={
                'wage': 5000,
                'date_start': date(2021, 1, 1),
            }
        )

    def test_cnss_rule(self):
        payslip = self._generate_payslip(date(2021, 1, 1), date(2021, 1, 31))
        payslip_results = {'BASIC': 5000.0, 'GROSS': 5000.0, 'E_CNSS': 224.0, 'JOB_LOSS_ALW': 9.5, 'E_AMO': 9.5, 'MEDICAL_ALW': 113.0, 'CIMR': 150.0, 'PRO_CONTRIBUTION': 150.0, 'TOTAL_UT_DED': 656.0, 'GROSS_TAXABLE': 4344.0, 'GROSS_INCOME_TAX': 202.13, 'FAMILY_CHARGE': 0, 'NET_INCOME_TAX': 202.13, 'SOCIAL_CONTRIBUTION': 0, 'NET': 3939.74}
        self._validate_payslip(payslip, payslip_results)

        self.contract.wage = 5600
        payslip = self._generate_payslip(date(2022, 5, 1), date(2022, 5, 31))
        payslip_results = {'BASIC': 5600.0, 'GROSS': 5600.0, 'E_CNSS': 250.88, 'JOB_LOSS_ALW': 10.64, 'E_AMO': 10.64, 'MEDICAL_ALW': 126.56, 'CIMR': 168.0, 'PRO_CONTRIBUTION': 168.0, 'TOTAL_UT_DED': 734.72, 'GROSS_TAXABLE': 4865.28, 'GROSS_INCOME_TAX': 306.39, 'FAMILY_CHARGE': 0, 'NET_INCOME_TAX': 306.39, 'SOCIAL_CONTRIBUTION': 0, 'NET': 4252.51}
        self._validate_payslip(payslip, payslip_results)

        self.contract.wage = 6000
        payslip = self._generate_payslip(date(2022, 6, 1), date(2022, 6, 30))
        payslip_results = {'BASIC': 6000.0, 'GROSS': 6000.0, 'E_CNSS': 268.8, 'JOB_LOSS_ALW': 11.4, 'E_AMO': 11.4, 'MEDICAL_ALW': 135.6, 'CIMR': 180.0, 'PRO_CONTRIBUTION': 180.0, 'TOTAL_UT_DED': 787.2, 'GROSS_TAXABLE': 5212.8, 'GROSS_INCOME_TAX': 397.17, 'FAMILY_CHARGE': 0, 'NET_INCOME_TAX': 397.17, 'SOCIAL_CONTRIBUTION': 0, 'NET': 4418.46}
        self._validate_payslip(payslip, payslip_results)

        self.contract.wage = 7500
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip_results = {'BASIC': 7500.0, 'SENIORITY': 0, 'GROSS': 7500.0, 'E_CNSS': 268.8, 'JOB_LOSS_ALW': 14.25, 'E_AMO': 14.25, 'MEDICAL_ALW': 169.5, 'CIMR': 225.0, 'PRO_CONTRIBUTION': 225.0, 'TOTAL_UT_DED': 916.8, 'GROSS_TAXABLE': 6583.2, 'GROSS_INCOME_TAX': 808.29, 'FAMILY_CHARGE': 0, 'NET_INCOME_TAX': 808.29, 'SOCIAL_CONTRIBUTION': 0, 'NET': 4966.62}
        self._validate_payslip(payslip, payslip_results)
