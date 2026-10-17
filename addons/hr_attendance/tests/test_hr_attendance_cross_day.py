from datetime import date, datetime
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('at_install', '-post_install')
class TestHrAttendanceCrossDay(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'BE Inc.',
        })
        cls.attendance = cls.env['hr.attendance']

        cls.att_type = cls.company._get_default_attendance_work_entry_type()
        cls.ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Overtime',
            'code': 'OT_TEST_CROSS_DAY',
        })

        # Deactivate default rules to keep tests isolated
        cls.env['hr.time.rule'].search([]).write({'active': False})

        # Create the new time rule based on employee schedule
        cls.time_rule = cls.env['hr.time.rule'].create({
            'name': 'Daily Overtime Rule',
            'working_hours_mode': 'schedule_day',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [(4, cls.att_type.id)],
            'company_id': cls.company.id,
        })

        # UTC+1 Employee (Europe/Brussels)
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Youssef Ahmed',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'tz': 'Europe/Brussels',
        })

        # UTC+4 Employee (Asia/Dubai)
        cls.employee_dubai = cls.env['hr.employee'].create({
            'name': 'Tariq Ali',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'tz': 'Asia/Dubai',
        })

        # UTC-5 Employee (America/New_York)
        cls.employee_ny = cls.env['hr.employee'].create({
            'name': 'Sarah Mohammed',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'tz': 'America/New_York',
        })

    def test_01_single_normal_day_attendance(self):
        """
        check-in  -> (3rd) 09:00 UTC
        check-out -> (3rd) 17:00 UTC
        No split expected for single day attendance
        """
        normal_attendance = self.attendance.create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 3, 9, 0),
            'check_out': datetime(2025, 11, 3, 17, 0),
        }])

        self.assertEqual(len(normal_attendance), 1)
        self.assertEqual(normal_attendance.check_in, datetime(2025, 11, 3, 9, 0))
        self.assertEqual(normal_attendance.check_out, datetime(2025, 11, 3, 17, 0))

    '''def test_02_standard_overnight_checkout(self):
        """
        check-in -> (4th) 08:00 (UTC)
        check-out-> (5th) 11:00 (UTC)
        Brussels (UTC+1): Local midnight = 23:00 UTC.
        create() returns 1 record. Post-processing splits into 2 total records.
        Day 1: 08:00 -> 23:00 UTC (15h worked vs 8h schedule = 7h overtime output)
        Day 2: 23:00 -> 11:00 UTC (12h worked vs 8h schedule = 4h overtime output)
        """
        created_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 4, 8, 0, 0),
            'check_out': datetime(2025, 11, 5, 11, 0, 0)
        })

        # Contract assertion: create() must return 1 record for 1 dict input
        self.assertEqual(len(created_attendance), 1, "create() must return exactly 1 record for 1 input dict.")

        # Search for primary (source) split records
        all_split_records = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('source_attendance_id', '=', False),
            ('check_in', '>=', datetime(2025, 11, 4, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 5, 23, 59, 59)),
        ], order='check_in asc')

        for a in all_split_records:
            print(f">> Split Record: {a.check_in} -> {a.check_out}, Worked Hours: {a.worked_hours}")
            for ot in a.overtime_attendance_ids:
                print(f"  - Overtime Output: {ot.check_in} -> {ot.check_out}, Worked Hours: {ot.worked_hours}, Time Rule: {ot.time_rule_id.name}")

        print(" ")

        self.assertEqual(len(all_split_records), 2, "Post-processing should result in 2 total source records.")

        # 1st record: (4th) 08:00 -> (4th) 23:00 (15.0 worked hours)
        self.assertEqual(all_split_records[0].check_in, datetime(2025, 11, 4, 8, 0, 0))
        self.assertEqual(all_split_records[0].check_out, datetime(2025, 11, 4, 23, 0, 0))
        self.assertEqual(all_split_records[0].worked_hours, 15.0)

        ot_outputs_day1 = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('time_rule_id', '!=', False),
            ('check_in', '>=', datetime(2025, 11, 4, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 4, 23, 59, 59)),
        ])
        self.assertAlmostEqual(sum(ot_outputs_day1.mapped('worked_hours')), 7.0, places=2)

        # 2nd record: (4th) 23:00 -> (5th) 11:00 (12.0 worked hours)
        self.assertEqual(all_split_records[1].check_in, datetime(2025, 11, 4, 23, 0, 0))
        self.assertEqual(all_split_records[1].check_out, datetime(2025, 11, 5, 11, 0, 0))
        self.assertEqual(all_split_records[1].worked_hours, 12.0)

        ot_outputs_day2 = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('time_rule_id', '!=', False),
            ('check_in', '>=', datetime(2025, 11, 5, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 5, 23, 59, 59)),
        ])
        self.assertAlmostEqual(sum(ot_outputs_day2.mapped('worked_hours')), 4.0, places=2)

    def test_03_multi_day_manual_entry(self):
        """
        check-in -> (5th) 20:00 (UTC)
        check-out-> (7th) 12:00 (UTC)
        Brussels (UTC+1): Local midnights at 23:00 UTC.
        Splits into 3 total records:
        Day 1 (5th): 20:00 -> 23:00 UTC (3h worked vs 8h schedule = 0h overtime)
        Day 2 (6th): 23:00 -> 23:00 UTC (24h worked vs 8h schedule = 16h overtime)
        Day 3 (7th): 23:00 -> 12:00 UTC (13h worked vs 8h schedule = 5h overtime)
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
            ('source_attendance_id', '=', False),
            ('check_in', '>=', datetime(2025, 11, 5, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 7, 23, 59, 59)),
        ], order='check_in asc')

        self.assertEqual(len(all_split_records), 3, "Post-processing should result in 3 total records.")

        # 1st record: (5th) 20:00 -> (5th) 23:00
        self.assertEqual(all_split_records[0].check_in, datetime(2025, 11, 5, 20, 0, 0))
        self.assertEqual(all_split_records[0].check_out, datetime(2025, 11, 5, 23, 0, 0))
        self.assertEqual(all_split_records[0].worked_hours, 3.0)

        ot_day1 = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('time_rule_id', '!=', False),
            ('check_in', '>=', datetime(2025, 11, 5, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 5, 23, 59, 59)),
        ])
        self.assertAlmostEqual(sum(ot_day1.mapped('worked_hours')), 0.0, places=2)

        # 2nd record: (5th) 23:00 -> (6th) 23:00
        self.assertEqual(all_split_records[1].check_in, datetime(2025, 11, 5, 23, 0, 0))
        self.assertEqual(all_split_records[1].check_out, datetime(2025, 11, 6, 23, 0, 0))
        self.assertEqual(all_split_records[1].worked_hours, 24.0)

        ot_day2 = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('time_rule_id', '!=', False),
            ('check_in', '>=', datetime(2025, 11, 6, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 6, 23, 59, 59)),
        ])
        self.assertAlmostEqual(sum(ot_day2.mapped('worked_hours')), 16.0, places=2)

        # 3rd record: (6th) 23:00 -> (7th) 12:00
        self.assertEqual(all_split_records[2].check_in, datetime(2025, 11, 6, 23, 0, 0))
        self.assertEqual(all_split_records[2].check_out, datetime(2025, 11, 7, 12, 0, 0))
        self.assertEqual(all_split_records[2].worked_hours, 13.0)

        ot_day3 = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('time_rule_id', '!=', False),
            ('check_in', '>=', datetime(2025, 11, 7, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 7, 23, 59, 59)),
        ])
        self.assertAlmostEqual(sum(ot_day3.mapped('worked_hours')), 5.0, places=2)

    def test_04_multiple_multi_day_creates(self):
        """
        Batch creation with 2 input dictionaries.
        create() must return a recordset of length 2.
        Post-processing cross-day splitting creates 3 additional split records (5 total source records).
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
            ('source_attendance_id', '=', False),
            ('check_in', '>=', datetime(2025, 11, 10, 0, 0, 0)),
            ('check_out', '<=', datetime(2025, 11, 14, 23, 59, 59)),
        ], order='check_in asc')

        self.assertEqual(len(all_split_records), 5, "The batch create should result in 5 total split source records.")

        # SHIFT 1: Record 1 (Monday)
        self.assertEqual(all_split_records[0].check_in, datetime(2025, 11, 10, 7, 0, 0))
        self.assertEqual(all_split_records[0].check_out, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(all_split_records[0].worked_hours, 16.0)

        # SHIFT 1: Record 2 (Tuesday)
        self.assertEqual(all_split_records[1].check_in, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(all_split_records[1].check_out, datetime(2025, 11, 11, 23, 0, 0))
        self.assertEqual(all_split_records[1].worked_hours, 24.0)

        # SHIFT 2: Record 3 (Wednesday)
        self.assertEqual(all_split_records[2].check_in, datetime(2025, 11, 11, 23, 30, 0))
        self.assertEqual(all_split_records[2].check_out, datetime(2025, 11, 12, 23, 0, 0))
        self.assertEqual(all_split_records[2].worked_hours, 23.5)

        # SHIFT 2: Record 4 (Thursday)
        self.assertEqual(all_split_records[3].check_in, datetime(2025, 11, 12, 23, 0, 0))
        self.assertEqual(all_split_records[3].check_out, datetime(2025, 11, 13, 23, 0, 0))
        self.assertEqual(all_split_records[3].worked_hours, 24.0)

        # SHIFT 2: Record 5 (Friday)
        self.assertEqual(all_split_records[4].check_in, datetime(2025, 11, 13, 23, 0, 0))
        self.assertEqual(all_split_records[4].check_out, datetime(2025, 11, 14, 9, 0, 0))
        self.assertEqual(all_split_records[4].worked_hours, 10.0)

    def test_05_cron_auto_check_out_without_split_shift(self):
        """
        check-in -> (10th) 09:00 (UTC)
        Expected work = 8h, tolerance = 2h -> Checkout cap = 19:00 UTC (10 hours total).
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
            ('source_attendance_id', '=', False),
            ('check_in', '=', check_in),
        ])

        self.assertEqual(closed_attendance.check_out, datetime(2025, 11, 10, 19, 0, 0),
                        "Monday checkout should be adjusted back to 19:00 (9:00 + 8h work + 2h tol)")
        self.assertEqual(closed_attendance.out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendance.worked_hours, 10.0)

    def test_06_cron_auto_check_out_with_split_shift(self):
        """
        check-in -> (10th) 20:00 (UTC)
        Brussels local check-in = 21:00. Allowed hours = 8h work + 2h tol = 10h total.
        Local auto checkout at Nov 11, 07:00 (Nov 11, 06:00 UTC).
        Splits across Brussels midnight (Nov 10, 23:00 UTC):
          - Day 1: 20:00 -> 23:00 UTC (3.0 hours)
          - Day 2: 23:00 -> 06:00 UTC (7.0 hours)
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
            ('source_attendance_id', '=', False),
            ('check_in', '>=', check_in)
        ], order='check_in asc')

        self.assertEqual(len(closed_attendances), 2, "Cron execution should result in 2 split records.")

        self.assertEqual(closed_attendances[0].check_out, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(closed_attendances[0].out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendances[0].worked_hours, 3.0)

        self.assertEqual(closed_attendances[1].check_out, datetime(2025, 11, 11, 6, 0, 0))
        self.assertEqual(closed_attendances[1].out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendances[1].worked_hours, 7.0)

        self.assertEqual(sum(closed_attendances.mapped('worked_hours')), 10.0)

    def test_07_utc_plus_timezone_split_and_autocheckout(self):
        """
        Asia/Dubai (UTC+4):
        Local midnight corresponds to 20:00 UTC on the current calendar day.
        Check-in: Nov 10, 18:00 UTC (22:00 Local)
        Cron auto check-out allows 10 hours total -> Checkout at Nov 11, 04:00 UTC (08:00 Local).
        Splits at Nov 10, 20:00 UTC (00:00 Local).
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
            ('source_attendance_id', '=', False),
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
        Cron auto check-out allows 10 hours total -> Checkout at Nov 11, 09:00 UTC (04:00 Local).
        Splits at Nov 11, 05:00 UTC (00:00 Local).
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
            ('source_attendance_id', '=', False),
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

        # Check total source database records created after splits (2 split records per employee = 6 records total)
        all_recs = self.attendance.search([
            ('employee_id', 'in', [self.employee.id, self.employee_dubai.id, self.employee_ny.id]),
            ('source_attendance_id', '=', False),
            ('check_in', '>=', datetime(2025, 11, 10, 0, 0, 0)),
        ])
        self.assertEqual(len(all_recs), 6, "Total records across 3 employees after timezone splits must be 6.")'''
