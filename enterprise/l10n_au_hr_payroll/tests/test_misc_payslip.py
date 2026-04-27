# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from unittest import skip

from odoo.tests import tagged
from odoo.exceptions import UserError

from .common import TestPayrollCommon


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestPayrollMisc(TestPayrollCommon):

    def test_misc_payslip_1(self):
        self.tax_treatment_category = 'F'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Naruto Uzumaki',
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
            'l10n_au_training_loan': True,
            'l10n_au_tax_free_threshold': False,
            'non_resident': True})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'FFSXXX')

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
                ('WITHHOLD', -1603),
                ('RTW.WITHHOLD', -96),
                ('WITHHOLD.STUDY', -143),
                ('WITHHOLD.TOTAL', -1842),
                ('NET', 3808),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_2(self):
        self.tax_treatment_category = 'F'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Muhammad Ali',
            'employment_basis_code': 'F',
            'tfn_declaration': '111111111',
            'salary_sacrifice_superannuation': 200,
            'salary_sacrifice_other': 100,
            'workplace_giving_employee': 50,
            'workplace_giving_employer': 50,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False,
            'non_resident': True})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'FFXXXX')

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
                ('WITHHOLD', -1603),
                ('RTW.WITHHOLD', -96),
                ('WITHHOLD.TOTAL', -1699),
                ('NET', 3951),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_3(self):
        self.tax_treatment_category = 'N'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': '000000000',
            'salary_sacrifice_superannuation': 200,
            'salary_sacrifice_other': 100,
            'workplace_giving_employee': 50,
            'workplace_giving_employer': 50,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False,
            'income_stream_type': 'SAW',
            'non_resident': True})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'NFXXXX')

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
                ('WITHHOLD', -2407),
                ('RTW.WITHHOLD', -135),
                ('WITHHOLD.TOTAL', -2542),
                ('NET', 3108),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_4(self):
        self.tax_treatment_category = 'N'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': '000000000',
            'salary_sacrifice_superannuation': 200,
            'salary_sacrifice_other': 100,
            'workplace_giving_employee': 50,
            'workplace_giving_employer': 50,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False,
            'income_stream_type': 'SAW',
            'non_resident': False})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'NAXXXX')

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
                ('WITHHOLD', -2514.5),
                ('RTW.WITHHOLD', -141),
                ('WITHHOLD.TOTAL', -2655.5),
                ('NET', 2994.5),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_5(self):
        self.tax_treatment_category = 'D'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'D',
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
            'income_stream_type': 'SAW',
            'non_resident': False})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'DBXXXX')
        # ATO Defined should raise error
        with self.assertRaises(UserError):
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
                    ('WITHHOLD', -2514.5),
                    ('RTW.WITHHOLD', -141),
                    ('WITHHOLD.TOTAL', -2655.5),
                    ('NET', 2994.5),
                    ('SUPER.CONTRIBUTION', 200),
                    ('SUPER', 695.75),
                ],
                input_lines=self.default_input_lines,
                payslip_date_from=date(2024, 7, 1),
                payslip_date_to=date(2024, 7, 31),
            )

    def test_misc_payslip_6(self):
        self.tax_treatment_category = 'D'

    def test_misc_payslip_7(self):
        self.tax_treatment_category = 'D'

    @skip("VOL Test case to be adapted for salary sacrifice")
    def test_misc_payslip_8(self):
        self.tax_treatment_category = 'V'

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
            'tax_treatment_option_voluntary': 'C',
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False,
            'income_stream_type': 'VOL',
            'comissioners_installment_rate': 50,
            'non_resident': False})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'VCXXXX')

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
                ('WITHHOLD', -2825),
                ('WITHHOLD.TOTAL', -2825),
                ('NET', 2825),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_9(self):
        self.tax_treatment_category = 'V'

        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'workplace_giving_employee': 50,
            'wage_type': 'monthly',
            'wage': 5000,
            'casual_loading': 0,
            'tax_treatment_option_voluntary': 'O',
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False,
            'income_stream_type': 'VOL',
            'non_resident': False})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'VOXXXX')

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
                ('OTE', 5200),
                ('EXTRA', 200),
                ('WORKPLACE.GIVING', -50),
                ('GROSS', 5150),
                ('WITHHOLD', -1030),
                ('WITHHOLD.TOTAL', -1030),
                ('NET', 4120),
                ('SUPER', 598),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_bonus_commissions').id,
                'amount': 200,
            }],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_10_backpay(self):
        """ Test payslip for backpay for current period
        https://www.ato.gov.au/tax-rates-and-codes/payg-withholding-schedule-5-tax-table-for-back-payments-commissions-bonuses-and-like-payments/examples
        Example 1
        """
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'weekly',
            'wage': 1400,
            'l10n_au_training_loan': True,
            'non_resident': False,
            'l10n_au_tax_free_threshold': True})
        inputs = [{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_bonus_commissions_prior').id,
                'name': 'Annual Bonus',
                'amount': 900,
            }]
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 5, 38, 1400),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 1400),
                ('OTE', 2300),
                ('BACKPAY', 900),
                ('GROSS', 2300),
                ('WITHHOLD', -271),
                ('BACKPAY.WITHHOLD', -312),
                ('WITHHOLD.STUDY', -94),  # 43 (STSL) + 52 (Backpay)
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -677),
                ('NET', 1622.92),
                ('SUPER', 264.5),
            ],
            input_lines=inputs,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 5),
        )

    def test_misc_payslip_11_child_support(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'weekly',
            'wage': 850,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False})
        employee.l10n_au_child_support_deduction = 320

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 5, 38, 850),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 850),
                ('OTE', 850),
                ('GROSS', 850),
                ('WITHHOLD', -206),
                ('WITHHOLD.TOTAL', -206),
                ('CHILD.SUPPORT', -129.5),
                ('NET', 514.5),
                ('SUPER', 97.75),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 5),
        )

    def test_misc_payslip_12_child_support(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'monthly',
            'wage': 3100,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True})
        employee.l10n_au_child_support_deduction = 1500

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 23, 174.8, 3100),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 3100),
                ('OTE', 3100),
                ('GROSS', 3100),
                ('WITHHOLD', -308),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -308),
                ('CHILD.SUPPORT', -554.84),
                ('NET', 2237.16),
                ('SUPER', 356.5),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_13_child_support(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'monthly',
            'wage': 4500,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False})

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 23, 174.8, 4500),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 4500),
                ('OTE', 4500),
                ('GROSS', 4500),
                ('WITHHOLD', -1157),
                ('WITHHOLD.TOTAL', -1157),
                ('CHILD.SUPPORT.GARNISHEE', -1800),
                ('CHILD.SUPPORT', -1800),
                ('NET', 1543.0),
                ('SUPER', 517.5),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_child_support_garnishee_periodic').id,
                'name': 'Garnishee Child Support',
                'amount': 1800,
            }],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_14_child_support(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'bi-weekly',
            'wage': 2800,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True})
        employee.l10n_au_child_support_garnishee_amount = 0.25

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 10, 76, 2800),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 2800),
                ('OTE', 2800),
                ('GROSS', 2800),
                ('WITHHOLD', -542),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -542),
                ('CHILD.SUPPORT.GARNISHEE', -564),
                ('CHILD.SUPPORT', -564),
                ('NET', 1693.38),
                ('SUPER', 322),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 12),
        )

    def test_misc_payslip_15_child_support(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'monthly',
            'wage': 6000,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True})
        employee.l10n_au_child_support_deduction = 300
        employee.l10n_au_child_support_garnishee_amount = 0.10

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 23, 174.8, 6000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6000),
                ('OTE', 6000),
                ('GROSS', 6000),
                ('WITHHOLD', -1157),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -1157),
                ('CHILD.SUPPORT.GARNISHEE', -484.3),
                ('CHILD.SUPPORT', -784.3),
                ('NET', 4058.7),
                ('SUPER', 690),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_16_medicare(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'weekly',
            'wage': 3000,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True,
            'medicare_surcharge': '3'})

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 5, 38, 3000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 3000),
                ('OTE', 3000),
                ('GROSS', 3000),
                ('WITHHOLD', -812),
                ('MEDICARE', -45),
                ('WITHHOLD.TOTAL', -857),
                ('NET', 2143),
                ('SUPER', 345),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 5),
        )

    def test_misc_payslip_17_medicare(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'monthly',
            'wage': 3100,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True,
            'medicare_exemption': 'H'})

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 23, 174.8, 3100),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 3100),
                ('OTE', 3100),
                ('GROSS', 3100),
                ('WITHHOLD', -247),
                ('MEDICARE', 31),
                ('WITHHOLD.TOTAL', -216),
                ('NET', 2884),
                ('SUPER', 356.5),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )

    def test_misc_payslip_18_medicare(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'bi-weekly',
            'wage': 2000,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True,
            'medicare_reduction': '3'})

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 10, 76, 2000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 2000),
                ('OTE', 2000),
                ('GROSS', 2000),
                ('WITHHOLD', -286.0),
                ('MEDICARE', 40),
                ('WITHHOLD.TOTAL', -246),
                ('NET', 1754.32),
                ('SUPER', 230),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 12),
        )

    def test_misc_payslip_19_basic_correction(self):
        self.tax_treatment_category = 'R'
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'monthly',
            'schedule_pay': 'weekly',
            'wage': 2000,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': True})
        self.assertEqual(employee.l10n_au_tax_treatment_code, "RTXXXX")
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 5, 38, 2000),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 2000),
                ('OTE', 2000),
                ('GROSS', 2000),
                ('WITHHOLD', -463.0),
                ('MEDICARE', 0),
                ('WITHHOLD.TOTAL', -463.0),
                ('NET', 1537.0),
                ('SUPER', 230),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 5),
            input_lines=[
            {
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_gross_income_correction_ote').id,
                'amount': -2000,
            },
            {
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_gross_income_correction_ote').id,
                'amount': 2000,
            },
            ]
        )
