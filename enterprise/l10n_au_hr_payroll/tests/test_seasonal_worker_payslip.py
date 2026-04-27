# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestPayrollSeasonal(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_treatment_category = 'W'
        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 38 Hours/Week",
            'company_id': cls.australian_company.id,
            'hours_per_day': 8,
            'tz': "Australia/Sydney",
            'two_weeks_calendar': False,
            'hours_per_week': 40.0,
            'full_time_required_hours': 40.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 17, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 17, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 12.0, 13.0, "lunch"),
                ("2", 13.0, 17, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 17, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 17, "afternoon"),
            ]],
        }])

    # https://www.ato.gov.au/individuals-and-families/coming-to-australia-or-going-overseas/coming-to-australia/seasonal-worker-programme-and-pacific-labour-scheme
    def test_seasonal_payslip_1(self):
        # Uses 40 hour work week according to ATO Example
        self.resource_calendar = self.resource_calendar_40_hours_per_week

        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'L',
            'contract_date_start': date(2021, 1, 1),
            'tfn_declaration': 'provided',
            'tfn': '999999661',
            'wage_type': 'hourly',
            'hourly_wage': 28.26,
            'casual_loading': 0,
            'l10n_au_training_loan': False,
            'l10n_au_tax_free_threshold': False,
            'income_stream_type': 'SWP',
            'is_non_resident': True})

        self.assertEqual(employee.l10n_au_tax_treatment_code, 'WPXXXX')

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 5, 40, 1130.40),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 1130.40),
                ('OTE', 1130.40),
                ('GROSS', 1130.40),
                ('WITHHOLD', -169.56),
                ('WITHHOLD.TOTAL', -169.56),
                ('NET', 960.84),
                ('SUPER', 130),
            ],
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 5),
        )

    def test_seasonal_payslip_2(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'L',
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
            'income_stream_type': 'SWP',
            'non_resident': True})

        self.assertTrue(self.australian_company.l10n_au_registered_for_palm)
        self.assertEqual(employee.l10n_au_tax_treatment_code, 'WPXXXX')

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
                ('WITHHOLD', -847.5),
                ('WITHHOLD.TOTAL', -847.5),
                ('NET', 4802.5),
                ('SUPER.CONTRIBUTION', 200),
                ('SUPER', 695.75),
            ],
            input_lines=self.default_input_lines,
            payslip_date_from=date(2024, 7, 1),
            payslip_date_to=date(2024, 7, 31),
        )
