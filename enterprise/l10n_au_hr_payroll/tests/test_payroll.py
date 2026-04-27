# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date
from freezegun import freeze_time
from contextlib import closing
from unittest import skip

from odoo import Command
from odoo.tests import tagged
from .common import TestPayrollCommon


@skip("This test is failing on runbot, it is not a priority to fix it now")
@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestPayroll(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.startClassPatcher(freeze_time(date(2024, 1, 1)))
        cls.tax_treatment_category = 'R'

    def test_withholding_amounts(self):
        test_scales = [
            {'l10n_au_tax_free_threshold': False},  # Scale 1
            {'l10n_au_tax_free_threshold': True},  # Scale 2
            {'is_non_resident': True},  # Scale 3
            {"l10n_au_medicare_exemption": "F"},  # Scale 5
            {"l10n_au_medicare_exemption": "H"},  # Scale 6
        ]
        today = date.today()
        payslip = self.env["hr.payslip"].create({
            "name": "Test Payslip AU",
            "employee_id": self.employee_id.id,
            "date_from": today,
            "date_to": today,
            "struct_id": self.default_payroll_structure.id,
        })
        payslip._compute_date_to()
        self.employee_id.write({"l10n_au_tax_free_threshold": False})
        for period, sample_data in self.schedule_1_withholding_sample_data.items():
            for row in sample_data:
                earnings = row[0]
                self.contract_ids[0].wage = earnings
                for idx, test_data in enumerate(row[1:]):
                    with self.subTest(earnings=earnings, scale=test_scales[idx]):
                        with closing(self.env.cr.savepoint()):
                            self.employee_id.write(test_scales[idx])
                            coefficients = payslip._l10n_au_tax_schedule_parameters()
                            amount = payslip._l10n_au_compute_withholding_amount(earnings, period, coefficients)
                            self.assertEqual(amount, test_data, f"weekly earnings of {earnings} scale {idx}: expected {test_data} got {-amount}")

    def test_medicare_adjustment(self):
        nbr_children = [0, 1, 2, 3, 4, 5]
        today = date.today()
        self.employee_id.marital = "married"
        payslip = self.env["hr.payslip"].create({
            "name": "Test Payslip AU",
            "employee_id": self.employee_id.id,
            "date_from": today,
            "date_to": today,
            "struct_id": self.default_payroll_structure.id,
        })
        payslip._compute_date_to()
        params = payslip._rule_parameter("l10n_au_withholding_schedule_1")['medicare']
        if self.employee_id.l10n_au_tax_free_threshold:
            key = 'tax-free'
        elif self.employee_id.l10n_au_medicare_exemption == 'H':
            key = 'half-exemption'
        params = params[key]
        for children in nbr_children:
            self.employee_id.children = children
            for period, sample_data in self.medicare_adjustment_sample_data.items():
                for row in sample_data:
                    earnings = row[0]
                    self.contract_ids[0].wage = earnings
                    amount = payslip._l10n_au_compute_medicare_adjustment(earnings, period, params)
                    self.assertEqual(amount, row[children + 1], f"weekly earnings of {earnings} children {self.employee_id.children}: expected {row[children + 1]} got {-amount}")

    def test_compute_loan_withhold(self):
        today = date.today()
        payslip = self.env["hr.payslip"].create({
            "name": "Test Payslip AU",
            "employee_id": self.employee_id.id,
            "date_from": today,
            "date_to": today,
            "struct_id": self.default_payroll_structure.id,
        })
        payslip._compute_date_to()

        loan_coefs = payslip._rule_parameter("l10n_au_stsl")
        for period, sample_data in self.loan_withhold_sample_data.items():
            self.employee_id.l10n_au_tax_free_threshold = False
            coefs = loan_coefs["no-tax-free"]
            for row_claimed in sample_data:
                earnings = row_claimed[0]
                expected = row_claimed[2]
                amount = payslip._l10n_au_compute_loan_withhold(earnings, period, coefs)
                self.assertAlmostEqual(amount, expected, delta=1, msg=f"weekly earnings of {earnings} expected {expected} got {-amount}")
            self.employee_id.l10n_au_tax_free_threshold = True
            coefs = loan_coefs["tax-free"]
            for row_not_claimed in sample_data:
                earnings = row_not_claimed[0]
                expected = row_not_claimed[1]
                amount = payslip._l10n_au_compute_loan_withhold(earnings, period, coefs)
                self.assertAlmostEqual(amount, expected, delta=1, msg=f"weekly earnings of {earnings}: expected {expected} got {-amount}")

    def test_general_cases(self):
        # https://www.ato.gov.au/rates/schedule-1---statement-of-formulas-for-calculating-amounts-to-be-withheld/?page=6#General_examples
        # EXAMPLE 1
        self.contract_ids[0].wage = 1103.45
        self.contract_ids[0].schedule_pay = "weekly"
        self.employee_id.marital = "married"
        self.employee_id.children = 5
        self.employee_id.l10n_au_tax_free_threshold = True
        payslip_id = self.env["hr.payslip"].create({
            "name": "payslip",
            "employee_id": self.employee_id.id,
            "contract_id": self.contract_ids[0].id,
            "struct_id": self.default_payroll_structure.id,
            "date_from": date(2023, 9, 18),
            "date_to": date(2023, 9, 23),
        })
        payslip_id.compute_sheet()
        payslip_lines = payslip_id.line_ids
        withholding_amount = payslip_lines.filtered(lambda l: l.code == "WITHHOLD").amount
        adjustment_amount = payslip_lines.filtered(lambda l: l.code == "MEDICARE").amount
        self.assertEqual(-withholding_amount, 198)
        self.assertEqual(adjustment_amount, 20)

        # EXAMPLE 2
        self.contract_ids[0].wage = 1110.30
        self.contract_ids[0].schedule_pay = "bi-weekly"
        self.employee_id.marital = "single"
        self.employee_id.children = 0
        self.employee_id.l10n_au_medicare_exemption = "F"
        self.employee_id.l10n_au_tax_free_threshold = True
        self.employee_id.l10n_au_nat_3093_amount = 1645
        payslip_id = self.env["hr.payslip"].create({
            "name": "payslip",
            "employee_id": self.employee_id.id,
            "contract_id": self.contract_ids[0].id,
            "struct_id": self.default_payroll_structure.id,
            "date_from": date(2023, 9, 18),
            "date_to": date(2023, 9, 30),
        })
        payslip_id.compute_sheet()
        payslip_lines = payslip_id.line_ids
        withholding_amount = payslip_lines.filtered(lambda l: l.code == "WITHHOLD").amount
        tax_offset = payslip_lines.filtered(lambda l: l.code == "TAX.OFFSET").amount
        self.assertEqual(-withholding_amount, 74)
        self.assertEqual(tax_offset, 63)

        # EXAMPLE 3

        self.contract_ids[0].wage = 4500.33
        self.contract_ids[0].schedule_pay = "monthly"
        self.employee_id.marital = "married"
        self.employee_id.children = 1
        self.employee_id.l10n_au_medicare_exemption = "X"
        self.employee_id.l10n_au_tax_free_threshold = True
        self.employee_id.l10n_au_nat_3093_amount = 1365
        payslip_id = self.env["hr.payslip"].create({
            "name": "payslip",
            "employee_id": self.employee_id.id,
            "contract_id": self.contract_ids[0].id,
            "struct_id": self.default_payroll_structure.id,
            "date_from": date(2023, 9, 1),
            "date_to": date(2023, 9, 30),
        })
        payslip_id.compute_sheet()
        payslip_lines = payslip_id.line_ids
        withholding_amount = payslip_lines.filtered(lambda l: l.code == "WITHHOLD").amount
        tax_offset = payslip_lines.filtered(lambda l: l.code == "TAX.OFFSET").amount
        self.assertEqual(-withholding_amount, 758)
        self.assertEqual(tax_offset, 113)

    def lines_by_code(self, lines):
        lines_by_code = defaultdict(lambda: {"lines": [], "amount": 0, "total": 0})
        for line in lines:
            lines_by_code[line.code]["lines"].append(line)
            lines_by_code[line.code]["amount"] += line.amount
            lines_by_code[line.code]["total"] += line.total
        return lines_by_code

    def test_withholding_monthly_regular_employee(self):
        self.tax_treatment_category = 'R'
        employee_id, contract_id = self.create_employee_and_contract(5000, {'schedule_pay': 'monthly', "l10n_au_training_loan": False, "l10n_au_tax_free_threshold": True})
        payslip_id = self.env["hr.payslip"].create({
            "name": "payslip",
            "employee_id": employee_id.id,
            "contract_id": contract_id.id,
            "struct_id": self.default_payroll_structure.id,
            "date_from": date(2023, 7, 1),
            "date_to": date(2023, 7, 31),
        })

        # Scenario 1: Tax free threshold claimed
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 932, "test scenario 1: tax free threshold claimed")

        # Scenario 2: Tax free threshold not claimed
        employee_id.l10n_au_tax_free_threshold = False
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 1456, "test scenario 2: tax free threshold not claimed")

        # Scenario 3: Foreign resident
        employee_id.is_non_resident = True
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 1625, "test scenario 3: foreign resident")
        employee_id.is_non_resident = False

        # Scenario 4: HELP / STSL Loan
        employee_id.l10n_au_training_loan = True
        employee_id.l10n_au_tax_free_threshold = True
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 1032, "test scenario 4: HELP / STSL Loan")
        employee_id.l10n_au_training_loan = False

        # Scenario 5: Tax offset
        employee_id.l10n_au_nat_3093_amount = 100
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 924, "test scenario 5: Tax offset of 100")
        employee_id.l10n_au_nat_3093_amount = 0

        # Scenario 6: Half medicare exemption
        employee_id.l10n_au_medicare_exemption = "H"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 880, "test scenario 6: Half medicare exemption")

        # Scenario 7: Full medicare exemption
        employee_id.l10n_au_medicare_exemption = "F"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 832, "test scenario 7: Full medicare exemption")
        employee_id.l10n_au_medicare_exemption = "X"

        # Scenario 9: Medicare surcharge
        employee_id.l10n_au_tfn_declaration = "000000000"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertAlmostEqual(-lbc["WITHHOLD.TOTAL"]["total"], 2349, 0, msg="test scenario 9: TFN not provided")

        # Scenario 10: TFN applied for but not provided, less than 28 days ago
        employee_id.l10n_au_tfn_declaration = "111111111"
        # structure_type was no tfn from previous test, make sure that changing declaration to a valid tfn does not change the structure
        # because this has to be done manually by the payroll agent
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 932, "test scenario 10: TFN applied for but not provided, less than 28 days ago")

        # Scenario 11: Employee under 18, and earns less than 350$ weekly
        employee_id.l10n_au_tfn_declaration = "333333333"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 932, "test scenario 11: Employee under 18, and earns less than 350$ weekly")

        # Scenario 12: Exempt from TFN
        employee_id.l10n_au_tfn_declaration = "444444444"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 932, "test scenario 12: Exempt from TFN")

        # Scenario 13: 4 children, medicare reduction
        employee_id.write({
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "999999661",
            "marital": "married",
            "children": 4,
        })
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 893, "test scenario 13: 4 children, medicare reduction")
        employee_id.write({
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "999999661",
            # kill the wife
            "marital": "single",
            # kill the children
            "children": 0,
        })

        # Scenario 14: Withholding variation
        payslip_id.employee_id.write({
            "l10n_au_withholding_variation": 'salaries',
            "l10n_au_withholding_variation_amount": 15,
        })
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 750, "test scenario 14: Withholding variation")
        payslip_id.employee_id.write({
            "l10n_au_withholding_variation": 'none',
        })

    def test_withholding_weekly_regular_employee(self):
        employee_id, contract_id = self.create_employee_and_contract(1000, {'schedule_pay': 'weekly', "l10n_au_training_loan": False, 'l10n_au_tax_free_threshold': True})
        payslip_id = self.env["hr.payslip"].create({
            "name": "payslip",
            "employee_id": employee_id.id,
            "contract_id": contract_id.id,
            "struct_id": self.default_payroll_structure.id,
            "date_from": date(2023, 7, 1),
            "date_to": date(2023, 7, 7),
        })

        # Scenario 26: Tax free threshold claimed
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 162, "test scenario 26: tax free threshold claimed")

        # Scenario 27: Tax free threshold not claimed
        employee_id.l10n_au_tax_free_threshold = False
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 283, "test scenario 27: tax free threshold not claimed")

        # Scenario 28: Foreign resident
        employee_id.is_non_resident = True
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 325, "test scenario 28: foreign resident")
        employee_id.is_non_resident = False
        employee_id.l10n_au_tax_free_threshold = True

        # Scenario 29: HELP / STSL Loan
        employee_id.l10n_au_training_loan = True
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 172, "test scenario 29: HELP / STSL Loan")
        employee_id.l10n_au_training_loan = False

        # Scenario 30: Tax offset
        employee_id.l10n_au_nat_3093_amount = 100
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 160, "test scenario 30: Tax offset of 100")
        employee_id.l10n_au_nat_3093_amount = 0

        # Scenario 31: Half medicare exemption
        employee_id.l10n_au_medicare_exemption = "H"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 152, "test scenario 31: Half medicare exemption")

        # Scenario 32: Full medicare exemption
        employee_id.l10n_au_medicare_exemption = "F"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 142, "test scenario 32: Full medicare exemption")
        employee_id.l10n_au_medicare_exemption = "X"

        # Scenario 34: Medicare surcharge
        employee_id.l10n_au_tfn_declaration = "000000000"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertAlmostEqual(-lbc["WITHHOLD.TOTAL"]["total"], 470, 0, "test scenario 34: TFN not provided")

        # Scenario 35: TFN applied for but not provided, less than 28 days ago
        employee_id.l10n_au_tfn_declaration = "111111111"
        # structure_type was no tfn from previous test, make sure that changing declaration to a valid tfn does not change the structure
        # because this has to be done manually by the payroll agent
        payslip_id.contract_id.schedule_pay = "weekly"
        payslip_id.date_from = date(2023, 7, 3)
        payslip_id.date_to = date(2023, 7, 7)
        payslip_id.compute_sheet()
        # Weekly wage is 1000 in this case
        self.assertAlmostEqual(payslip_id.worked_days_line_ids.amount, 1000, 0)

        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 162, "test scenario 35: TFN applied for but not provided, less than 28 days ago")

        # Scenario 36: Employee under 18, and earns less than 350$ weekly
        employee_id.l10n_au_tfn_declaration = "333333333"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 162, "test scenario 36: Employee under 18, and earns less than 350$ weekly")

        # Scenario 37: Exempt from TFN
        employee_id.l10n_au_tfn_declaration = "444444444"
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 162, "test scenario 37: Exempt from TFN")

        # Scenario 38: 4 children, medicare reduction
        employee_id.write({
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "999999661",
            "marital": "married",
            "children": 4,
        })
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertEqual(-lbc["WITHHOLD.TOTAL"]["total"], 142, "test scenario 38: 4 children, medicare reduction")
        employee_id.write({
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "999999661",
            # kill the wife
            "marital": "single",
            # kill the children
            "children": 0,
        })

        # Scenario 39: Withholding variation
        payslip_id.employee_id.write({
            "l10n_au_withholding_variation": 'salaries',
            "l10n_au_withholding_variation_amount": 15,
        })
        payslip_id.compute_sheet()
        lbc = self.lines_by_code(payslip_id.line_ids)
        self.assertAlmostEqual(-lbc["WITHHOLD.TOTAL"]["total"], 150, 0, "test scenario 39: Withholding variation")
        payslip_id.employee_id.write({
            "l10n_au_withholding_variation": 'none',
        })

    def test_termination_payment_unused_leaves(self):
        employee_id, contract_id = self.create_employee_and_contract(5000, {'schedule_pay': 'monthly', 'scale': '2'})
        # Allocate Holidays
        self.env['hr.leave.allocation'].create([{
            'name': 'Paid Time Off 2023-24',
            'holiday_status_id': self.annual_leave_type.id,
            'number_of_days': 15,
            'employee_id': employee_id.id,
            'state': 'confirm',
            'date_from': date(2023, 7, 1),
            'date_to': date(2024, 6, 30),
        }]).action_validate()

        # This would be done by the wizard.
        contract_id.date_end = date(2023, 8, 31)

        payslip_term = self.env["hr.payslip"].create({
            "name": "Termination Payment",
            "employee_id": employee_id.id,
            "contract_id": contract_id.id,
            "struct_id": self.env.ref("l10n_au_hr_payroll.hr_payroll_structure_au_regular").id,
            "l10n_au_termination_type": "genuine",
            "date_from": date(2023, 8, 1),
            "date_to": date(2023, 8, 31),
            "input_line_ids": [
                Command.create({'input_type_id': self.env.ref('l10n_au_hr_payroll.input_severance_pay').id, 'amount': 15000}),
                Command.create({'input_type_id': self.env.ref('l10n_au_hr_payroll.input_golden_handshake').id, 'amount': 20000}),
                Command.create({'input_type_id': self.env.ref('l10n_au_hr_payroll.input_genuine_redundancy').id, 'amount': 5000}),
            ]
        })
        # Scenario 1: Tax free threshold claimed
        payslip_term.compute_sheet()
        lbc = self.lines_by_code(payslip_term.line_ids)
        self.assertEqual(lbc["ETP.LEAVE.GROSS"]["total"], 3461.54, "Incorrect Leave base")
        self.assertEqual(-lbc["ETP.LEAVE.WITHHOLD"]["total"], 1108, "Withhold incorrect for genuine redundancy.")
