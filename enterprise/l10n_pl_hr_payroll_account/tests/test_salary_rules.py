# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.pl'),
            structure=cls.env.ref('l10n_pl_hr_payroll.hr_payroll_structure_pl_employee_salary'),
            structure_type=cls.env.ref('l10n_pl_hr_payroll.structure_type_employee_pl'),
            contract_fields={
                'wage': 7000.0,
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'PENSION': -683.2, 'PENSION.EMPLOYER': 683.2, 'DISABILITY': -105.0, 'DISABILITY.EMPLOYER': 455.0, 'SICKNESS': -171.5, 'ACCIDENT.EMPLOYER': 116.9, 'LABOUR.EMPLOYER': 171.5, 'SOCIAL.TOTAL': -959.7, 'SOCIAL.TOTAL.EMPLOYER': 1426.6, 'GROSS': 6040.3, 'STANDARD.EARNING': -250.0, 'TAXABLE': 5790.3, 'TAX': 0.0, 'HEALTH': -543.63, 'CHILD': 0.0, 'NET': 5496.67}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_children_1(self):
        self.employee.children = 1
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'PENSION': -683.2, 'PENSION.EMPLOYER': 683.2, 'DISABILITY': -105.0, 'DISABILITY.EMPLOYER': 455.0, 'SICKNESS': -171.5, 'ACCIDENT.EMPLOYER': 116.9, 'LABOUR.EMPLOYER': 171.5, 'SOCIAL.TOTAL': -959.7, 'SOCIAL.TOTAL.EMPLOYER': 1426.6, 'GROSS': 6040.3, 'STANDARD.EARNING': -250.0, 'TAXABLE': 5790.3, 'TAX': 0.0, 'HEALTH': -543.63, 'CHILD': 92.67, 'NET': 5589.34}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_children_2(self):
        self.employee.children = 2
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'PENSION': -683.2, 'PENSION.EMPLOYER': 683.2, 'DISABILITY': -105.0, 'DISABILITY.EMPLOYER': 455.0, 'SICKNESS': -171.5, 'ACCIDENT.EMPLOYER': 116.9, 'LABOUR.EMPLOYER': 171.5, 'SOCIAL.TOTAL': -959.7, 'SOCIAL.TOTAL.EMPLOYER': 1426.6, 'GROSS': 6040.3, 'STANDARD.EARNING': -250.0, 'TAXABLE': 5790.3, 'TAX': 0.0, 'HEALTH': -543.63, 'CHILD': 185.34, 'NET': 5682.01}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_children_3(self):
        self.employee.children = 3
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'PENSION': -683.2, 'PENSION.EMPLOYER': 683.2, 'DISABILITY': -105.0, 'DISABILITY.EMPLOYER': 455.0, 'SICKNESS': -171.5, 'ACCIDENT.EMPLOYER': 116.9, 'LABOUR.EMPLOYER': 171.5, 'SOCIAL.TOTAL': -959.7, 'SOCIAL.TOTAL.EMPLOYER': 1426.6, 'GROSS': 6040.3, 'STANDARD.EARNING': -250.0, 'TAXABLE': 5790.3, 'TAX': 0.0, 'HEALTH': -543.63, 'CHILD': 352.01, 'NET': 5848.68}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_children_4(self):
        self.employee.children = 4
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'PENSION': -683.2, 'PENSION.EMPLOYER': 683.2, 'DISABILITY': -105.0, 'DISABILITY.EMPLOYER': 455.0, 'SICKNESS': -171.5, 'ACCIDENT.EMPLOYER': 116.9, 'LABOUR.EMPLOYER': 171.5, 'SOCIAL.TOTAL': -959.7, 'SOCIAL.TOTAL.EMPLOYER': 1426.6, 'GROSS': 6040.3, 'STANDARD.EARNING': -250.0, 'TAXABLE': 5790.3, 'TAX': 0.0, 'HEALTH': -543.63, 'CHILD': 577.01, 'NET': 6073.68}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_children_5(self):
        self.employee.children = 5
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 7000.0, 'PENSION': -683.2, 'PENSION.EMPLOYER': 683.2, 'DISABILITY': -105.0, 'DISABILITY.EMPLOYER': 455.0, 'SICKNESS': -171.5, 'ACCIDENT.EMPLOYER': 116.9, 'LABOUR.EMPLOYER': 171.5, 'SOCIAL.TOTAL': -959.7, 'SOCIAL.TOTAL.EMPLOYER': 1426.6, 'GROSS': 6040.3, 'STANDARD.EARNING': -250.0, 'TAXABLE': 5790.3, 'TAX': 0.0, 'HEALTH': -543.63, 'CHILD': 802.01, 'NET': 6298.68}
        self._validate_payslip(payslip, payslip_results)
