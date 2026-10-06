from datetime import date, datetime, timedelta
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

    def _assert_day_part(self, source, check_in, check_out, worked_hours, overtime_hours=None):
        """Check a part of a split attendance, with the time rule outputs created from it.

        The time rules cut the source at the end of the scheduled hours and move the excess to overtime outputs
        (``overtime_attendance_ids``), so the part spans the source and its outputs.
        """
        parts = source | source.overtime_attendance_ids
        self.assertEqual(source.check_in, check_in)
        # the outputs may stop a microsecond before midnight
        self.assertAlmostEqual(max(parts.mapped('check_out')), check_out, delta=timedelta(seconds=1))
        self.assertAlmostEqual(sum(parts.mapped('worked_hours')), worked_hours, places=2)
        if overtime_hours is not None:
            overtime = source.overtime_attendance_ids.filtered('time_rule_id')
            self.assertAlmostEqual(sum(overtime.mapped('worked_hours')), overtime_hours, places=2)

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

    def _get_sources(self, employees, check_in_from):
        """Return the split parts (no time rule outputs) of the employees from ``check_in_from``."""
        return self.attendance.search([
            ('employee_id', 'in', employees.ids),
            ('source_attendance_id', '=', False),
            ('check_in', '>=', check_in_from),
        ], order='check_in asc')

    def test_02_standard_overnight_checkout(self):
        """
        check-in -> (4th) 08:00 (UTC)
        check-out-> (5th) 11:00 (UTC)
        Brussels (UTC+1): Local midnight = 23:00 UTC.
        create() returns 1 record. Post-processing splits into 2 source records.
        Day 1: 08:00 -> 23:00 UTC (15h worked vs 8h schedule = 7h overtime output)
        Day 2: 23:00 -> 11:00 UTC (12h worked vs 8h schedule = 4h overtime output)
        """
        created_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 4, 8, 0, 0),
            'check_out': datetime(2025, 11, 5, 11, 0, 0),
        })

        # Contract assertion: create() must return 1 record for 1 dict input
        self.assertEqual(len(created_attendance), 1, "create() must return exactly 1 record for 1 input dict.")

        day1, day2 = self._get_sources(self.employee, datetime(2025, 11, 4))
        self.assertEqual(day1, created_attendance, "create() returns the first day of the split.")
        self._assert_day_part(day1, datetime(2025, 11, 4, 8, 0), datetime(2025, 11, 4, 23, 0), 15.0, overtime_hours=7.0)
        self._assert_day_part(day2, datetime(2025, 11, 4, 23, 0), datetime(2025, 11, 5, 11, 0), 12.0, overtime_hours=4.0)

    def test_03_multi_day_manual_entry(self):
        """
        check-in -> (5th) 20:00 (UTC)
        check-out-> (7th) 12:00 (UTC)
        Brussels (UTC+1): Local midnights at 23:00 UTC.
        Splits into 3 source records:
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

        day1, day2, day3 = self._get_sources(self.employee, datetime(2025, 11, 5))
        self.assertEqual(day1, created_attendance)
        self._assert_day_part(day1, datetime(2025, 11, 5, 20, 0), datetime(2025, 11, 5, 23, 0), 3.0, overtime_hours=0.0)
        self._assert_day_part(day2, datetime(2025, 11, 5, 23, 0), datetime(2025, 11, 6, 23, 0), 24.0, overtime_hours=16.0)
        self._assert_day_part(day3, datetime(2025, 11, 6, 23, 0), datetime(2025, 11, 7, 12, 0), 13.0, overtime_hours=5.0)

    def test_04_multiple_multi_day_creates(self):
        """
        Batch creation with 2 input dictionaries.
        create() must return a recordset of length 2, the first day of each attendance.
        Post-processing cross-day splitting creates 3 additional split records (5 source records).
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
            },
        ])

        # Contract assertion: batch create with 2 dicts must return exactly 2 records
        self.assertEqual(len(created_attendances), 2, "Batch create with 2 dicts must return a recordset of length 2.")

        sources = self._get_sources(self.employee, datetime(2025, 11, 10))
        self.assertEqual(len(sources), 5, "The batch create should result in 5 split source records.")
        self.assertEqual(sources[0] | sources[2], created_attendances)

        # SHIFT 1: Monday, Tuesday (ends at Tuesday's local midnight: no empty Wednesday part)
        self._assert_day_part(sources[0], datetime(2025, 11, 10, 7, 0), datetime(2025, 11, 10, 23, 0), 16.0)
        self._assert_day_part(sources[1], datetime(2025, 11, 10, 23, 0), datetime(2025, 11, 11, 23, 0), 24.0)
        # SHIFT 2: Wednesday, Thursday, Friday
        self._assert_day_part(sources[2], datetime(2025, 11, 11, 23, 30), datetime(2025, 11, 12, 23, 0), 23.5)
        self._assert_day_part(sources[3], datetime(2025, 11, 12, 23, 0), datetime(2025, 11, 13, 23, 0), 24.0)
        self._assert_day_part(sources[4], datetime(2025, 11, 13, 23, 0), datetime(2025, 11, 14, 9, 0), 10.0)

    def _auto_check_out(self, employee, check_in):
        """Open an attendance for the employee and run the automatic check-out (tolerance mode, 2h).

        The cron checks out once the employee has worked the hours of their schedule (8h) and the tolerance has
        passed. The tolerance only delays the check-out, it adds no worked time: the check-out is check-in + 8h.

        :return: the split parts, in chronological order
        """
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0,
        })
        self.attendance.create({
            'employee_id': employee.id,
            'check_in': check_in,
        })._cron_auto_check_out()
        return self._get_sources(employee, check_in)

    def test_05_cron_auto_check_out_without_split_shift(self):
        """
        check-in -> (10th) 09:00 (UTC), Brussels 10:00
        Expected work = 8h -> check-out at 17:00 UTC (Brussels 18:00), same day: no split.
        """
        closed_attendance = self._auto_check_out(self.employee, datetime(2025, 11, 10, 9, 0))
        self.assertRecordValues(closed_attendance, [{
            'check_in': datetime(2025, 11, 10, 9, 0),
            'check_out': datetime(2025, 11, 10, 17, 0),
            'out_mode': 'auto_check_out',
        }])
        self.assertAlmostEqual(closed_attendance.worked_hours, 8.0)

    def test_06_cron_auto_check_out_with_split_shift(self):
        """
        check-in -> (10th) 20:00 (UTC), Brussels 21:00
        Expected work = 8h -> check-out at (11th) 04:00 UTC (Brussels 05:00).
        Splits across Brussels midnight (Nov 10, 23:00 UTC):
          - Day 1: 20:00 -> 23:00 UTC (3.0 hours)
          - Day 2: 23:00 -> 04:00 UTC (5.0 hours)
        """
        closed_attendances = self._auto_check_out(self.employee, datetime(2025, 11, 10, 20, 0))
        self.assertRecordValues(closed_attendances, [
            {'check_in': datetime(2025, 11, 10, 20, 0), 'check_out': datetime(2025, 11, 10, 23, 0), 'out_mode': 'auto_check_out'},
            {'check_in': datetime(2025, 11, 10, 23, 0), 'check_out': datetime(2025, 11, 11, 4, 0), 'out_mode': 'auto_check_out'},
        ])
        self.assertEqual(closed_attendances.mapped('worked_hours'), [3.0, 5.0])

    def test_07_utc_plus_timezone_split_and_autocheckout(self):
        """
        Asia/Dubai (UTC+4): local midnight is 20:00 UTC on the current calendar day.
        check-in -> (10th) 18:00 UTC (22:00 local)
        Expected work = 8h -> check-out at (11th) 02:00 UTC (06:00 local).
        Splits at Nov 10, 20:00 UTC (00:00 local): 2h + 6h.
        """
        closed_attendances = self._auto_check_out(self.employee_dubai, datetime(2025, 11, 10, 18, 0))
        self.assertRecordValues(closed_attendances, [
            {'check_in': datetime(2025, 11, 10, 18, 0), 'check_out': datetime(2025, 11, 10, 20, 0)},
            {'check_in': datetime(2025, 11, 10, 20, 0), 'check_out': datetime(2025, 11, 11, 2, 0)},
        ])
        self.assertEqual(closed_attendances.mapped('worked_hours'), [2.0, 6.0])

    def test_08_utc_minus_timezone_split_and_autocheckout(self):
        """
        America/New_York (UTC-5 EST): local midnight is 05:00 UTC on the following calendar day.
        check-in -> (10th) 23:00 UTC (18:00 local)
        Expected work = 8h -> check-out at (11th) 07:00 UTC (02:00 local).
        Splits at Nov 11, 05:00 UTC (00:00 local): 6h + 2h.
        """
        closed_attendances = self._auto_check_out(self.employee_ny, datetime(2025, 11, 10, 23, 0))
        self.assertRecordValues(closed_attendances, [
            {'check_in': datetime(2025, 11, 10, 23, 0), 'check_out': datetime(2025, 11, 11, 5, 0)},
            {'check_in': datetime(2025, 11, 11, 5, 0), 'check_out': datetime(2025, 11, 11, 7, 0)},
        ])
        self.assertEqual(closed_attendances.mapped('worked_hours'), [6.0, 2.0])

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
        self.assertEqual(len(all_recs), 6, "Total records across 3 employees after timezone splits must be 6.")
