# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import fields
from odoo.tests import tagged
from .common import TestPayrollCommon


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestPayrollUnusedLeaves(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_payroll_structure = cls.env.ref("l10n_au_hr_payroll.hr_payroll_structure_au_regular")
        cls.tax_treatment_category = 'R'
        cls.long_service = cls.env['hr.leave.type'].create({
            'name': 'Long Service Leave',
            'company_id': cls.australian_company.id,
            'l10n_au_leave_type': 'long_service',
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_long_service_leave').id,
        })
        cls.annual = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave',
            'company_id': cls.australian_company.id,
            'l10n_au_leave_type': 'annual',
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_paid_time_off').id,
        })

    # Unused leaves tests
    def get_unused_leaves_employee(self, birthday, date_start, date_end, leave_loading=('once', 0), tfn_provided=True, resident=True):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'leave_loading': leave_loading[0],
            'leave_loading_rate': leave_loading[1],
            'salary_sacrifice_superannuation': 0,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            # 'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date(birthday),
            'contract_date_start': fields.Date.to_date(date_start),
            'contract_date_end': fields.Date.to_date(date_end),
            'tfn': 999999661,
            'tfn_declaration': 'provided' if tfn_provided else '000000000',
            'non_resident': not resident,
            'l10n_au_tax_free_threshold': resident
        })
        employee.is_non_resident = not resident
        return employee, contract

    def create_leaves(self, employee, contract, leaves):
        """ Creates Allocations and Leaves

        Args:
            employee (hr.employee)
            leaves (dict): {
            "annual": {
                "pre_1993": unused_leaves,
                "post_1993": unused_leaves,
            },
            "long_service": {
                "pre_1978": unused_leaves,
                "pre_1993": unused_leaves,
                "post_1993": unused_leaves,
            },
        }
        """
        dates = {
            "pre_1978": {"start": date(1976, 1, 1), "end": date(1978, 8, 15)},
            "pre_1993": {"start": date(1978, 8, 17), "end": date(1993, 8, 16)},
            "post_1993": {"start": date(1993, 8, 19), "end": max(contract.date_end, date.today())},
        }
        for leave_type, amount in leaves.items():
            leave_type_id = self.annual if leave_type == 'annual' else self.long_service
            for period, number_of_days in amount.items():
                start_date = dates[period]['start']
                end_date = max(dates[period]['end'], contract.date_end or dates[period]['end'])

                # Allocate Holidays
                allocation = self.env['hr.leave.allocation'].create([{
                    'name': f'{leave_type_id.name} Allocation',
                    'holiday_status_id': leave_type_id.id,
                    'number_of_days': number_of_days,
                    'employee_id': employee.id,
                    'state': 'confirm',
                    'date_from': start_date,
                    'date_to': end_date,
                }])
                allocation.action_validate()

                self.assertAlmostEqual(allocation.number_of_days, number_of_days)

    # AL only + non-genuine + TFN
    def test_01_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1995-6-8', '2022-1-3', '2024-3-12')
        self.create_leaves(
            employee,
            contract,
            {
                "annual": {
                    "post_1993": 14.84,
                }
            },
        )

        self.assertFalse(employee.is_non_resident)
        self.assertEqual(employee.l10n_au_tfn_declaration, 'provided')

        expected_gross = 4794.45
        expected_withhold = -1668
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    def test_02_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1976-1-1', '1992-8-17', '2024-3-12')
        self.create_leaves(
            employee,
            contract,
            leaves={
                "annual": {
                    "pre_1993": 20,
                    "post_1993": 10.42,
                }
            },
        )

        expected_gross = 9827.97
        expected_withhold = -3207.69
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # AL only + genuine + TFN
    def test_03_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1976-1-1', '1992-8-17', '2024-3-12')
        self.create_leaves(
            employee,
            contract,
            leaves={
                "annual": {
                    "pre_1993": 20,
                    "post_1993": 10.42,
                }
            },
        )

        expected_gross = 9827.97
        expected_withhold = -3144.95
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="genuine"
        )

    # AL only + non-genuine + TFN + loading
    def test_04_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1995-6-8', '2022-1-3', '2024-3-12', ('regular', 17.5))
        self.create_leaves(
            employee,
            contract,
            {
                "annual": {
                    "post_1993": 14.84,
                }
            },
        )

        expected_gross = 5633.48
        expected_withhold = -1920
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # AL only + non-genuine + TFN + loading
    def test_05_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1976-1-1', '1992-01-1', '2024-3-12', ('regular', 17.5))
        self.create_leaves(
            employee,
            contract,
            leaves={
                "annual": {
                    "pre_1993": 20,
                    "post_1993": 10.42,
                }
            },
        )

        expected_gross = 11547.87
        expected_withhold = -3785.53
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # AL only + genuine + TFN + loading
    def test_06_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1976-1-1', '1992-08-1', '2024-3-12', ('regular', 17.5))
        self.create_leaves(
            employee,
            contract,
            leaves={
                "annual": {
                    "pre_1993": 20,
                    "post_1993": 10.42,
                }
            },
        )

        expected_gross = 11547.87
        expected_withhold = -3695.32
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="genuine"
        )

    # < $300 + > 1993 + 32% is smaller
    def test_07_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1995-6-8', '2022-1-3', '2024-3-12')
        self.create_leaves(
            employee,
            contract,
            {
                "annual": {
                    "post_1993": 0.5,
                }
            },
        )

        expected_gross = 161.54
        expected_withhold = -48
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # < $300 + > 1993 + standard is smaller
    def test_08_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1995-6-8', '2022-1-3', '2024-3-12')
        self.create_leaves(
            employee,
            contract,
            {
                "annual": {
                    "post_1993": 0.25,
                }
            },
        )

        expected_gross = 80.77
        expected_withhold = 0
        normal_withholding = -247.0

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # No TFN + Resident
    def test_09_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1995-6-8', '2022-1-3', '2024-3-12', tfn_provided=False)
        self.create_leaves(
            employee,
            contract,
            {
                "annual": {
                    "post_1993": 14.84,
                }
            },
        )

        employee.l10n_au_tax_free_threshold = False
        self.assertFalse(employee.is_non_resident)
        self.assertEqual(employee.l10n_au_tfn_declaration, '000000000')

        expected_gross = 4794.45
        expected_withhold = -2253.39
        normal_withholding = -1213.85
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # No TFN + Foreign Resident
    def test_10_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1995-6-8', '2022-1-3', '2024-3-12', tfn_provided=False, resident=False)
        self.create_leaves(
            employee,
            contract,
            {
                "annual": {
                    "post_1993": 14.84,
                }
            },
        )

        self.assertTrue(employee.is_non_resident)
        self.assertEqual(employee.l10n_au_tfn_declaration, '000000000')

        expected_gross = 4794.45
        expected_withhold = -2157.5
        normal_withholding = -1163
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # Withholding Var. + impact leaves
    def test_11_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1976-1-1', '1992-08-1992', '2024-3-12')
        employee.l10n_au_withholding_variation = "leaves"
        employee.l10n_au_withholding_variation_amount = 30

        self.create_leaves(
            employee,
            contract,
            leaves={
                "annual": {
                    "post_1993": 14.84,
                }
            },
        )

        expected_gross = 4794.45
        expected_withhold = -1438.33
        normal_withholding = -775.38
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # Withholding Var. + does not impact leaves
    def test_12_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1976-1-1', '1992-08-1992', '2024-3-12')
        employee.l10n_au_withholding_variation = "salaries"
        employee.l10n_au_withholding_variation_amount = 30
        self.create_leaves(
            employee,
            contract,
            leaves={
                "annual": {
                    "post_1993": 14.84,
                }
            },
        )

        expected_gross = 4794.45
        expected_withhold = -1668
        normal_withholding = -775.38
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 8.0, 60.8, 2584.61),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 2584.61),
                ("OTE", 2584.61),
                ("GROSS", 2584.61),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 2584.61 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 284),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # LSL only + non-genuine + > 1993
    def test_13_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1980-1-1', '2002-1-1', '2024-1-1')
        self.create_leaves(
            employee,
            contract,
            {
                "long_service": {
                    "post_1993": 112,
                }
            },
        )

        self.assertFalse(employee.is_non_resident)
        self.assertEqual(employee.l10n_au_tfn_declaration, 'provided')

        expected_gross = 36184.51
        expected_withhold = -12480
        normal_withholding = 0
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 1.0, 7.6, 323.08),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 323.08),
                ("OTE", 323.08),
                ("GROSS", 323.08),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 323.08 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 35.54),
            ],
            payslip_date_from=contract.date_end.replace(day=1),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )

    # LSL ATO > 93
    def test_23_termination_unused_leaves(self):
        # TODO: Check rule parameter
        employee, contract = self.get_unused_leaves_employee('1958-1-1', '2005-1-1', '2015-1-14')
        contract.schedule_pay = "weekly"
        contract.wage = 1000
        self.env.ref("l10n_au_hr_payroll.rule_parameter_withholding_schedule_1_2023").date_from = fields.Date.from_string("2014-1-1")
        self.env.ref("l10n_au_hr_payroll.rule_parameter_study_loan_coefficients_2023").date_from = fields.Date.from_string("2014-1-1")
        self.env.ref("l10n_au_hr_payroll.rule_parameter_super_2023").date_from = fields.Date.from_string("2014-1-1")

        self.env['hr.rule.parameter.value'].create({
            "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_leave_withholding").id,
            "date_from": fields.Date.from_string("2014-1-1"),
            "parameter_value": 32,
        })
        self.env['hr.rule.parameter.value'].create({
            "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_leaves_low_threshold").id,
            "date_from": fields.Date.from_string("2014-1-1"),
            "parameter_value": 300,
        })
        self.env['hr.rule.parameter.value'].create({
            "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_leaves_low_withhold").id,
            "date_from": fields.Date.from_string("2014-1-1"),
            "parameter_value": 32,
        })

        self.create_leaves(
            employee,
            contract,
            {
                "long_service": {
                    "pre_1993": 40,
                }
            },
        )

        self.assertFalse(employee.is_non_resident)
        self.assertEqual(employee.l10n_au_tfn_declaration, 'provided')

        expected_gross = 8000
        expected_withhold = -2560
        normal_withholding = -58
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 3.0, (7.6 * 3), 600.1),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 600.1),
                ("OTE", 600.1),
                ("GROSS", 600.1),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", 0),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold),
                ("NET", 600.1 + expected_gross + (normal_withholding + expected_withhold)),
                ("SUPER", 66.01),
            ],
            payslip_date_from=fields.Date.from_string("2015-1-12"),
            payslip_date_to=contract.date_end,
            termination_type="genuine"
        )

    # https://www.ato.gov.au/forms-and-instructions/employment-termination-payments-withholding-from-unused-leave-payments/unused-long-service-leave/examples
    # Matt's Retirement
    def test_24_termination_unused_leaves(self):
        # TODO: Check rule parameter
        employee, contract = self.get_unused_leaves_employee('1958-1-1', '1977-1-1', '2014-12-31')
        contract.schedule_pay = "weekly"
        contract.wage = 1200
        # Tax tables 2014
        # https://softwaredevelopers.ato.gov.au/sites/default/files/resource-attachments/NAT_1004.pdf
        # Payg
        self.env["hr.rule.parameter.value"].create(
            {
                "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_withholding_schedule_1").id,
                "date_from": fields.datetime(2014, 7, 1).date(),
                "parameter_value": {
                    "tax-free": [
                        (355, 0.0, 0.0),
                        (395, 0.1900, 67.4635),
                        (493, 0.2900, 106.9673),
                        (711, 0.2100, 67.4642),
                        (1282, 0.3477, 165.4431),
                        (1538, 0.3450, 161.9815),
                        (3461, 0.3900, 231.2123),
                        ("inf", 0.4900, 577.3662),
                    ],
                    "medicare": {
                        "tax-free": {
                            "WEST": 548,
                            "MLFT": 38474,
                            "WFTD": 52,
                            "ADDC": 3533,
                            "SOPM": 0.1000,
                            "SOPD": 0.0800,
                            "WLA": 438.4800,
                            "ML": 0.0200,
                        },
                        "half-exemption": {
                            "WEST": 924,
                            "MLFT": 38474,
                            "WFTD": 52,
                            "ADDC": 3533,
                            "SOPM": 0.0500,
                            "SOPD": 0.0400,
                            "WLA": 739.8800,
                            "ML": 0.010,
                        },
                    },
                },
            }
        )

        self.env.ref("l10n_au_hr_payroll.rule_parameter_study_loan_coefficients_2023").date_from = fields.Date.from_string("2014-1-1")
        self.env["hr.rule.parameter.value"].create(
            {
                "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_super").id,
                "date_from": fields.datetime(2014, 7, 1).date(),
                "parameter_value": 9.50,
            }
        )
        self.env['hr.rule.parameter.value'].create({
            "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_leave_withholding").id,
            "date_from": fields.Date.from_string("2014-1-1"),
            "parameter_value": 32,
        })
        self.env['hr.rule.parameter.value'].create({
            "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_leaves_low_threshold").id,
            "date_from": fields.Date.from_string("2014-1-1"),
            "parameter_value": 300,
        })
        self.env['hr.rule.parameter.value'].create({
            "rule_parameter_id": self.env.ref("l10n_au_hr_payroll.rule_parameter_leaves_low_withhold").id,
            "date_from": fields.Date.from_string("2014-1-1"),
            "parameter_value": 32,
        })

        self.create_leaves(
            employee,
            contract,
            {
                "long_service": {
                    "pre_1993": 106,
                    "post_1993": 151,
                    "pre_1978": 13,
                }
            },
        )

        self.assertFalse(employee.is_non_resident)
        self.assertEqual(employee.l10n_au_tfn_declaration, 'provided')
        self.assertEqual(employee.l10n_au_tax_free_threshold, True)

        expected_gross = 80000  # manual amount
        expected_withhold = -26794
        normal_withholding = -252

        payslip = self.env["hr.payslip"].create({
            "name": "payslip",
            "employee_id": employee.id,
            "contract_id": contract.id,
            "struct_id": self.default_payroll_structure.id,
            "date_from": fields.Date.from_string("2014-12-25"),
            "date_to": contract.date_end,
            "l10n_au_termination_type": "normal",
        })
        payslip.input_line_ids.filtered(lambda x: x.code == 'LSL').amount = expected_gross
        payslip.compute_sheet()

        self._test_payslip(
            employee,
            contract,
            payslip=payslip,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 5, (7.6 * 5), 1200),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 1200),
                ("OTE", 1200),
                ("GROSS", 1200),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", -24),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold - 24),
                ("NET", 1200 + expected_gross + (normal_withholding + expected_withhold - 24)),
                ("SUPER", 114),
            ],
        )
        payslip.action_payslip_draft()
        # Recompute the gross
        payslip.action_refresh_from_work_entries()

        expected_gross = 64800.0  # Recomputed Amount
        expected_withhold = -21557.0
        normal_withholding = -252

        self._test_payslip(
            employee,
            contract,
            payslip=payslip,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 5, (7.6 * 5), 1200),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 1200),
                ("OTE", 1200),
                ("GROSS", 1200),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", -24),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold - 24),
                ("NET", 1200 + expected_gross + (normal_withholding + expected_withhold - 24)),
                ("SUPER", 114),
            ],
        )

    # Causal Employee + Casual Loading
    def test_25_termination_unused_leaves(self):
        employee, contract = self.get_unused_leaves_employee('1976-1-1', '2010-1-1', '2024-3-15')
        contract.schedule_pay = 'weekly'
        contract.wage_type = 'hourly'
        contract.hourly_wage = 40
        contract.l10n_au_casual_loading = 0.25

        self.create_leaves(
            employee,
            contract,
            leaves={
                "long_service": {
                    "post_1993": 40,
                }
            },
        )

        # Days * Hours/day * Hourly wage * casual loading
        expected_gross = 40 * 7.6 * 40 * 1.25
        expected_withhold = -5252
        normal_withholding = -473

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types["WORK100"].id, 5, 38, 1900),
            ],
            expected_lines=[
                # (code, total)
                ("BASIC", 1900),
                ("OTE", 1900),
                ("GROSS", 1900),
                ("ETP.LEAVE.GROSS", expected_gross),
                ("WITHHOLD", normal_withholding),
                ("WITHHOLD.STUDY", -114),
                ("MEDICARE", 0),
                ("ETP.LEAVE.WITHHOLD", expected_withhold),
                ("WITHHOLD.TOTAL", normal_withholding + expected_withhold - 114),
                ("NET", 1900 + expected_gross + (normal_withholding + expected_withhold - 114)),
                ("SUPER", 209),
            ],
            payslip_date_from=fields.Date.from_string('2024-3-11'),
            payslip_date_to=contract.date_end,
            termination_type="normal"
        )
