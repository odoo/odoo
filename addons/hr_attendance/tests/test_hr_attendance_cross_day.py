# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('at_install', '-post_install')
class TestHrAttendanceCrossDay(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Ruleset for overtime testing',
            'rule_ids': [Command.create({
                'name': 'Ruleset for overtime testing - Rule 1',
                'base_off': 'quantity',
                'expected_hours_from_contract': True,
                'quantity_period': 'day',
            })],
        })
        cls.company = cls.env['res.company'].create({
            'name': 'BE Inc.',
        })
        cls.attendance = cls.env['hr.attendance']

        # UTC+1 Employee (Europe/Brussels)
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Youssef Ahmed',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'ruleset_id': cls.ruleset.id,
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'tz': 'Europe/Brussels',
        })

        # UTC+4 Employee (Asia/Dubai)
        cls.employee_dubai = cls.env['hr.employee'].create({
            'name': 'Tariq Dubai',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'ruleset_id': cls.ruleset.id,
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'tz': 'Asia/Dubai',
        })

        # UTC-5 Employee (America/New_York)
        cls.employee_ny = cls.env['hr.employee'].create({
            'name': 'Sarah NewYork',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'ruleset_id': cls.ruleset.id,
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'tz': 'America/New_York',
        })

    def test_01_single_normal_day_attendance(self):
        """
        check-in -> (3rd) 09:00
        check-out-> (3rd) 17:00
        No split
        """
        normal_attendance = self.attendance.create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 3, 9, 0),
            'check_out': datetime(2025, 11, 3, 17, 0),
        }])
        self.assertEqual(len(normal_attendance), 1)
        self.assertEqual(normal_attendance.check_in, datetime(2025, 11, 3, 9, 0))
        self.assertEqual(normal_attendance.check_out, datetime(2025, 11, 3, 17, 0))

    def test_02_standard_overnight_checkout(self):
        """
        check-in -> (4th) 08:00 (UTC)
        check-out-> (5th) 11:00 (UTC)
        create() returns 1 record (1:1 input/output mapping).
        Post-processing cross-day splitting splits into 2 total records.
        """
        created_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 4, 8, 0, 0),
            'check_out': datetime(2025, 11, 5, 11, 0, 0)
        })

        # Contract assertion: create() must return 1 record for 1 dict input
        self.assertEqual(len(created_attendance), 1, "create() must return exactly 1 record for 1 input dict.")

        # Search for all generated splitted records
        all_split_records = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', datetime(2025, 11, 4, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 5, 23, 59, 59)),
        ], order='check_in asc')

        self.assertEqual(len(all_split_records), 2, "Post-processing should result in 2 total records.")

        # 1st record: (4th) 08:00 -> (4th) 23:00 (15hrs worked & 7hrs overtime)
        self.assertEqual(all_split_records[0].check_in, datetime(2025, 11, 4, 8, 0, 0))
        self.assertEqual(all_split_records[0].check_out, datetime(2025, 11, 4, 23, 0, 0))
        self.assertEqual(all_split_records[0].worked_hours, 15.0)
        self.assertEqual(all_split_records[0].overtime_hours, 7.0)

        # 2nd record: (4th) 23:00 -> (5th) 11:00 (12hrs worked & 4hrs overtime)
        self.assertEqual(all_split_records[1].check_in, datetime(2025, 11, 4, 23, 0, 0))
        self.assertEqual(all_split_records[1].check_out, datetime(2025, 11, 5, 11, 0, 0))
        self.assertEqual(all_split_records[1].worked_hours, 12.0)
        self.assertEqual(all_split_records[1].overtime_hours, 4.0)

    def test_03_multi_day_manual_entry(self):
        """
        check-in -> (5th) 20:00 (UTC)
        check-out-> (7th) 12:00 (UTC)
        create() returns 1 record.
        Post-processing cross-day splitting splits into 3 total records.
        """
        created_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 5, 20, 0, 0),
            'check_out': datetime(2025, 11, 7, 12, 0, 0),
        })

        # Contract assertion: create() returns 1 record
        self.assertEqual(len(created_attendance), 1, "create() must return exactly 1 record for 1 input dict.")

        all_split_records = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', datetime(2025, 11, 5, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 7, 23, 59, 59)),
        ], order='check_in asc')

        self.assertEqual(len(all_split_records), 3, "Post-processing should result in 3 total records.")

        # 1st record: (5th) 20:00 -> (5th) 23:00
        self.assertEqual(all_split_records[0].check_in, datetime(2025, 11, 5, 20, 0, 0))
        self.assertEqual(all_split_records[0].check_out, datetime(2025, 11, 5, 23, 0, 0))
        self.assertEqual(all_split_records[0].worked_hours, 3.0)
        self.assertEqual(all_split_records[0].overtime_hours, 0.0)

        # 2nd record: (5th) 23:00 -> (6th) 23:00
        self.assertEqual(all_split_records[1].check_in, datetime(2025, 11, 5, 23, 0, 0))
        self.assertEqual(all_split_records[1].check_out, datetime(2025, 11, 6, 23, 0, 0))
        self.assertEqual(all_split_records[1].worked_hours, 24.0)
        self.assertEqual(all_split_records[1].overtime_hours, 16.0)

        # 3rd record: (6th) 23:00 -> (7th) 12:00
        self.assertEqual(all_split_records[2].check_in, datetime(2025, 11, 6, 23, 0, 0))
        self.assertEqual(all_split_records[2].check_out, datetime(2025, 11, 7, 12, 0, 0))
        self.assertEqual(all_split_records[2].worked_hours, 13.0)
        self.assertEqual(all_split_records[2].overtime_hours, 5.0)

    def test_04_multiple_multi_day_creates(self):
        """
        Batch creation with 2 input dictionaries.
        create() must return a recordset of length 2.
        Post-processing cross-day splitting creates 3 additional split records (5 total).
        """
        created_attendances = self.attendance.create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 11, 10, 7, 0, 0),
                'check_out': datetime(2025, 11, 11, 23, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 11, 11, 23, 30, 0),
                'check_out': datetime(2025, 11, 14, 9, 0, 0),
            }
        ])

        # Contract assertion: batch create with 2 dicts must return exactly 2 records
        self.assertEqual(len(created_attendances), 2, "Batch create with 2 dicts must return a recordset of length 2.")

        all_split_records = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', datetime(2025, 11, 10, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 14, 23, 59, 59)),
        ], order='check_in asc')

        self.assertEqual(len(all_split_records), 5, "The batch create should result in 5 total split records.")

        # SHIFT 1: Record 1 (Monday)
        self.assertEqual(all_split_records[0].check_in, datetime(2025, 11, 10, 7, 0, 0))
        self.assertEqual(all_split_records[0].check_out, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(all_split_records[0].worked_hours, 16.0)
        self.assertEqual(all_split_records[0].overtime_hours, 8.0)

        # SHIFT 1: Record 2 (Tuesday)
        self.assertEqual(all_split_records[1].check_in, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(all_split_records[1].check_out, datetime(2025, 11, 11, 23, 0, 0))
        self.assertEqual(all_split_records[1].worked_hours, 24.0)
        self.assertEqual(all_split_records[1].overtime_hours, 16.0)

        # SHIFT 2: Record 3 (Wednesday)
        self.assertEqual(all_split_records[2].check_in, datetime(2025, 11, 11, 23, 30, 0))
        self.assertEqual(all_split_records[2].check_out, datetime(2025, 11, 12, 23, 0, 0))
        self.assertEqual(all_split_records[2].worked_hours, 23.5)
        self.assertEqual(all_split_records[2].overtime_hours, 15.5)

        # SHIFT 2: Record 4 (Thursday)
        self.assertEqual(all_split_records[3].check_in, datetime(2025, 11, 12, 23, 0, 0))
        self.assertEqual(all_split_records[3].check_out, datetime(2025, 11, 13, 23, 0, 0))
        self.assertEqual(all_split_records[3].worked_hours, 24.0)
        self.assertEqual(all_split_records[3].overtime_hours, 16.0)

        # SHIFT 2: Record 5 (Friday)
        self.assertEqual(all_split_records[4].check_in, datetime(2025, 11, 13, 23, 0, 0))
        self.assertEqual(all_split_records[4].check_out, datetime(2025, 11, 14, 9, 0, 0))
        self.assertEqual(all_split_records[4].worked_hours, 10.0)
        self.assertEqual(all_split_records[4].overtime_hours, 2.0)

    def test_05_cron_auto_check_out_without_split_shift(self):
        """
        check-in -> (10th) 09:00 (UTC)
        """
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0
        })

        check_in = datetime(2025, 11, 10, 9, 0, 0)
        open_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })

        open_attendance._cron_auto_check_out()

        closed_attendance = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '=', check_in),
        ])

        self.assertEqual(closed_attendance.check_out, datetime(2025, 11, 10, 19, 0, 0),
                        "Monday checkout should be adjusted back to 19:00 (9:00 + 8h work + 2h tol)")
        self.assertEqual(closed_attendance.out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendance.worked_hours, 10.0)

    def test_06_cron_auto_check_out_with_split_shift(self):
        """
        check-in -> (10th) 20:00 (UTC)
        """
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0
        })

        check_in = datetime(2025, 11, 10, 20, 0, 0)
        open_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })

        open_attendance._cron_auto_check_out()

        closed_attendances = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', check_in)
        ], order='check_in asc')

        self.assertEqual(len(closed_attendances), 2, "Cron execution should result in 2 split records.")

        self.assertEqual(closed_attendances[0].check_out, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(closed_attendances[0].out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendances[0].worked_hours, 3.0)

        self.assertEqual(closed_attendances[1].check_out, datetime(2025, 11, 11, 6, 0, 0))
        self.assertEqual(closed_attendances[1].out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendances[1].worked_hours, 7.0)

        self.assertEqual(sum(closed_attendances.mapped('worked_hours')), 10.0, "total worked hours (20:00 + 8h work + 2h tol)")

    def test_07_utc_plus_timezone_split_and_autocheckout(self):
        """
        Asia/Dubai (UTC+4):
        Local midnight corresponds to 20:00 UTC on the current calendar day.
        Check-in: Nov 10, 18:00 UTC (22:00 Local)
        Check-out: Nov 11, 04:00 UTC (08:00 Local)
        Should split at Nov 10, 20:00 UTC (00:00 Local).
        """
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0
        })

        check_in = datetime(2025, 11, 10, 18, 0, 0)
        open_attendance = self.attendance.create({
            'employee_id': self.employee_dubai.id,
            'check_in': check_in,
        })

        open_attendance._cron_auto_check_out()

        closed_attendances = self.attendance.search([
            ('employee_id', '=', self.employee_dubai.id),
            ('check_in', '>=', check_in)
        ], order='check_in asc')

        self.assertEqual(len(closed_attendances), 2, "Dubai shift across local midnight must split into 2 records.")

        # Record 1: 18:00 UTC -> 20:00 UTC (Local 22:00 -> 00:00, 2 hours)
        self.assertEqual(closed_attendances[0].check_in, datetime(2025, 11, 10, 18, 0, 0))
        self.assertEqual(closed_attendances[0].check_out, datetime(2025, 11, 10, 20, 0, 0))
        self.assertAlmostEqual(closed_attendances[0].worked_hours, 2.0)

        # Record 2: 20:00 UTC -> 04:00 UTC next day (Local 00:00 -> 08:00, 8 hours)
        self.assertEqual(closed_attendances[1].check_in, datetime(2025, 11, 10, 20, 0, 0))
        self.assertEqual(closed_attendances[1].check_out, datetime(2025, 11, 11, 4, 0, 0))
        self.assertAlmostEqual(closed_attendances[1].worked_hours, 8.0)

        self.assertEqual(sum(closed_attendances.mapped('worked_hours')), 10.0)

    def test_08_utc_minus_timezone_split_and_autocheckout(self):
        """
        America/New_York (UTC-5 EST):
        Local midnight corresponds to 05:00 UTC on the following calendar day.
        Check-in: Nov 10, 23:00 UTC (18:00 Local)
        Check-out: Nov 11, 09:00 UTC (04:00 Local)
        Should split at Nov 11, 05:00 UTC (00:00 Local).
        """
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0
        })

        check_in = datetime(2025, 11, 10, 23, 0, 0)
        open_attendance = self.attendance.create({
            'employee_id': self.employee_ny.id,
            'check_in': check_in,
        })

        open_attendance._cron_auto_check_out()

        closed_attendances = self.attendance.search([
            ('employee_id', '=', self.employee_ny.id),
            ('check_in', '>=', check_in)
        ], order='check_in asc')

        self.assertEqual(len(closed_attendances), 2, "NY shift across local midnight must split into 2 records.")

        # Record 1: 23:00 UTC -> 05:00 UTC next day (Local 18:00 -> 00:00, 6 hours)
        self.assertEqual(closed_attendances[0].check_in, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(closed_attendances[0].check_out, datetime(2025, 11, 11, 5, 0, 0))
        self.assertAlmostEqual(closed_attendances[0].worked_hours, 6.0)

        # Record 2: 05:00 UTC -> 09:00 UTC next day (Local 00:00 -> 04:00, 4 hours)
        self.assertEqual(closed_attendances[1].check_in, datetime(2025, 11, 11, 5, 0, 0))
        self.assertEqual(closed_attendances[1].check_out, datetime(2025, 11, 11, 9, 0, 0))
        self.assertAlmostEqual(closed_attendances[1].worked_hours, 4.0)

        self.assertEqual(sum(closed_attendances.mapped('worked_hours')), 10.0)

    def test_09_batch_create_across_different_timezones(self):
        """
        Batch creation for employees in different timezones simultaneously.
        create() returns 3 records (1 per employee input).
        Post-processing cross-day splits process correctly for each employee's distinct timezone.
        """
        created = self.attendance.create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 11, 10, 20, 0),
                'check_out': datetime(2025, 11, 11, 6, 0),
            },
            {
                'employee_id': self.employee_dubai.id,
                'check_in': datetime(2025, 11, 10, 18, 0),
                'check_out': datetime(2025, 11, 11, 4, 0),
            },
            {
                'employee_id': self.employee_ny.id,
                'check_in': datetime(2025, 11, 10, 23, 0),
                'check_out': datetime(2025, 11, 11, 9, 0),
            },
        ])

        self.assertEqual(len(created), 3, "Batch create across 3 employees must return exactly 3 records.")

        # Check total database records created after splits (2 split records per employee = 6 records total)
        all_recs = self.attendance.search([
            ('employee_id', 'in', [self.employee.id, self.employee_dubai.id, self.employee_ny.id]),
            ('check_in', '>=', datetime(2025, 11, 10, 0, 0, 0)),
        ])
        self.assertEqual(len(all_recs), 6, "Total records across 3 employees after timezone splits must be 6.")
