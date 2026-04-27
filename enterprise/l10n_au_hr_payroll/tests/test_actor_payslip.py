# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from unittest import skip

from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestPayrollActor(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollActor, cls).setUpClass()
        cls.default_payroll_structure = cls.env.ref("l10n_au_hr_payroll.hr_payroll_structure_au_regular")
        cls.tax_treatment_category = 'A'

    def test_actor_payslip_1(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True,
            'tax_treatment_option_actor': 'D',
            'leave_loading': 'regular',
            'leave_loading_rate': 17.5,
            'workplace_giving_type': 'none',
            'workplace_giving_employee': 0,
            'workplace_giving_employer': 0,
            'salary_sacrifice_superannuation': 0,
            'salary_sacrifice_other': 0,
            'wage_type': 'monthly',
            'schedule_pay': 'weekly',
            'wage': 5000,
            'casual_loading': 0,
            'performances_per_week': 1,
        })
        payslip_date = date(2023, 7, 3)
        payslip_end_date = date(2023, 7, 9)
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 5, 38, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 5000),
                ('GROSS', 5000),
                ('WITHHOLD', -1317),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -1317),
                ('NET', 3683),
                ('SUPER', 550),
            ],
            payslip_date_from=payslip_date,
            payslip_date_to=payslip_end_date,
        )

    def test_actor_payslip_2(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_training_loan': False,
            'tax_treatment_option_actor': 'D',
            'leave_loading': 'regular',
            'leave_loading_rate': 17.5,
            'workplace_giving_type': 'none',
            'workplace_giving_employee': 0,
            'workplace_giving_employer': 0,
            'salary_sacrifice_superannuation': 0,
            'salary_sacrifice_other': 0,
            'wage_type': 'monthly',
            'schedule_pay': 'weekly',
            'wage': 5000,
            'casual_loading': 0,
            'performances_per_week': 1,
        })
        payslip_date = date(2023, 7, 3)
        payslip_end_date = date(2023, 7, 9)
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 5, 38, 5000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 5000),
                ('OTE', 5000),
                ('GROSS', 5000),
                ('WITHHOLD', -1481),
                ('WITHHOLD.TOTAL', -1481),
                ('NET', 3519),
                ('SUPER', 550),
            ],
            payslip_date_from=payslip_date,
            payslip_date_to=payslip_end_date,
        )

    @skip("Daily actors with number of performances to be implemented")
    def test_actor_payslip_3(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
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

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'ATXXXX')

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
                ('WITHHOLD', -1229),
                ('RTW.WITHHOLD', -96),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -1325),
                ('NET', 4325),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    @skip("Daily actors with number of performances to be implemented")
    def test_actor_payslip_4(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
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
            'l10n_au_tax_free_threshold': False})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'ANXXXX')

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
                ('WITHHOLD', -1393),
                ('RTW.WITHHOLD', -141),
                ('WITHHOLD.TOTAL', -1534),
                ('NET', 4116),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    @skip("Daily actors with number of performances to be implemented")
    def test_actor_payslip_5(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
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
            'less_than_3_performance': True,
            'l10n_au_tax_free_threshold': True})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'ADXXXX')

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
                ('WITHHOLD', -1229),
                ('RTW.WITHHOLD', -96),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -1325),
                ('NET', 4325),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_actor_payslip_6(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
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
            'l10n_au_tax_free_threshold': False,
            'tax_treatment_option_actor': 'P'})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'APXXXX')

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
                ('WITHHOLD', -1070),
                ('RTW.WITHHOLD', -96),
                ('WITHHOLD.TOTAL', -1166),
                ('NET', 4484),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )
