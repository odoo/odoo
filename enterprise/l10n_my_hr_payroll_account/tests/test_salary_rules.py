# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.my'),
            structure=cls.env.ref('l10n_my_hr_payroll.hr_payroll_structure_my_employee_salary'),
            structure_type=cls.env.ref('l10n_my_hr_payroll.structure_type_employee_my'),
            contract_fields={
                'wage': 7000,
            }
        )

    def test_01_payslip(self):
        payslip = self._generate_payslip(date(2020, 4, 1), date(2020, 4, 30))
        payslip_results = {'BASIC': 7000.0, 'GROSS': 7000.0, 'EPF_EMP': -490.0, 'EPF_EMPLR': 840.0, 'SOCSO_800_EMP': -11.9, 'SOCSO_800_EMPLR': 11.9, 'SOCSO_4_EMP': -29.75, 'SOCSO_4_EMPLR': -104.15, 'SOCSO_EMP': 41.65, 'SOCSO_EMPLR': -92.25, 'EIS_EMP': -14.0, 'EIS_EMPLR': 14.0, 'NET': 6496.0}
        self._validate_payslip(payslip, payslip_results)

    def test_02_payslip(self):
        self.employee.l10n_my_socso_exempted = True
        payslip = self._generate_payslip(date(2020, 4, 1), date(2020, 4, 30))
        payslip_results = {'BASIC': 7000.0, 'GROSS': 7000.0, 'EPF_EMP': -490.0, 'EPF_EMPLR': 840.0, 'SOCSO_800_EMP': 0.0, 'SOCSO_800_EMPLR': 0.0, 'SOCSO_4_EMP': 0.0, 'SOCSO_4_EMPLR': -74.4, 'SOCSO_EMP': 0.0, 'SOCSO_EMPLR': -74.4, 'EIS_EMP': -14.0, 'EIS_EMPLR': 14.0, 'NET': 6496.0}
        self._validate_payslip(payslip, payslip_results)

    def test_03_payslip(self):
        self.contract.wage = 2000
        payslip = self._generate_payslip(date(2020, 4, 1), date(2020, 4, 30))
        payslip_results = {'BASIC': 2000.0, 'GROSS': 2000.0, 'EPF_EMP': -140.0, 'EPF_EMPLR': 260.0, 'SOCSO_800_EMP': -3.9, 'SOCSO_800_EMPLR': 3.9, 'SOCSO_4_EMP': -9.75, 'SOCSO_4_EMPLR': -34.15, 'SOCSO_EMP': 13.65, 'SOCSO_EMPLR': -30.25, 'EIS_EMP': -4.0, 'EIS_EMPLR': 4.0, 'NET': 1856.0}
        self._validate_payslip(payslip, payslip_results)

    def test_04_payslip(self):
        payslip = self._generate_payslip(date(2020, 4, 1), date(2020, 4, 30))
        payslip.write({'input_line_ids': [(0, 0, {
            'input_type_id': self.env.ref('l10n_my_hr_payroll.l10n_my_hr_payroll_input_generic').id,
            'amount': 30,
        }), (0, 0, {
            'input_type_id': self.env.ref('l10n_my_hr_payroll.l10n_my_hr_payroll_dearness_allowance').id,
            'amount': 40,
        }), (0, 0, {
            'input_type_id': self.env.ref('l10n_my_hr_payroll.l10n_my_hr_payroll_house_rent_allowance').id,
            'amount': 50,
        }), (0, 0, {
            'input_type_id': self.env.ref('l10n_my_hr_payroll.l10n_my_hr_payroll_conveyance_allowance').id,
            'amount': 60,
        })]})
        payslip.compute_sheet()
        payslip_results = {'BASIC': 7000.0, 'MY_GENERIC_ALW': 30.0, 'MY_CONV_ALW': 60.0, 'MY_DA': 40.0, 'MY_HRA': 50.0, 'GROSS': 7180.0, 'EPF_EMP': -503.0, 'EPF_EMPLR': 862, 'SOCSO_800_EMP': -11.9, 'SOCSO_800_EMPLR': 11.9, 'SOCSO_4_EMP': -29.75, 'SOCSO_4_EMPLR': -104.15, 'SOCSO_EMP': 41.65, 'SOCSO_EMPLR': -92.25, 'EIS_EMP': -14.36, 'EIS_EMPLR': 14.36, 'NET': 6662.64}
        self._validate_payslip(payslip, payslip_results)
