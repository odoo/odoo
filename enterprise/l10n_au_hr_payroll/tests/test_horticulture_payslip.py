# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestPayrollHorticulture(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollHorticulture, cls).setUpClass()
        cls.tax_treatment_category = 'C'

    def test_horticulture_payslip_1(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'non_resident': False,
            'leave_loading': 'regular',
            'leave_loading_rate': 17.5,
            'workplace_giving_type': 'both',
            'workplace_giving_employee': 100,
            'workplace_giving_employer': 100,
            'salary_sacrifice_superannuation': 100,
            'salary_sacrifice_other': 0,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True
        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 21, 159.6, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 5000),
                ('SALARY.SACRIFICE.TOTAL', -200),
                ('SALARY.SACRIFICE.OTHER', -100),
                ('WORKPLACE.GIVING', -100),
                ('GROSS', 4700),
                ('WITHHOLD', -611),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -611),
                ('NET', 4089),
                ('SUPER.CONTRIBUTION', 100),
                ('SUPER', 550),
            ],
        )

    def test_horticulture_payslip_2(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'non_resident': False,
            'leave_loading': 'regular',
            'leave_loading_rate': 17.5,
            'workplace_giving_type': 'employer_deduction',
            'workplace_giving_employee': 0,
            'workplace_giving_employer': 100,
            'salary_sacrifice_superannuation': 100,
            'salary_sacrifice_other': 0,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'tfn_declaration': '000000000',
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True
        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 21, 159.6, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 5000),
                ('SALARY.SACRIFICE.TOTAL', -200),
                ('SALARY.SACRIFICE.OTHER', -100),
                ('GROSS', 4800),
                ('WITHHOLD', -2255),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -2255),
                ('NET', 2545),
                ('SUPER.CONTRIBUTION', 100),
                ('SUPER', 550),
            ],
        )

    def test_horticulture_payslip_3(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'leave_loading': 'regular',
            'leave_loading_rate': 17.5,
            'workplace_giving_type': 'employee_deduction',
            'workplace_giving_employee': 200,
            'workplace_giving_employer': 0,
            'salary_sacrifice_superannuation': 100,
            'salary_sacrifice_other': 0,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'tfn_declaration': '000000000',
            'non_resident': True,
            'l10n_au_training_loan': False
        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 21, 159.6, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 5000),
                ('SALARY.SACRIFICE.TOTAL', -100),
                ('WORKPLACE.GIVING', -200),
                ('GROSS', 4700),
                ('WITHHOLD', -2114),
                ('WITHHOLD.TOTAL', -2114),
                ('NET', 2586),
                ('SUPER.CONTRIBUTION', 100),
                ('SUPER', 550),
            ],
        )

    def test_horticulture_payslip_4(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'leave_loading': 'regular',
            'leave_loading_rate': 17.5,
            'workplace_giving_type': 'none',
            'workplace_giving_employee': 0,
            'workplace_giving_employer': 0,
            'salary_sacrifice_superannuation': 100,
            'salary_sacrifice_other': 100,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'non_resident': True,
            'l10n_au_training_loan': False
        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 21, 159.6, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 5000),
                ('SALARY.SACRIFICE.TOTAL', -200),
                ('SALARY.SACRIFICE.OTHER', -100),
                ('GROSS', 4800),
                ('WITHHOLD', -1560),
                ('WITHHOLD.TOTAL', -1560),
                ('NET', 3240),
                ('SUPER.CONTRIBUTION', 100),
                ('SUPER', 550),
            ],
        )

    def test_horticulture_payslip_5(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'salary_sacrifice_superannuation': 200,
            'salary_sacrifice_other': 100,
            'workplace_giving_employee': 50,
            'workplace_giving_employer': 50,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'non_resident': True,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'CFXXXX')

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 23, 174.8, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 6050),
                ('EXTRA', 200),
                ('SALARY.SACRIFICE.TOTAL', -350),
                ('ALW', 550),
                ('ALW.TAXFREE', 0),
                ('RTW', 300),
                ('SALARY.SACRIFICE.OTHER', -150),
                ('WORKPLACE.GIVING', -50),
                ('GROSS', 5650),
                ('WITHHOLD', -1605),
                ('RTW.WITHHOLD', -96),
                ('WITHHOLD.TOTAL', -1701),
                ('NET', 3949),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_horticulture_payslip_6(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'salary_sacrifice_superannuation': 200,
            'salary_sacrifice_other': 100,
            'workplace_giving_employee': 50,
            'workplace_giving_employer': 50,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'CTXXXX')

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 23, 174.8, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 6050),
                ('EXTRA', 200),
                ('SALARY.SACRIFICE.TOTAL', -350),
                ('ALW', 550),
                ('ALW.TAXFREE', 0),
                ('RTW', 300),
                ('SALARY.SACRIFICE.OTHER', -150),
                ('WORKPLACE.GIVING', -50),
                ('GROSS', 5650),
                ('WITHHOLD', -696),
                ('RTW.WITHHOLD', -96),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -792),
                ('NET', 4858),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )
