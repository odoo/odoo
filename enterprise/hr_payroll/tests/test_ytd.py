# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase
from odoo.exceptions import ValidationError


class TestYTD(TestPayslipContractBase):

    @classmethod
    def setUpClass(cls):

        super().setUpClass()

        # A new company (and a new employee)
        cls.company_2 = cls.env['res.company'].create({'name': 'Odooo'})
        cls.shrek_emp = cls.env['hr.employee'].create({
            'name': 'Shrek',
            'company_id': cls.company_2.id,
        })
        cls.shrek_contract = cls.env['hr.contract'].create({
            'date_start': date(2000, 4, 22),
            'name': 'Contract for Shrek',
            'wage': 5000.33,
            'employee_id': cls.shrek_emp.id,
            'structure_type_id': cls.structure_type.id,
            'state': 'open',
        })

        # A new company (and a new employee)
        cls.company_3 = cls.env['res.company'].create({'name': 'Odooooooo'})
        cls.donkey_emp = cls.env['hr.employee'].create({
            'name': 'Donkey',
            'company_id': cls.company_3.id,
        })
        cls.donkey_contract = cls.env['hr.contract'].create({
            'date_start': date(2000, 4, 22),
            'name': 'Contract for Donkey',
            'wage': 5000.33,
            'employee_id': cls.donkey_emp.id,
            'structure_type_id': cls.structure_type.id,
            'state': 'open',
        })

    def _generate_payslip(self, date_from, struct, line_value, no_confirm=False,
            no_compute=False, employee=None, contract=None):
        """ Create a payslip with a payslip_line and a worked_days_line with a
        total or amount set on line_value.
        """
        # All tested payslips will last 1 month.
        # This shouldn't really matter anyway because date_from is not used to compute the YTD.
        date_to = date_from + relativedelta(months=1, days=-1)

        test_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip for YTD tests - ' + str(date_from),
            'employee_id': employee.id if employee else self.richard_emp.id,
            'contract_id': contract.id if contract else self.contract_cdi.id,
            'company_id': employee.company_id.id if employee else self.richard_emp.company_id.id,
            'struct_id': struct.id,
            'date_from': date_from,
            'date_to': date_to,
            'edited': True,
        })

        # A new rule, used to check if YTD is working on payslip_lines
        # In order to have better tests, it's great to be able to set a unique
        # value for each payslip (BUT with the same rule, for the computation
        # of the YTD). Yet, since compute_sheet will be called later, we can't
        # just create a new line, we must also create a special matching rule.
        test_rule = self.env['hr.salary.rule'].search([
            ('code', '=', 'TEST-YTD'),
            ('struct_id', '=', struct.id),
        ])

        if not test_rule:
            test_rule = self.env['hr.salary.rule'].create({
                'name': 'Rule for YTD test',
                'amount_select': 'code',
                'amount_python_compute':
                    "result = payslip.line_ids.filtered(lambda l: l.code == 'TEST-YTD')['total']",
                'code': 'TEST-YTD',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'struct_id': struct.id,
            })
        test_payslip.line_ids += self.env['hr.payslip.line'].create({
            'code': 'TEST-YTD',
            'name':  test_rule.name,
            'salary_rule_id': test_rule.id,
            'total': line_value,
            'slip_id': test_payslip.id,
        })

        # The already existing line, used to check if YTD is working on worked_days_lines
        test_worked_days = test_payslip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100')
        self.assertEqual(len(test_worked_days), 1)
        test_worked_days.amount = line_value

        # We compute and confirm the payslip
        if not no_compute:
            test_payslip.compute_sheet()
            if not no_confirm:
                test_payslip.action_payslip_done()

        return test_payslip

    def _assert_ytd_values(self, payslip, line_goal_value):
        """ Check if the payslip has the correct YTD values """
        test_line = payslip.line_ids.filtered(lambda l: l.code == 'BASIC')
        self.assertAlmostEqual(test_line.ytd, line_goal_value, delta=0.01,
            msg="The YTD of the slip line should be " + str(line_goal_value) +
                "$ but is currently " + str(test_line.ytd) + "$")

        test_worked_days = payslip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100')
        self.assertAlmostEqual(test_worked_days.ytd, line_goal_value, delta=0.01,
            msg="The YTD of the worked days line should be " + str(line_goal_value) +
                "$ but is currently " + str(test_worked_days.ytd) + "$")

    def test_ytd_00_classic_flow(self):
        """ This test checks if the YTD works in the main use case """
        # New structure to ensure we have no other payslip in it
        ytd_test_structure_00 = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 00',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })

        # Three payslips in the wrong years (they should not be taken into account)
        payslip_year_2023_A = self._generate_payslip(date(2023, 11, 1), ytd_test_structure_00, 1001)
        self._assert_ytd_values(payslip_year_2023_A, 1001)
        payslip_year_2023_B = self._generate_payslip(date(2023, 2, 1), ytd_test_structure_00, 1002)
        self._assert_ytd_values(payslip_year_2023_B, 1002)
        payslip_year_2025 = self._generate_payslip(date(2025, 2, 1), ytd_test_structure_00, 1004)
        self._assert_ytd_values(payslip_year_2025, 1004)

        # Three classic payslips (their totals should be summed in the YTD)
        payslip_january_A = self._generate_payslip(date(2024, 1, 1), ytd_test_structure_00, 1010)
        self._assert_ytd_values(payslip_january_A, 1010)
        payslip_march_A = self._generate_payslip(date(2024, 3, 1), ytd_test_structure_00, 1020)
        self._assert_ytd_values(payslip_march_A, 1010 + 1020)
        payslip_may = self._generate_payslip(date(2024, 5, 1), ytd_test_structure_00, 1040)
        self._assert_ytd_values(payslip_may, 1010 + 1020 + 1040)

        # Three payslips in the middle of the previous ones
        # (some of the previous payslips should be summed, but not all of them)
        payslip_february_A = self._generate_payslip(date(2024, 2, 1), ytd_test_structure_00, 1080)
        self._assert_ytd_values(payslip_february_A, 1010 + 1080)
        payslip_february_B = self._generate_payslip(date(2024, 2, 15), ytd_test_structure_00, 1160)
        self._assert_ytd_values(payslip_february_B, 1010 + 1080 + 1160)
        # This one should ideally take into account the 1st february and 15th february payslips,
        # but since we have not recomputed the 1st march payslip they will NOT be taken into account
        payslip_march_B = self._generate_payslip(date(2024, 3, 2), ytd_test_structure_00, 1320)
        self._assert_ytd_values(payslip_march_B, 1010 + 1020 + 1320)

        # One payslip exactly on the same period as another payslip
        # Its YTD should take into account the other payslip that ends on the same date.
        payslip_january_B = self._generate_payslip(date(2024, 1, 1), ytd_test_structure_00, 1640)
        self._assert_ytd_values(payslip_january_B, 1010 + 1640)

    def test_ytd_01_matching_payslips(self):
        """ This test checks if unwanted payslips are correctly excluded from the YTD """
        # New structure to ensure we have no other payslip in it
        ytd_test_structure_01 = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 01',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })

        # A classic payslip (nothing special here)
        payslip_classic_A = self._generate_payslip(date(2024, 1, 1), ytd_test_structure_01, 1010)
        self._assert_ytd_values(payslip_classic_A, 1010)

        # A 'draft' payslip : it should compute its own YTD as usual, but it
        # should not be taken into account while computing other payslips
        payslip_draft = self._generate_payslip(
            date(2024, 2, 1), ytd_test_structure_01, 1001, no_confirm=True
        )
        self._assert_ytd_values(payslip_draft, 1010 + 1001)

        # Another employee's payslip : it should not have any link with Richard's payslips
        payslip_another_employee = self._generate_payslip(
            date(2024, 3, 1), ytd_test_structure_01, 1002, employee=self.jules_emp
        )
        self._assert_ytd_values(payslip_another_employee, 1002)

        ytd_test_structure_01_bis = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 01 bis',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })

        # A payslip in another structure : it should not have any link with the other payslips
        payslip_another_structure = self._generate_payslip(
            date(2024, 4, 1), ytd_test_structure_01_bis, 1004
        )
        self._assert_ytd_values(payslip_another_structure, 1004)

        # A last classic payslip : it should only take into account the first 'classic' one
        payslip_classic_B = self._generate_payslip(date(2024, 5, 1), ytd_test_structure_01, 1020)
        self._assert_ytd_values(payslip_classic_B, 1010 + 1020)

    def test_ytd_02_reset_date(self):
        """ This test checks the reset date """
        # New structure to ensure we have no other payslip in it
        ytd_test_structure_02 = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 02',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })

        # Check the default reset date of the company
        self.assertEqual(self.richard_emp.company_id.ytd_reset_day, 1)
        self.assertEqual(self.richard_emp.company_id.ytd_reset_month, '1')

        reset_date = date(2024, 1, 1)
        # Tests of the behaviour of the reset date :
        self.richard_emp.company_id.ytd_reset_day = reset_date.day
        self.richard_emp.company_id.ytd_reset_month = str(reset_date.month)

        # First payslip, ending one day before the reset date
        payslip_before_reset = self._generate_payslip(
            reset_date + relativedelta(months=-1, days=0), ytd_test_structure_02, 1001
        )
        self._assert_ytd_values(payslip_before_reset, 1001)

        # Second payslip, ending exactly on the reset date
        # It should be considered in a new year, so its YTD should be 1010
        payslip_on_reset = self._generate_payslip(
            reset_date + relativedelta(months=-1, days=1), ytd_test_structure_02, 1010
        )
        self._assert_ytd_values(payslip_on_reset, 1010)

        # Third payslip, ending one day after the reset date
        # It's the second payslip of the new year, so its YTD should be 1010 + 1020
        payslip_after_reset = self._generate_payslip(
            reset_date + relativedelta(months=-1, days=2), ytd_test_structure_02, 1020
        )
        self._assert_ytd_values(payslip_after_reset, 1010 + 1020)

        # Since the 'reset day' field is an int with no constraint, a constraint is triggered
        # when it's edited. It should stay between 1 and the last day of the month

        self.richard_emp.company_id.ytd_reset_day = 1
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.richard_emp.company_id.ytd_reset_day = -20
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.richard_emp.company_id.ytd_reset_day = 0

        self.richard_emp.company_id.ytd_reset_month = '1'
        self.richard_emp.company_id.ytd_reset_day = 31
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.richard_emp.company_id.ytd_reset_day = 32

        # Since the reset day is 31, we can't change the month to april directly
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.richard_emp.company_id.ytd_reset_month = '4'
        self.richard_emp.company_id.ytd_reset_day = 30
        self.richard_emp.company_id.ytd_reset_month = '4'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.richard_emp.company_id.ytd_reset_day = 31

        # If the reset month is February, then the reset day will always be capped to 28.
        self.richard_emp.company_id.ytd_reset_day = 28
        self.richard_emp.company_id.ytd_reset_month = '2'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.richard_emp.company_id.ytd_reset_day = 29

        # Then, even in leap years, the reset date will stay on the 28th
        self.assertEqual(
            self.richard_emp.company_id.get_last_ytd_reset_date(date(2020, 6, 1)),
            date(2020, 2, 28)
        )

    def test_ytd_03_edit_payslip_lines_wizard(self):
        """ This test checks the edit_payslip_lines wizard """
        # New structure to ensure we have no other payslip in it
        ytd_test_structure_03 = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 03',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })

        # First payslip, a classic one
        payslip_classic_A = self._generate_payslip(date(2024, 1, 1), ytd_test_structure_03, 1001)
        self._assert_ytd_values(payslip_classic_A, 1001)

        # Second payslip, the one which will be edited
        payslip_to_edit = self._generate_payslip(
            date(2024, 6, 1), ytd_test_structure_03, 1002, no_confirm=True
        )
        self._assert_ytd_values(payslip_to_edit, 1001 + 1002)

        # Opening the edit_payslip_lines wizard
        action = payslip_to_edit.action_edit_payslip_lines()
        wizard = self.env[action['res_model']].browse(action['res_id'])

        # Editing the YTD values
        test_slip_lines = wizard.line_ids.filtered(lambda l: l.code == 'BASIC')
        self.assertEqual(len(test_slip_lines), 1)
        test_slip_lines.ytd = 6010

        test_worked_days = wizard.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100')
        self.assertEqual(len(test_worked_days), 1)
        test_worked_days.ytd = 6010

        # Checking if the edit worked on the current payslip
        wizard.action_validate_edition()
        payslip_to_edit.action_payslip_done()
        self._assert_ytd_values(payslip_to_edit, 6010)

        # Two new payslips to ensure that the change is taken into account in the future
        payslip_classic_B = self._generate_payslip(date(2024, 7, 1), ytd_test_structure_03, 1020)
        self._assert_ytd_values(payslip_classic_B, 6010 + 1020)
        payslip_classic_C = self._generate_payslip(date(2024, 8, 1), ytd_test_structure_03, 1040)
        self._assert_ytd_values(payslip_classic_C, 6010 + 1020 + 1040)

    def test_ytd_04_compute_many_payslips_together(self):
        """ This test ensures that the YTD values are computed correctly if we compute
        a lot of them at the same time, even if we have payslips with much different
        caracteristics in the lot (different companies, different years, ...)
        """
        # New structure to ensure we have no other payslip in it
        ytd_test_structure_04 = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 04',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })

        # A few preliminary payslips

        # First payslip, a classic one
        payslip_lot0_classic = self._generate_payslip(date(2024, 1, 1), ytd_test_structure_04, 1)
        self._assert_ytd_values(payslip_lot0_classic, 1)
        # A payslip in a different company (and so a different employee), same reset date
        payslip_lot0_company_2 = self._generate_payslip(
            date(2024, 1, 1), ytd_test_structure_04, 2,
            employee=self.shrek_emp, contract=self.shrek_contract
        )
        self._assert_ytd_values(payslip_lot0_company_2, 2)
        # A payslip in a different company (and so a different employee), different reset date
        self.company_3.ytd_reset_month = '4'
        payslip_lot0_company_3 = self._generate_payslip(
            date(2024, 1, 1), ytd_test_structure_04, 4,
            employee=self.donkey_emp, contract=self.donkey_contract
        )
        self._assert_ytd_values(payslip_lot0_company_3, 4)

        # First lot of payslips

        # A classic payslip
        payslip_lot1_classic_A = self._generate_payslip(
            date(2024, 2, 1), ytd_test_structure_04, 8, no_compute=True
        )
        # A payslip with a different employee
        payslip_lot1_another_employee = self._generate_payslip(
            date(2024, 3, 1), ytd_test_structure_04, 16, no_compute=True, employee=self.jules_emp
        )
        # A payslip in a different structure
        ytd_test_structure_04_bis = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 04 bis',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })
        payslip_lot1_another_structure = self._generate_payslip(
            date(2024, 4, 1), ytd_test_structure_04_bis, 32, no_compute=True
        )
        # A payslip in the following year
        payslip_lot1_another_year = self._generate_payslip(
            date(2025, 3, 1), ytd_test_structure_04, 64, no_compute=True
        )
        # Two payslips in a different company (and so a different employee)
        # but with the same reset date
        payslip_lot1_company_2_A = self._generate_payslip(
            date(2024, 2, 1), ytd_test_structure_04, 128, no_compute=True,
            employee=self.shrek_emp, contract=self.shrek_contract
        )
        payslip_lot1_company_2_B = self._generate_payslip(
            date(2024, 6, 1), ytd_test_structure_04, 256, no_compute=True,
            employee=self.shrek_emp, contract=self.shrek_contract
        )
        # Two payslips in a different company (and so a different employee)
        # but with a different reset date
        payslip_lot1_company_3_A = self._generate_payslip(
            date(2024, 2, 1), ytd_test_structure_04, 512, no_compute=True,
            employee=self.donkey_emp, contract=self.donkey_contract
        )
        payslip_lot1_company_3_B = self._generate_payslip(
            date(2024, 6, 1), ytd_test_structure_04, 1024, no_compute=True,
            employee=self.donkey_emp, contract=self.donkey_contract
        )
        # Finally, two classic payslips (to ensure the order doesn't change anything)
        payslip_lot1_classic_B = self._generate_payslip(
            date(2024, 5, 1), ytd_test_structure_04, 2048, no_compute=True
        )
        payslip_lot1_classic_C = self._generate_payslip(
            date(2024, 6, 1), ytd_test_structure_04, 4096, no_compute=True
        )

        payslip_lot_1 = payslip_lot1_classic_A + payslip_lot1_another_employee +\
            payslip_lot1_another_structure + payslip_lot1_another_year + payslip_lot1_company_2_A +\
            payslip_lot1_company_2_B + payslip_lot1_company_3_A + payslip_lot1_company_3_B +\
            payslip_lot1_classic_B + payslip_lot1_classic_C

        payslip_lot_1.compute_sheet()
        payslip_lot_1.action_payslip_done()

        # Tiny little check : the change of company did work correctly
        self.assertEqual(payslip_lot1_company_2_A.company_id, self.company_2)

        # Main check : the YTD values were computed correctly
        self._assert_ytd_values(payslip_lot1_classic_A, 1 + 8)
        self._assert_ytd_values(payslip_lot1_another_employee, 16)
        self._assert_ytd_values(payslip_lot1_another_structure, 32)
        self._assert_ytd_values(payslip_lot1_another_year, 64)
        self._assert_ytd_values(payslip_lot1_company_2_A, 2 + 128)
        self._assert_ytd_values(payslip_lot1_company_2_B, 2 + 256)
        self._assert_ytd_values(payslip_lot1_company_3_A, 4 + 512)
        self._assert_ytd_values(payslip_lot1_company_3_B, 1024)
        self._assert_ytd_values(payslip_lot1_classic_B, 1 + 2048)
        self._assert_ytd_values(payslip_lot1_classic_C, 1 + 4096)

        # Second lot of payslips

        # A classic payslip
        payslip_lot2_classic = self._generate_payslip(
            date(2024, 7, 1), ytd_test_structure_04, 8192, no_compute=True
        )
        # A payslip with a different employee
        payslip_lot2_another_employee = self._generate_payslip(
            date(2024, 8, 1), ytd_test_structure_04, 16384, no_compute=True,
            employee=self.jules_emp
        )
        # A payslip in a different structure
        payslip_lot2_another_structure = self._generate_payslip(
            date(2024, 9, 1), ytd_test_structure_04_bis, 32768, no_compute=True
        )
        # A payslip in the following year
        payslip_lot2_another_year = self._generate_payslip(
            date(2025, 10, 1), ytd_test_structure_04, 65536, no_compute=True
        )
        # A payslip in a different company (and so a different employee)
        payslip_lot2_company_2 = self._generate_payslip(
            date(2024, 11, 1), ytd_test_structure_04, 131072, no_compute=True,
            employee=self.shrek_emp, contract=self.shrek_contract
        )

        payslip_lot_2 = payslip_lot2_classic + payslip_lot2_another_employee +\
            payslip_lot2_another_structure + payslip_lot2_another_year + payslip_lot2_company_2

        payslip_lot_2.compute_sheet()
        payslip_lot_2.action_payslip_done()

        self._assert_ytd_values(payslip_lot2_classic, 1 + 4096 + 8192)
        self._assert_ytd_values(payslip_lot2_another_employee, 16 + 16384)
        self._assert_ytd_values(payslip_lot2_another_structure, 32 + 32768)
        self._assert_ytd_values(payslip_lot2_another_year, 64 + 65536)
        self._assert_ytd_values(payslip_lot2_company_2, 2 + 256 + 131072)

    def test_ytd_05_reset_date_with_many_payslips_together(self):
        """ This really specific test ensures that the earliest_ytd_date_to
        from _get_ytd_payslips is correct, in the case where we compute in the
        same time a few payslips from different companies
        """
        # New structure to ensure we have no other payslip in it
        ytd_test_structure_05 = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for YTD test 05',
            'type_id': self.structure_type.id,
            'ytd_computation': True,
        })

        # Changing the reset dates of the companies
        self.richard_emp.company_id.ytd_reset_month = '5'
        self.company_2.ytd_reset_month = '3'
        self.company_3.ytd_reset_month = '7'

        # A preliminary payslip (company 2)
        payslip_company_2_preliminary = self._generate_payslip(
            date(2024, 4, 1), ytd_test_structure_05, 1010,
            employee=self.shrek_emp, contract=self.shrek_contract
        )
        self._assert_ytd_values(payslip_company_2_preliminary, 1010)

        # A lot with 3 payslips from the 3 different companies
        payslip__company_1_lot = self._generate_payslip(
            date(2024, 10, 1), ytd_test_structure_05, 1001, no_compute=True,
            employee=self.richard_emp, contract=self.contract_cdi
        )
        payslip__company_2_lot = self._generate_payslip(
            date(2024, 12, 1), ytd_test_structure_05, 1020, no_compute=True,
            employee=self.shrek_emp, contract=self.shrek_contract
        )
        payslip__company_3_lot = self._generate_payslip(
            date(2024, 10, 1), ytd_test_structure_05, 1002, no_compute=True,
            employee=self.donkey_emp, contract=self.donkey_contract
        )

        payslip_lot = payslip__company_1_lot + payslip__company_2_lot + payslip__company_3_lot

        payslip_lot.compute_sheet()
        payslip_lot.action_payslip_done()

        self._assert_ytd_values(payslip__company_2_lot, 1010 + 1020)
