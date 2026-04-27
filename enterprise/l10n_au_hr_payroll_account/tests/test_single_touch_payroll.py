# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from lxml import etree
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from contextlib import closing
from freezegun import freeze_time

from odoo import fields, Command
from odoo.tests import tagged, Form
from odoo.tools import file_path
from odoo.exceptions import ValidationError, MissingError
from .common import L10nPayrollAccountCommon
from odoo.addons.l10n_au_hr_payroll.tests.test_unused_leaves import TestPayrollUnusedLeaves


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestSingleTouchPayroll(L10nPayrollAccountCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref('hr.group_hr_manager')
        cls.env['l10n_au.stp'].search([]).unlink()
        cls.env['ir.sequence'].create({
            'name': 'STP Sequence',
            'code': 'stp.transaction',
            'prefix': 'PAYEVENT0004',
            'padding': 10,
            'number_next': 1,
        })
        cls.company.l10n_au_bms_id = "ODOO_TEST_BMS_ID"
        cls.company.write({
                "vat": "83914571673",
                "email": "au_company@odoo.com",
                "phone": "123456789",
                "zip": "2000",
                'l10n_au_branch_code': '100'
        })
        cls.long_service = cls.env['hr.leave.type'].create({
            'name': 'Long Service Leave',
            'company_id': cls.company.id,
            'l10n_au_leave_type': 'long_service',
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_long_service_leave').id,
        })
        cls.annual = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave',
            'company_id': cls.company.id,
            'l10n_au_leave_type': 'annual',
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_paid_time_off').id,
        })

    allocate_leaves = TestPayrollUnusedLeaves.create_leaves

    # ==================== HELPERS ====================

    def create_leave(self, date_from=None, amount=None, name="", work_entry_type=None, employee_id=False):
        holiday_leave_types = self.env['hr.leave.type'].create([{
            'name': 'Paid Time Off',
            'requires_allocation': 'no',
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
            'work_entry_type_id': work_entry_type.id,
        }])
        duration = amount / self.contract_2.hourly_wage
        return self.env['hr.leave'].create({
            'name': name or 'Holiday!!!',
            'employee_id': employee_id.id,
            'holiday_status_id': holiday_leave_types.id,
            'request_date_from': date_from,
            'request_date_to': date_from + relativedelta(hours=duration),
            'request_unit_hours': duration,
            # 'number_of_hours': duration,
        }).with_context(leave_fast_create=True).action_validate()

    def _prepare_payslip_run(self, employee_ids, extra_input_xml_ids=None, start_date=None, end_date=None):
        input_xml_ids = extra_input_xml_ids
        if not input_xml_ids:
            input_xml_ids = {
                "l10n_au_hr_payroll.input_laundry_1": 100,
                "l10n_au_hr_payroll.input_laundry_2": 100,
                "l10n_au_hr_payroll.input_gross_director_fee": 100,
                "l10n_au_hr_payroll.input_bonus_commissions_overtime_prior": 100,
                "l10n_au_hr_payroll.input_fringe_benefits_amount": 2000,
            }

        payslip_run = self.env["hr.payslip.run"].create(
            {
                "date_start": start_date or "2024-01-01",
                "date_end": end_date or "2024-01-31",
                "name": "January Batch",
                "company_id": self.company.id,
            }
        )

        payslip_employee = (
            self.env["hr.payslip.employees"]
            .create(
                {
                    "employee_ids": [
                        Command.set(employee_ids.ids)
                    ]
                }
            )
        )
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.slip_ids.write({"input_line_ids": [(0, 0, {
            "input_type_id": self.env.ref(input_id).id,
            "amount": amount,
            }) for input_id, amount in input_xml_ids.items()
        ]})
        payslip_run.slip_ids.compute_sheet()
        payslip_run.action_validate()
        return payslip_run

    def _submit_stp(self, stp):
        self.assertTrue(stp, "The STP record should have been created when the payslip was created")
        self.assertEqual(stp.state, "draft", "The STP record should be in draft state")
        stp.submit_date = stp.submit_date or date.today()
        # TODO: Check the data being generated in the XML file
        action = self.env['l10n_au.stp.submit'].create(
            {'l10n_au_stp_id': stp.id}
        )
        with self.assertRaises(ValidationError):
            action.action_submit()
        action.stp_terms = True
        action.action_submit()

        self.assertTrue(stp.xml_file, "The XML file should have been generated")
        self.assertEqual(stp.state, "sent", "The STP record should be in sent state")

    def create_ytd_opening_balances(self, employee, values: list):
        """
        Args:
            employee (hr.employee)
            values (list): List with (code, amount) tuples
        """
        ytd_wizard = self.env["l10n_au.previous.payroll.transfer"].create(
            {
                "previous_bms_id": "12321321",
                "l10n_au_previous_payroll_transfer_employee_ids": [
                    Command.create({"employee_id": employee.id, "previous_payroll_id": "test_123213"})
                ]
            })
        ytd_wizard.action_transfer()
        for code, value in values:
            rule = self.env["l10n_au.payslip.ytd"].search([("employee_id", "=", employee.id), ("rule_id.code", "=", code)])
            rule.ensure_one()
            if isinstance(value, (int, float)):
                rule.start_value = value
            else:
                for key, val in value.items():
                    if input_line := rule.l10n_au_payslip_ytd_input_ids.filtered(lambda x: x.name == key):
                        input_line.ytd_amount = val
                    else:
                        raise MissingError(f"Input line {key} not found in YTD rule {rule.name}")

    def create_payslips(self, employee, num_slips, start_date):
        slip_vals = []
        for i in range(num_slips):
            slip_month = start_date.month + i if (start_date.month + i) <= 12 else 1
            slip_vals.append({
                "employee_id": employee.id,
                "contract_id": employee.contract_id.id,
                "date_from": start_date.replace(month=slip_month),
                "date_to": start_date.replace(month=slip_month) + relativedelta(day=31),
                "name": f"January Payslip {i + 1}",
                "struct_id": self.default_payroll_structure.id,
            })
        slips = self.env["hr.payslip"].create(slip_vals)
        slips.compute_sheet()
        slips.action_payslip_done()
        return slips[-1]

    # Assert dict vals
    def assertStpTupleEqual(self, stp_tuple, expected_values):
        error_msg = ""
        for key, value in expected_values.items():
            try:
                self.assertEqual(stp_tuple[key], value)
            except AssertionError:
                error_msg += f"{key}: {stp_tuple[key]} != {value}\n"

        if error_msg:
            self.fail("The STP tuple value(s) do not match the expected values\n" + error_msg)

    def assertAlmostEqualRecordValues(self, records, expected_values: list, delta=0.5):
        error_msg = []
        if len(records) != len(expected_values):
            self.fail(f"The number of records do not match the expected values {len(records)} != {len(expected_values)}\n"
                      f"Actual: {records.mapped('code')}\n"
                      f"Expected: {[x['code'] for x in expected_values]}"
                      )
        for record, expected in zip(records.sorted(key="code"), sorted(expected_values, key=lambda x: x["code"])):
            try:
                for key, value in expected.items():
                    if isinstance(value, (int, float)):
                        self.assertAlmostEqual(record[key], value, delta=delta)
            except AssertionError:
                error_msg.append(f"Expected: {expected}\n\tActual: {record.read(list(expected.keys()))}\n")

        if error_msg:
            self.fail("The record values do not match the expected values\n\t" + "\n\t".join(error_msg))

    # ==================== TESTS ====================

    def test_stp(self):
        self.employee_1.l10n_au_child_support_garnishee_amount = 0.15
        self.employee_1.l10n_au_child_support_deduction = 120
        self.contract_1.l10n_au_salary_sacrifice_superannuation = 100
        self.env.ref("l10n_au_hr_payroll.input_bonus_commissions").l10n_au_payroll_code = "Gross"
        batch = self._prepare_payslip_run(
            self.employee_1 + self.employee_2,
            {
                "l10n_au_hr_payroll.input_child_support_garnishee_lump_sum": 1000,
                "l10n_au_hr_payroll.input_bonus_commissions": 7000,
            },
        )

        self.assertTrue(
            all(state == "ready" for state in batch.slip_ids.mapped("l10n_au_stp_status")),
            "All payslips should be ready to be sent to STP"
        )

        stp = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id)])
        stp.submit_date = date.today()
        data = stp._get_complex_rendering_data()
        self.assertEqual(data[self.employee_1.id]["Remuneration"][0]["GrossA"], 12000)
        self.assertEqual(data[self.employee_2.id]["Remuneration"][0]["GrossA"], 14000)
        self.assertListEqual(
            data[self.employee_1.id]["Deduction"],
            [
                {"RemunerationTypeC": "G", "RemunerationA": 2124.7},
                {"RemunerationTypeC": "D", "RemunerationA": 120.0},
            ],
        )
        self._submit_stp(stp)

    def test_stp_bonuses(self):
        self.employee_1.l10n_au_child_support_garnishee_amount = 0.15
        self.employee_1.l10n_au_child_support_deduction = 120
        self.contract_1.l10n_au_salary_sacrifice_superannuation = 100
        self.env.ref("l10n_au_hr_payroll.input_bonus_commissions").l10n_au_payroll_code = "Gross"
        batch = self._prepare_payslip_run(
            self.employee_1 + self.employee_2,
            {
                "l10n_au_hr_payroll.input_child_support_garnishee_lump_sum": 1000,
                "l10n_au_hr_payroll.input_bonus_commissions": 7000,
            },
        )

        self.assertTrue(
            all(state == "ready" for state in batch.slip_ids.mapped("l10n_au_stp_status")),
            "All payslips should be ready to be sent to STP"
        )

        stp = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id)])
        stp.submit_date = date.today()
        data = stp._get_complex_rendering_data()
        self.assertEqual(data[self.employee_1.id]["Remuneration"][0]["GrossA"], 12000)
        self.assertEqual(data[self.employee_2.id]["Remuneration"][0]["GrossA"], 14000)
        self.assertListEqual(
            data[self.employee_1.id]["Deduction"],
            [
                {"RemunerationTypeC": "G", "RemunerationA": 2124.7},
                {"RemunerationTypeC": "D", "RemunerationA": 120.0},
            ],
        )
        self._submit_stp(stp)

    @freeze_time("2024-03-31")
    def test_update_event(self):
        batch = self._prepare_payslip_run(employee_ids=self.employee_1 + self.employee_2)
        stp = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id)])
        self._submit_stp(stp)
        self.create_payslips(self.employee_2, 2, date(2024, 2, 1))
        # Missed the reporting for February and March
        stp_update = self.env["l10n_au.stp"].create(
            {
                "company_id": self.company.id,
                "payevent_type": "update",
                "l10n_au_stp_emp": [
                    (0, 0, {"employee_id": self.employee_1.id}),
                    (0, 0, {"employee_id": self.employee_2.id}),
                ],
            }
        )
        self.assertRecordValues(
            stp_update.l10n_au_stp_emp,
            [
                {
                    "employee_id": self.employee_1.id,
                    "ytd_gross": 5000.0,
                    "ytd_tax": 1036.0,
                    "ytd_super": 572.0,
                    "ytd_rfba": 2000.0,
                    "ytd_rfbae": 0.0,
                },
                {
                    "employee_id": self.employee_2.id,
                    "ytd_gross": 21000.0,
                    "ytd_tax": 4979.0,
                    "ytd_super": 2332.0,
                    "ytd_rfba": 2000.0,
                    "ytd_rfbae": 0.0,
                },
            ],
        )
        self._submit_stp(stp_update)

    def test_out_of_cycle_termination(self):
        self.contract_1.write({"l10n_au_salary_sacrifice_superannuation": 100})
        self.allocate_leaves(
            self.employee_1,
            self.contract_1,
            leaves={
                "annual": {
                    "pre_1993": 20,
                    "post_1993": 10.42,
                }
            },
        )
        payslip = self.env["hr.payslip"].create({
                "name": "payslip",
                "employee_id": self.employee_1.id,
                "contract_id": self.contract_1.id,
                "date_from": "2024-05-01",
                "date_to": "2024-05-31",
                "input_line_ids": [(0, 0, {
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_golden_handshake').id,
                    'amount': 250,
                })],
                "l10n_au_termination_type": 'normal',
            })

        payslip.compute_sheet()
        payslip.action_payslip_done()
        stp = self.env["l10n_au.stp"].search([("payslip_ids", "in", payslip.id)])
        stp.submit_date = date.today()
        rendering_data = stp._get_rendering_data()
        termination_tuple = rendering_data[1][0]["Remuneration"][0]["EmploymentTerminationPaymentCollection"]
        self.assertDictEqual(
            termination_tuple[0],
            {
                "IncomePayAsYouGoWithholdingA": 80.0,
                "IncomeTaxPayAsYouGoWithholdingTypeC": "O",
                "IncomeD": fields.Date.from_string("2024-05-31"),
                "IncomeTaxableA": 250.0,
                "IncomeTaxFreeA": 0,
            },
        )
        super_tuple = rendering_data[1][0]["SuperannuationContributionCollection"]
        self.assertListEqual(
            super_tuple,
            [
                {"EntitlementTypeC": "O", "EmployerContributionsYearToDateA": 5000.0},  # OTE
                {"EntitlementTypeC": "L", "EmployerContributionsYearToDateA": 550.0},  # NON RESC
                {"EntitlementTypeC": "R", "EmployerContributionsYearToDateA": 100.0},  # RESC
            ]
        )
        self.assertEqual(rendering_data[1][0]["EmploymentEndD"], fields.Date.from_string("2024-05-31"))
        self._submit_stp(stp)

    def test_out_of_cycle_termination_genuine(self):
        self.contract_1.write({
            "wage": 2000,
            "schedule_pay": "weekly",
            "date_start": "2011-9-01",
            "date_end": "2024-11-01",
        })
        self.allocate_leaves(
            self.employee_1,
            self.contract_1,
            leaves={
                "annual": {
                    "post_1993": 12,
                }
            },
        )
        payslip = self.env["hr.payslip"].create({
                "name": "payslip",
                "employee_id": self.employee_1.id,
                "contract_id": self.contract_1.id,
                "date_from": "2024-10-28",
                "date_to": "2024-11-01",
                "input_line_ids": [(0, 0, {
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_genuine_redundancy').id,
                    'amount': 110000,
                })],
                "l10n_au_termination_type": 'genuine',
            })

        payslip.compute_sheet()
        payslip.action_payslip_done()
        stp = self.env["l10n_au.stp"].search([("payslip_ids", "in", payslip.id)])
        stp.submit_date = date.today()
        rendering_data = stp._get_rendering_data()
        termination_tuple = rendering_data[1][0]["Remuneration"][0]["EmploymentTerminationPaymentCollection"]
        self.assertDictEqual(
            termination_tuple[0],
            {
                "IncomePayAsYouGoWithholdingA": 5134.0,
                "IncomeTaxPayAsYouGoWithholdingTypeC": "R",
                "IncomeD": fields.Date.from_string("2024-11-30"),
                "IncomeTaxableA": 16044.0,
                "IncomeTaxFreeA": 93956.0,
            },
        )
        self.assertEqual(rendering_data[1][0]["EmploymentEndD"], fields.Date.from_string("2024-11-1"))
        lumpsum_tuple = rendering_data[1][0]["Remuneration"][0]["LumpSumCollection"]
        # ETP Tax free under tax free cap (Genuine) are reported as Lump Sum D
        self.assertListEqual(
            lumpsum_tuple,
            [{"TypeC": "D", "PaymentsA": 93956.0}, {"TypeC": "R", "PaymentsA": 4800.0}],
        )
        self._submit_stp(stp)

    @freeze_time("2024-10-31")
    def test_payslip_ytd_with_opening_balances(self):
        self.employee_2.write({
            "l10n_au_child_support_garnishee_amount": 0.0,
            "l10n_au_child_support_deduction": 60.2,
        })
        self.contract_2.write({
            "wage": 5000,
            "l10n_au_workplace_giving": 120.6,
            "l10n_au_workplace_giving_employer": 120.4,
            "l10n_au_extra_negotiated_super": 0.0161,
            "l10n_au_salary_sacrifice_superannuation": 80.2,
            "l10n_au_salary_sacrifice_other": 120.2
        })

        self.create_ytd_opening_balances(
            self.employee_2,
            [
                ("BASIC", {"Attendance": 25000,
                           "Overtime Hours": 140,
                           "Other Paid Leave": 130,
                           "Paid Parental Leave": 120,
                           "Workers Compensation": 110,
                           "Ancillary and Defence Leave": 100
                           }),
                ("EXTRA", {"Cashing out leaves (annual, long service, personal or RDO)": 1001,
                           "Bonus/Commissions (For Payslip Period)": 1002,
                           "Director's Fees": 1003,
                           "Cashing out time off in lieu (TOIL)": 1004,
                           "Bonus/Commissions In Relation to Overtime (For Payslip Period)": 1005
                           }),
                ("SALARY.SACRIFICE.OTHER", {"Salary Sacrifice: Other Benefits": -601,
                                            "Salary Sacrificed Workplace Giving": -602}),
                ("WORKPLACE.GIVING", -603),
                ("ALW", {"Cents per Kilometer: Mileage for business purposes in excess of ATO measure":	10,
                         "Cents per Kilometer: Mileage for other vehicles":	11,
                         "Cents per Kilometer: Mileage for private purposes assessed not to be fully spent":	12,
                         "Award Transport: Transport for business purposes not traced to historical award":	13,
                         "Award Transport: Transport for private purposes":	14,
                         "Laundry: Allowance for approved uniforms above ATO measure":	15,
                         "Laundry: Allowance for the exception for conventional clothing":	16,
                         "Laundry: Allowance for non-approved uniforms or private purposes":	17,
                         "Call Back: Called back to work overtime after leaving premises":	18,
                         "On Call: Pre-sacrificed amount for payments outside ordinary hours":	19,
                         "On Call: Pre-sacrificed amount for payments within ordinary hours":	20,
                         "Domestic Travel Allowance: For meals, accommodation and incidentals when not sleeping away for business purposes":	21,
                         "Domestic Travel Allowance: For meals, accommodation and incidentals when sleeping away for business purposes above ATO measures":	22,
                         "Domestic Travel Allowance: For meals, accommodation and incidentals when sleeping away for private purposes":	23,
                         "Overseas Travel Allowance: For meals and incidentals for business purposes above ATO measures":	24,
                         "Overseas Travel Allowance: For meals and incidentals for private purposes":	25,
                         "Overseas Accommodation Allowance: For business purposes":	26,
                         "Work-Related Non-Expense: Allowance to compensate for specific work, activities, disabilities, skills or qualifications":	27,
                         "Qualifications Expense: To cover the cost of qualifications, insurance, licenses and certifications":	28,
                         "Uniform Allowance: For purchase of approved uniforms":	29,
                         "Car: Fixed rates paid to cover transport costs not covered by award transport":	30,
                         "Home Office: Allowance to cover the cost of equipment or connection":	31,
                         "Fares: Allowance to cover the cost of fares":	32,
                         "Other Deductible: Deductible allowances not defined separately elsewhere":	33,
                         "Overtime Meal Allowance: Overtime Over ATO Measures":	34
                         }),
                ("RTW", 700),
                ("ALW.TAXFREE", {"Cents per Kilometer: Mileage for business purposes up to ATO measure": 51,
                                 "Award Transport: Transport for business purposes traced to historical award": 52,
                                 "Laundry: Allowance for approved uniforms up to ATO measure": 53,
                                 "Domestic Travel Allowance: For meals, accommodation and incidentals when sleeping away for business purposes up to ATO measures": 54,
                                 "Overseas Travel Allowance: For meals and incidentals for business purposes up to ATO measures": 55,
                                 "Overtime Meal Allowance: Overtime Up to ATO Measures": 56
                                 }),
                ("BACKPAY", {"Leave Loading Lump Sum": 201,
                             "Lump Sum E": 202,
                             "Bonus/Commissions (Prior Period)": 203
                             }),
                ("WITHHOLD.TOTAL", -5753.8),
                ("CHILD.SUPPORT", {"Child Support Deduction": -301,
                                   "Child Support Garnishee: Periodic": -302,
                                   # Should manually be added to withhold
                                   "Child Support Garnishee: Lump Sum": -303}),
                ("SUPER.CONTRIBUTION", {"Salary Sacrifice: Superannuation": 401,
                                        "Extra Negotiated Super (RESC)": 402}),
                ("SUPER", 3355.55),
                ("RFBA", {"Fringe Benefits Amount": 501,
                          "Fringe Benefits Amount - Exempt": 502})
            ]
        )

        def create_work_entry(work_entry_type, start, duration, state="draft"):
            work_entry = self.env["hr.work.entry"].create([{
                "name": f"Work Entry {self.env.ref(work_entry_type).name}",
                "work_entry_type_id": self.env.ref(work_entry_type).id,
                "employee_id": self.employee_2.id,
                "contract_id": self.contract_2.id,
                "date_start": start,
                "date_stop": start + relativedelta(hours=duration),
                "duration": duration,
                "state": state,
            }])
            work_entry.action_validate()

        # Work Entries, For simplicty, Leaves handled as work entries
        create_work_entry("hr_work_entry.overtime_work_entry_type", datetime(2024, 10, 1, 9), 3)
        create_work_entry("l10n_au_hr_payroll.l10n_au_work_entry_type_other", datetime(2024, 10, 3, 9), 4, "validated")
        create_work_entry("l10n_au_hr_payroll.l10n_au_work_entry_type_parental", datetime(2024, 10, 4, 9), 3, "validated")
        create_work_entry("l10n_au_hr_payroll.l10n_au_work_entry_type_compensation", datetime(2024, 10, 5, 9), 4)
        create_work_entry("l10n_au_hr_payroll.l10n_au_work_entry_type_defence", datetime(2024, 10, 6, 9), 3, "validated")

        input_lines = [
            ('l10n_au_hr_payroll.input_leaves_cashed_out_in_service', 200.2),
            ('l10n_au_hr_payroll.input_bonus_commissions', 200.4),
            ('l10n_au_hr_payroll.input_gross_director_fee', 200.6),
            ('l10n_au_hr_payroll.input_toil_cashed_out_in_service', 200.8),
            ('l10n_au_hr_payroll.input_bonus_commissions_overtime_prior', 201),
            # Taxable Allowances
            ('l10n_au_hr_payroll.input_cents_per_kilometer_2', 2),
            ('l10n_au_hr_payroll.input_cents_per_kilometer_3', 2.2),
            ('l10n_au_hr_payroll.input_cents_per_kilometer_5', 2.4),
            ('l10n_au_hr_payroll.input_award_transport_2', 2.6),
            ('l10n_au_hr_payroll.input_award_transport_3', 2.8),
            ('l10n_au_hr_payroll.input_laundry_2', 3),
            ('l10n_au_hr_payroll.input_laundry_3', 3.2),
            ('l10n_au_hr_payroll.input_laundry_4', 3.4),
            ('l10n_au_hr_payroll.input_call_back', 3.6),
            ('l10n_au_hr_payroll.input_on_call_1', 3.8),
            ('l10n_au_hr_payroll.input_on_call_2', 4),
            ('l10n_au_hr_payroll.input_domestic_travel_allowance_2', 4.2),
            ('l10n_au_hr_payroll.input_domestic_travel_allowance_3', 4.4),
            ('l10n_au_hr_payroll.input_domestic_travel_allowance_4', 4.6),
            ('l10n_au_hr_payroll.input_overseas_travel_allowance_2', 4.8),
            ('l10n_au_hr_payroll.input_overseas_travel_allowance_3', 5),
            ('l10n_au_hr_payroll.input_overseas_accommodation_allowance_1', 5.2),
            ('l10n_au_hr_payroll.input_work_related_non_expense', 5.4),
            ('l10n_au_hr_payroll.input_qualifications_expense', 5.6),
            ('l10n_au_hr_payroll.input_uniform_allowance', 5.8),
            ('l10n_au_hr_payroll.input_car', 6),
            ('l10n_au_hr_payroll.input_home_office', 6.2),
            ('l10n_au_hr_payroll.input_fares', 6.4),
            ('l10n_au_hr_payroll.input_other_deductible', 6.6),
            ('l10n_au_hr_payroll.input_overtime_meal_allowance_2', 6.8),
            # Tax Free Allowances
            ('l10n_au_hr_payroll.input_cents_per_kilometer_1', 10.2),
            ('l10n_au_hr_payroll.input_award_transport_1', 10.4),
            ('l10n_au_hr_payroll.input_laundry_1', 10.6),
            ('l10n_au_hr_payroll.input_domestic_travel_allowance_1', 10.8),
            ('l10n_au_hr_payroll.input_overseas_travel_allowance_1', 11),
            ('l10n_au_hr_payroll.input_overtime_meal_allowance_1', 11.2),
            # RTW
            ('l10n_au_hr_payroll.input_b2work', 140),
            # Backpay
            ('l10n_au_hr_payroll.input_leave_loading_lump', 40.2),
            ('l10n_au_hr_payroll.input_bonus_commissions_prior', 40.6),
            # Child Support
            ('l10n_au_hr_payroll.input_child_support_garnishee_periodic', 60.5),
            ('l10n_au_hr_payroll.input_child_support_garnishee_lump_sum', 60.6),
            # Fringe Benefits
            ('l10n_au_hr_payroll.input_fringe_benefits_amount', 100.2),
            ('l10n_au_hr_payroll.input_fringe_benefits_exempt_amount', 100.4)
        ]
        slip = self.env['hr.payslip'].create({
                "employee_id": self.employee_2.id,
                "contract_id": self.employee_2.contract_id.id,
                "date_from": datetime(2024, 10, 1),
                "date_to":  datetime(2024, 10, 31),
                "name": "OCT Payslip Test",
                "struct_id": self.default_payroll_structure.id,
                "input_line_ids": [(0, 0, {
                    'input_type_id': self.env.ref(input_id).id,
                    'amount': amount,
                }) for input_id, amount in input_lines]
            })
        # Add a lump sum E with date
        self.env['hr.payslip.input'].create({
            'payslip_id': slip.id,
            'input_type_id': self.env.ref('l10n_au_hr_payroll.l10n_au_lumpsum_e').id,
            'amount': 40.4,
            'name': '2023'
        })
        slip.action_refresh_from_work_entries()

        self.assertAlmostEqualRecordValues(
            slip.worked_days_line_ids,
            [
                {'code': 'WORK100', 'amount': 4629.24, 'ytd': 25000 + 4629.24},
                {'code': 'OVERTIME', 'amount': 79.45, 'ytd': 140 + 79.45},
                {'code': 'AU.O', 'amount': 105.93, 'ytd': 130 + 105.93},
                {'code': 'AU.P', 'amount': 79.45, 'ytd': 120 + 79.45},
                {'code': 'AU.W', 'amount': 105.93, 'ytd': 110 + 105.93},
                {'code': 'AU.A', 'amount': 79.45, 'ytd': 100 + 79.45},
            ]
        )
        self.assertAlmostEqualRecordValues(
            slip.line_ids,
            [
                {'code': 'BASIC', 'amount': 5079.45, 'ytd': 30679.45},
                {'code': 'OTE', 'amount': 5917.2, 'ytd': 35963.2},
                {'code': 'EXTRA', 'amount': 1003, 'ytd': 6018},
                {'code': 'SALARY.SACRIFICE.TOTAL', 'amount': -320.8, 'ytd': -1924.8},
                {'code': 'ALW', 'amount': 110.0, 'ytd': 660.0},
                {'code': 'ALW.TAXFREE', 'amount': 64.2, 'ytd': 385.2},
                {'code': 'RTW', 'amount': 140, 'ytd': 840},
                {'code': 'BACKPAY', 'amount': 121.2, 'ytd': 727.2},
                {'code': 'SALARY.SACRIFICE.OTHER', 'amount': -240.6, 'ytd': -1443.6},
                {'code': 'WORKPLACE.GIVING', 'amount': -120.6, 'ytd': -723.6},
                {'code': 'GROSS', 'amount': 6012.25, 'ytd': 36276.25},
                {'code': 'WITHHOLD', 'amount': -1075.0, 'ytd': -1075.0},
                {'code': 'BACKPAY.WITHHOLD', 'amount': -56.96, 'ytd': -56.96},
                {'code': 'RTW.WITHHOLD', 'amount': 140.0, 'ytd': -44.8},
                {'code': 'MEDICARE', 'amount': 0.0, 'ytd': 0.0},
                {'code': 'WITHHOLD.TOTAL', 'amount': -1176.76, 'ytd': -6930.56},
                {'code': 'CHILD.SUPPORT.GARNISHEE', 'amount': -121.1, 'ytd': -726.1},
                {'code': 'CHILD.SUPPORT', 'amount': -181.3, 'ytd': -1087.3},
                {'code': 'NET', 'amount': 4718.39, 'ytd': 4718.39},
                {'code': 'SUPER.CONTRIBUTION', 'amount': 175.47, 'ytd': 978.47},
                {'code': 'SUPER', 'amount': 680.48, 'ytd': 4036.03},
                {'code': 'RFBA', 'amount': 200.6, 'ytd': 1203.6},
            ]
        )

    def test_ytd_orm_cache(self):
        with closing(self.env.registry.cursor()) as test_cr:
            self.env = self.env(context=dict(self.env.context, cr=test_cr))
            # payslips = self.create_payslips(self.employee_2, 2, date(2024, 7, 1))
            slip = self.env["hr.payslip"].create({
                "employee_id": self.employee_2.id,
                "contract_id": self.employee_2.contract_id.id,
                "date_from": date(2024, 7, 1),
                # "date_to": start_date.replace(day=31, month=slip_month),
                "name": "Test Payslip",
                "struct_id": self.default_payroll_structure.id,
                "input_line_ids": [(0, 0, {
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_laundry_1').id,
                    'amount': 100,
                    }), (0, 0, {
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_laundry_2').id,
                    'amount': 100,
                    }), (0, 0, {
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_gross_director_fee').id,
                    'amount': 100,
                    }), (0, 0, {
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_bonus_commissions_overtime_prior').id,
                    'amount': 100,
                })]
            })
            slip.compute_sheet()
            slip.action_payslip_done()
            result = slip._l10n_au_get_year_to_date_totals(l10n_au_include_current_slip=True)
            slip._l10n_au_get_ytd_inputs(l10n_au_include_current_slip=True)

        with closing(self.env.registry.cursor()) as test_cr:
            self.env = self.env(context=dict(self.env.context, cr=test_cr))
            # self.env = self.env(context=dict(self.env.context, cr=test_cr))
            result = slip._l10n_au_get_year_to_date_totals(l10n_au_include_current_slip=True)
            inputs = slip._l10n_au_get_ytd_inputs(l10n_au_include_current_slip=True)
            for key, value in result['worked_days'].items():
                self.assertTrue(key)

            for key, value in inputs.items():
                self.assertTrue(value["payroll_code"])

    def test_stp_zeroing(self):
        self.create_payslips(self.employee_2, 2, date(2024, 7, 1))
        # Changing the company details
        self.company = self.env.company
        self.company.write(
            {
                "l10n_au_bms_id": "6a99448e-20ec-4ca1-9f8a-93524aeb244d",
                "vat": "11 225 459 588",
                "l10n_au_branch_code": "1",
                "name": "Employer A",
                "zip": "3000",
            }
        )
        self.employee_1.write(
            {
                "name": "Employer A contact name",
                "private_email": "EmployerA@Email.address",
                "private_phone": "0400 000000",
            }
        )
        self.employee_2.write(
            {
                "l10n_au_payroll_id": "481",  # Changed
                "l10n_au_tfn": "800000008",  # Changed
            }
        )

        # Submit a zeoring event
        with freeze_time("2024-10-31"):
            stp = self.env["l10n_au.stp"].create(
                {
                    "company_id": self.company.id,
                    "payevent_type": "update",
                    "is_zeroing": True,
                    "l10n_au_stp_emp": [(0, 0, {"employee_id": self.employee_2.id})],
                }
            )

            stp.action_generate_xml()

        # Expected XML
        parsed_expected = etree.parse(file_path("l10n_au_hr_payroll_account/tests/stp_test_zeroing.xml")).getroot()
        expected_payevent_root = parsed_expected.find("{http://www.sbr.gov.au/ato/payevnt}PAYEVNT")
        expected_payeventemp_roots = parsed_expected.findall("{http://www.sbr.gov.au/ato/payevntemp}PAYEVNTEMP")

        # Actual XML
        xml_root = etree.fromstring(b"<data>" + base64.b64decode(stp.xml_file) + b"</data>")
        actual_payevent_root = xml_root.find("{http://www.sbr.gov.au/ato/payevnt}PAYEVNT")
        actual_payeventemp_roots = xml_root.findall("{http://www.sbr.gov.au/ato/payevntemp}PAYEVNTEMP")

        self.assertXmlTreeEqual(actual_payevent_root, expected_payevent_root)

        for actual_payeventemp_root, expected_payeventemp_root in zip(actual_payeventemp_roots, expected_payeventemp_roots):
            self.assertXmlTreeEqual(actual_payeventemp_root, expected_payeventemp_root)

    def test_full_file_replacement(self):

        def _get_payment_amount(move):
            return sum(move.line_ids.filtered_domain([("partner_id", "!=", False), ("price_total", ">", 0)]).mapped("price_total"))

        # Prepare and submit a payrun
        batch = self._prepare_payslip_run(self.employee_1 + self.employee_2)
        batch.action_validate()
        stp = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id)])
        self._submit_stp(stp)
        # Pay the payslips and validate the batch
        batch.slip_ids.move_id.action_post()
        payments = self._register_payment(batch)
        batch.l10n_au_payment_batch_id.validate_batch()
        self.assertTrue(all(payslip.state == 'paid' for payslip in batch.slip_ids), "All payslips must be marked paid!")
        self.assertTrue(all(p.is_reconciled for p in payments), "All payments should be reconciled!")

        # Make a full file replacement
        payslip_to_update = batch.slip_ids[0]
        original_payment_amount = _get_payment_amount(payslip_to_update.move_id)
        action = stp.action_replace_file()
        wizard = self.env["l10n_au.stp.ffr.wizard"].with_context(action['context']).create({})
        wizard.ffr_payslip_ids.write({"to_reset": True})
        wizard.action_create_ffr()
        self.assertTrue(all(payslip.state == 'verify' for payslip in batch.slip_ids), "The payslips should have been reset!")
        self.assertTrue(all(not p.is_reconciled for p in payments), "All payments should be unreconciled!")
        # Add an extra input to the payslip
        payslip_to_update.write({
            "input_line_ids": [(0, 0, {"input_type_id": self.env.ref("l10n_au_hr_payroll.input_laundry_1").id, "amount": 100})]
        })
        batch.slip_ids.compute_sheet()
        batch.action_validate()
        self.assertEqual(batch.slip_ids.mapped("state"), ["done", "done"], "The payslips should have been done!")
        self.assertEqual(batch.state, "close", "The payslip batch should be done!")
        # Submit the new STP record
        ffr = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id), ("ffr", "=", True)])
        self.assertEqual(ffr.previous_report_id, stp, "The previous report should be the original STP record")
        self._submit_stp(ffr)
        self.assertEqual(ffr.submission_id, stp.submission_id, "The previous report should be the original STP record")
        self.assertNotEqual(ffr.xml_file, stp.xml_file, "The Replacement STP should not be the same as the original STP")

        # Register new payments
        new_payments = self._register_payment(batch)
        new_payment_amount = _get_payment_amount(payslip_to_update.move_id)
        self.assertTrue(all(payslip.state == 'paid' for payslip in batch.slip_ids), "All payslips must be marked paid!")
        self.assertEqual(new_payments.amount, new_payment_amount - original_payment_amount, "The payment amount should account for the difference in payslip amounts!")
        self.assertTrue(all(p.is_reconciled for p in payments | new_payments), "All payments should be reconciled!")

    def test_stp_multiple_income_stream(self):
        self.employee_1.l10n_au_child_support_garnishee_amount = 0.15
        self.employee_1.l10n_au_child_support_deduction = 120
        self.contract_1.l10n_au_salary_sacrifice_superannuation = 100
        self.env.ref("l10n_au_hr_payroll.input_bonus_commissions").l10n_au_payroll_code = "Gross"
        batch = self._prepare_payslip_run(
            self.employee_1 + self.employee_2,
            {
                "l10n_au_hr_payroll.input_child_support_garnishee_lump_sum": 1000,
                "l10n_au_hr_payroll.input_bonus_commissions": 7000,
            },
        )
        stp = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id)])
        stp.submit_date = date.today()
        data = stp._get_complex_rendering_data()
        self.assertEqual(data[self.employee_1.id]["Remuneration"][0]["GrossA"], 12000)
        self.assertEqual(data[self.employee_2.id]["Remuneration"][0]["GrossA"], 14000)
        self._submit_stp(stp)
        self.employee_1.country_id = self.env.ref("base.hk")
        self.employee_1.l10n_au_income_stream_type = "WHM"

        batch_2 = self._prepare_payslip_run(
            self.employee_1 + self.employee_2,
            {
                "l10n_au_hr_payroll.input_laundry_1": 100,
                "l10n_au_hr_payroll.input_laundry_2": 100,
                "l10n_au_hr_payroll.input_bonus_commissions_overtime_prior": 100,
                "l10n_au_hr_payroll.input_fringe_benefits_amount": 2000,
            },
            start_date="2024-02-01",
            end_date="2024-02-29",
        )
        stp_2 = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch_2.id)])
        stp_2.submit_date = date.today()
        data_2 = stp_2._get_complex_rendering_data()
        remuneration_collection = data_2[self.employee_1.id]["Remuneration"]
        remuneration_collection = sorted(remuneration_collection, key=lambda x: x["IncomeStreamTypeC"])
        self.assertEqual(len(remuneration_collection), 2)
        self.assertStpTupleEqual(
            remuneration_collection[0],
            {
                "GrossA": 12000,
                "IncomeStreamTypeC": "SAW",
                "IncomeTaxPayAsYouGoWithholdingTaxWithheldA": 3402.0,

            }
        )
        self.assertStpTupleEqual(
            remuneration_collection[1],
            {
                "GrossA": 5000,
                "IncomeStreamTypeC": "WHM",
                "IncomeTaxPayAsYouGoWithholdingTaxWithheldA": 966.0,
            }
        )
        self.assertStpTupleEqual(remuneration_collection[0], data[self.employee_1.id]["Remuneration"][0])
        self._submit_stp(stp_2)

    def test_finalisation(self):
        action_finalise = self.env.ref("l10n_au_hr_payroll_account.action_l10n_au_payroll_finalisation")
        # Nothing to Finalise
        with freeze_time("2024-12-30"), self.assertRaisesRegex(
            ValidationError,
            "Please select at least one employee to Finalise / Unfinalise."):
            action = Form.from_action(self.env, action_finalise.read()[0])
            action.is_eofy = True
            action.save().submit_to_ato()

        with freeze_time("2024-12-30"), self.assertRaisesRegex(
            ValidationError,
            f"There is no data to finalise for employee {self.employee_1.name} for the selected Fiscal year. "
                "Please unfinalise the employee to make any adjustments."):
            action = Form.from_action(self.env, action_finalise.read()[0])
            with action.l10n_au_payroll_finalisation_emp_ids.new() as line:
                line.employee_id = self.employee_1
            action.save().submit_to_ato()
        # Create data to finalise
        self.contract_1.date_end = "2024-11-30"
        with freeze_time("2024-11-30"):
            batch = self._prepare_payslip_run(self.employee_1 + self.employee_2, start_date="2024-11-01", end_date="2024-11-30")
            batch.action_validate()
            stp = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id)])
            self._submit_stp(stp)

        # Nothing to unfinalise
        with freeze_time("2024-12-30"), self.assertRaisesRegex(
                ValidationError,
                f"There is no data to unfinalise for employee {self.employee_1.name} for the selected Fiscal year."):
            action = Form.from_action(self.env, action_finalise.read()[0])
            action.finalisation = False
            with action.l10n_au_payroll_finalisation_emp_ids.new() as line:
                line.employee_id = self.employee_1
            action.save().submit_to_ato()

        # Finalise Data
        with freeze_time("2024-12-30"):
            action = Form.from_action(self.env, action_finalise.read()[0])
            action.is_eofy = True
            record = action.save()
            self.assertEqual(len(record.l10n_au_payroll_finalisation_emp_ids), 2)
            stp = Form.from_action(self.env, record.submit_to_ato()).save()
            self._submit_stp(stp)
        self.assertTrue(all(payslip.l10n_au_finalised for payslip in batch.slip_ids), "All payslips must be marked finalised!")

        # Unfinalise successfully
        with freeze_time("2024-12-30"):
            action = Form.from_action(self.env, action_finalise.read()[0])
            action.finalisation = False
            action.is_eofy = True
            record = action.save()
            self.assertEqual(len(record.l10n_au_payroll_finalisation_emp_ids), 2)
            stp = Form.from_action(self.env, record.submit_to_ato()).save()
            self._submit_stp(stp)
        self.assertFalse(all(payslip.l10n_au_finalised for payslip in batch.slip_ids), "All payslips must be Unfinalised!")

    def test_finalisation_without_payslips(self):
        with freeze_time("2024-12-29"):
            self.create_ytd_opening_balances(
                self.employee_2,
                [
                    ("BASIC", {"Attendance": 50000,
                                }),
                    ("WITHHOLD.TOTAL", -5753.8),
                    ("SUPER", 3355.55),
                    ("RFBA", {"Fringe Benefits Amount": 501,
                                "Fringe Benefits Amount - Exempt": 502})
                ]
            )
        action_finalise = self.env.ref("l10n_au_hr_payroll_account.action_l10n_au_payroll_finalisation")
        with freeze_time("2024-12-30"):
            action = Form.from_action(self.env, action_finalise.read()[0])
            action.is_eofy = True
            record = action.save()
            self.assertEqual(len(record.l10n_au_payroll_finalisation_emp_ids), 1)
            stp = Form.from_action(self.env, record.submit_to_ato()).save()
            employee_stp = stp.l10n_au_stp_emp
            self.assertRecordValues(employee_stp, [{
                "ytd_gross": 50000,
                "ytd_tax": 5753.8,
                "ytd_super": 3355.55,
                "ytd_rfba": 501,
                "ytd_rfbae": 502
            }])
            self._submit_stp(stp)

        with freeze_time("2024-12-30"):
            action = Form.from_action(self.env, action_finalise.read()[0])
            action.finalisation = False
            action.is_eofy = True
            record = action.save()
            self.assertEqual(len(record.l10n_au_payroll_finalisation_emp_ids), 1)
            stp = Form.from_action(self.env, record.submit_to_ato()).save()
            employee_stp = stp.l10n_au_stp_emp
            self.assertRecordValues(employee_stp, [{
                "ytd_gross": 50000,
                "ytd_tax": 5753.8,
                "ytd_super": 3355.55,
                "ytd_rfba": 501,
                "ytd_rfbae": 502
            }])
            self._submit_stp(stp)
