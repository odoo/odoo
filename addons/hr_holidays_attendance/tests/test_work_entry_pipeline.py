# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install', 'work_entry_pipeline')
class TestWorkEntryPipeline(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.calendar = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar
        cls.att_type = cls.env.company._get_default_attendance_work_entry_type()
        cls.env.company.attendance_work_entry_type_id = cls.att_type
        cls.overtime_type = cls.env.ref('hr_work_entry.generic_work_entry_type_overtime')

        # Disable all data-file time rules so tests are self-contained.
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.time_rule = cls.env['hr.time.rule'].create({
            'name': 'Test Schedule Rule',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.overtime_type.id,
            'condition_work_entry_type_ids': [cls.att_type.id],
        })

        cls.cal_emp = cls.env['hr.employee'].create({
            'name': 'Cal Employee',
            'tz': 'UTC',
            'attendance_based': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3500,
        })
        cls.cal_version = cls.cal_emp.version_id

        cls.flex_emp = cls.env['hr.employee'].create({
            'name': 'Flex Employee',
            'tz': 'UTC',
            'attendance_based': True,
            'resource_calendar_id': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })
        cls.flex_version = cls.flex_emp.version_id

    def _check_work_entries(self, entries, expected):
        entries = sorted(entries, key=lambda v: (v['date'], v['work_entry_type_id'].code))
        expected = sorted(expected, key=lambda e: (e[0], e[2].code))
        self.assertEqual(len(entries), len(expected),
                         f"Expected {len(expected)} entries, got {len(entries)}: "
                         f"{[(v['date'], v['duration'], v['work_entry_type_id'].code) for v in entries]}")
        for entry, (exp_date, exp_dur, exp_type) in zip(entries, expected):
            self.assertEqual(entry['date'], exp_date)
            self.assertAlmostEqual(entry['duration'], exp_dur, places=5)
            self.assertEqual(entry['work_entry_type_id'].code, exp_type.code)

    def test_no_overtime(self):
        """No attendance: a workday generates schedule-only work entries."""
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
        ])

    def test_overtime_before_and_after(self):
        """Attendance 06:00-20:00 (14h) on an 8h day -> 8h att + 6h overtime."""
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
            (date(2022, 12, 12), 6, self.overtime_type),
        ])

    def test_overtime_before_only(self):
        """Attendance 06:00-16:00 (10h) on an 8h day -> 8h att + 2h overtime."""
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 16),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
            (date(2022, 12, 12), 2, self.overtime_type),
        ])

    def test_overtime_after_only(self):
        """Attendance 10:00-20:00 (10h) on an 8h day -> 8h att + 2h overtime."""
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 10),
            'check_out': datetime(2022, 12, 12, 20),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
            (date(2022, 12, 12), 2, self.overtime_type),
        ])

    def test_overtime_weekend(self):
        """Attendance on Saturday (no schedule) -> all hours become overtime."""
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),   # Saturday
            'check_out': datetime(2022, 12, 10, 17),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 10), date(2022, 12, 10))
        self._check_work_entries(vals, [
            (date(2022, 12, 10), 6, self.overtime_type),
        ])

    def test_no_overtime_under_schedule(self):
        """Attendance within the schedule (3h < 8h) -> just 8h of schedule."""
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 9),
            'check_out': datetime(2022, 12, 12, 12),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 3, self.att_type),
        ])

    def test_flex_basic(self):
        """Flex employee: attendance -> GENERATED_ATTENDANCE work entry, no overtime."""
        self.env['hr.attendance'].create({
            'employee_id': self.flex_emp.id,
            'check_in': datetime(2022, 12, 12, 9),
            'check_out': datetime(2022, 12, 12, 13),
        })
        vals = self.flex_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 4, self.att_type),
        ])

    def test_flex_multiple_attendances_same_day(self):
        """Two attendances on the same day merge into one work entry."""
        self.env['hr.attendance'].create([
            {'employee_id': self.flex_emp.id, 'check_in': datetime(2022, 12, 12, 8), 'check_out': datetime(2022, 12, 12, 12)},
            {'employee_id': self.flex_emp.id, 'check_in': datetime(2022, 12, 12, 13), 'check_out': datetime(2022, 12, 12, 17)},
        ])
        vals = self.flex_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
        ])

    def test_attendance_unlink_removes_leave(self):
        """Deleting an attendance cascades to its source leave."""
        att = self.env['hr.attendance'].create({
            'employee_id': self.flex_emp.id,
            'check_in': datetime(2022, 12, 12, 9),
            'check_out': datetime(2022, 12, 12, 13),
        })
        leave = att.work_time_leave_id
        self.assertTrue(leave, "Source leave should be created on attendance creation")
        att.unlink()
        self.assertFalse(leave.exists(), "Source leave should be deleted when attendance is deleted")

    # Public holiday interaction TODO: public holiday cases needs a second look
    def _make_public_holiday(self, date_from, date_to, work_entry_type):
        """Create a global resource.calendar.leaves (no resource, no calendar) absence leave."""
        return self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': date_from,
            'date_to': date_to,
            'count_as': 'absence',
            'work_entry_type_id': work_entry_type.id,
        })

    def test_no_overtime_public_holiday(self):
        """Public holiday with no attendance: 8h of public-holiday work entry, nothing else."""
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTEST', 'count_as': 'absence',
        })
        # Monday 2022-12-26, full UTC day
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 8, public_type),
        ])

    def test_overtime_with_public_holiday_full_day_attendance(self):
        """14h attendance (06:00-20:00) on a public holiday.

        The time rule compares against the 8h schedule (public holidays do NOT reduce
        the expected hours in hr.time.rule) -> 6h overtime.
        The attendance covers the entire scheduled slot (08:00-17:00),
        so the public-holiday absence is trimmed
        to zero by the worked time -> no public-holiday work entry.

        this might seem counter-intuitive, that the employee worked 14 hours on a public holiday day,
        and he gets paid for 8 hours WORK100 and 6 OVERTIME.
        TODO: might need improving, but to achieve the intuitive flow for public holidays,
        we could use non-calendar based time rule (next test).
        """
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTEST2', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 20),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 8, self.att_type),
            (date(2022, 12, 26), 6, self.overtime_type),
        ])

    def test_public_holiday_intuitive_with_timing_rule(self):
        """
        A no-threshold timing rule (expected_hours=0) scoped only to public holidays
        captures all attendance as a dedicated PH-worked type.  No regular attendance
        or overtime entries are produced; the public-holiday absence is fully trimmed
        by the output leave.
        """
        ph_worked_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday Worked', 'code': 'PHWORK', 'requires_allocation': False,
        })
        # disable the main time rule on public holidays so it does not also fire.
        self.time_rule.apply_on_public_holidays = False
        self.env['hr.time.rule'].create({
            'name': 'Public Holiday Timing',
            'working_hours_mode': 'day',
            'expected_hours': 0.0,
            'timing_start': 0.0,
            'timing_stop': 24.0,
            'apply_monday': False,
            'apply_tuesday': False,
            'apply_wednesday': False,
            'apply_thursday': False,
            'apply_friday': False,
            'apply_saturday': False,
            'apply_sunday': False,
            'apply_on_public_holidays': True,
            'work_entry_type_id': ph_worked_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTEST', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 20),  # 14h
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))

        # all 14h captured as PH-worked.
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 14, ph_worked_type),
        ])

    def test_public_holiday_partial_attendance(self):
        """3h attendance within the schedule on a public holiday: no overtime (3h < 8h),
        public-holiday work entry covers the unworked schedule slots."""
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTEST3', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        # Attendance 09:00-12:00 UTC (within the morning slot 08:00-12:00)
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 9),
            'check_out': datetime(2022, 12, 26, 12),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))
        # 3h worked < 8h expected -> no overtime.
        # Public-holiday trimmed by time_on (09:00-12:00): leaves 00:00-09:00 + 12:00-23:59.
        # Intersected with schedule (08:00-12:00 + 13:00-17:00): 08:00-09:00 (1h) + 13:00-17:00 (4h) = 5h.
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 3, self.att_type),
            (date(2022, 12, 26), 5, public_type),
        ])

    def test_employer_tolerance(self):
        """Overtime below employer_tolerance is not counted.

        Employee works 8h30min (30min over the 8h schedule).  With a 1h employer
        tolerance the excess (30min < 1h) is ignored -> no overtime output leave.
        """
        self.time_rule.employer_tolerance = 1.0
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 16, 30),  # 8.5h
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        # 8.5h worked, 8h expected, 0.5h excess < 1h tolerance -> no overtime
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8.5, self.att_type),
        ])

    def test_overtime_multiple_attendances_same_day(self):
        """Two attendances totalling 10h on the same day: 8h att_type + 2h overtime."""
        self.env['hr.attendance'].create([
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 12, 7, 30),
                'check_out': datetime(2022, 12, 12, 12, 30),
            },
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 12, 12, 30),
                'check_out': datetime(2022, 12, 12, 17, 30),
            },
        ])
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        # Total 10h, schedule 8h -> 2h overtime.  Two source leaves merged into one knocked day.
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
            (date(2022, 12, 12), 2, self.overtime_type),
        ])

    def test_flex_public_holiday_trimmed_by_attendance(self):
        """Public holiday trimmed by worked time on a flex employee.

        Public holiday covers 06:00-18:00 (12h).  Two attendances: 09:00-11:00
        and 13:00-15:00 (4h total).  time_on subtracts worked slots from the
        absence leave: 12h - 4h = 8h public holiday + 4h attendance.
        """
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTESTFLEX', 'count_as': 'absence',
        })
        flex_brussels = self.env['hr.employee'].create({
            'name': 'Flex Brussels',
            'tz': 'Europe/Brussels',
            'attendance_based': True,
            'resource_calendar_id': False,
            'date_version': '2018-01-01',
            'contract_date_start': '2018-01-01',
            'wage': 3000,
        })
        self._make_public_holiday(
            datetime(2018, 1, 1, 6, 0, 0), datetime(2018, 1, 1, 18, 0, 0), public_type,
        )
        self.env['hr.attendance'].create([
            {
                'employee_id': flex_brussels.id,
                'check_in': datetime(2018, 1, 1, 9, 0, 0),
                'check_out': datetime(2018, 1, 1, 11, 0, 0),
            },
            {
                'employee_id': flex_brussels.id,
                'check_in': datetime(2018, 1, 1, 13, 0, 0),
                'check_out': datetime(2018, 1, 1, 15, 0, 0),
            },
        ])
        vals = flex_brussels.version_id.generate_work_entries(date(2018, 1, 1), date(2018, 1, 1))
        time_off_entries = [v for v in vals if v['work_entry_type_id'] == public_type]
        other_entries = [v for v in vals if v['work_entry_type_id'] != public_type]
        self.assertEqual(len(time_off_entries), 1)
        self.assertAlmostEqual(sum(v['duration'] for v in time_off_entries), 8, places=5)
        self.assertAlmostEqual(sum(v['duration'] for v in other_entries), 4, places=5)

    def test_flex_absence_leave_and_attendance(self):
        """Flex employee: resource.calendar.leaves generates entries alongside attendance leaves."""
        leave_type = self.env['hr.work.entry.type'].create({
            'name': 'Sick', 'code': 'SICKFLEX', 'count_as': 'absence',
        })
        flex_emp = self.env['hr.employee'].create({
            'name': 'Flex Sick',
            'tz': 'Europe/Brussels',
            'attendance_based': True,
            'resource_calendar_id': False,
            'date_version': '2024-09-01',
            'contract_date_start': '2024-09-01',
            'wage': 5000,
        })
        self.env['resource.calendar.leaves'].sudo().create({
            'resource_id': flex_emp.resource_id.id,
            'date_from': datetime(2024, 9, 2),
            'date_to': datetime(2024, 9, 3),
            'work_entry_type_id': leave_type.id,
        })
        vals = flex_emp.version_id.generate_work_entries(date(2024, 9, 1), date(2024, 9, 30))
        self.assertEqual(len(vals), 2)

        self.env['hr.attendance'].create({
            'employee_id': flex_emp.id,
            'check_in': datetime(2024, 9, 14, 14, 0, 0),
            'check_out': datetime(2024, 9, 14, 17, 0, 0),
        })
        vals = flex_emp.version_id.generate_work_entries(date(2024, 9, 1), date(2024, 9, 30))
        self.assertEqual(len(vals), 3)

    def test_public_holiday_preshift_attendance_no_overtime(self):
        """5h attendance 06:00-11:00 on a public holiday -> 5h att + 5h public, no overtime.

        time_on trims the public holiday inside the schedule:
          (11:00-12:00) + (13:00-17:00) = 5h public remain.
        5h worked < 8h expected -> no overtime output.
        """
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTPH', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 11),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 5, self.att_type),
            (date(2022, 12, 26), 5, public_type),
        ])

    def test_public_holiday_small_attendance_no_overtime(self):
        """1h attendance 10:00-11:00 on a public holiday -> 1h att + 7h public, no overtime.

        time_on = 10:00-11:00; remaining public holiday in schedule:
          (08:00-10:00) + (11:00-12:00) + (13:00-17:00) = 7h.
        1h worked < 8h expected -> no overtime.
        """
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTPH2', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 10),
            'check_out': datetime(2022, 12, 26, 11),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 1, self.att_type),
            (date(2022, 12, 26), 7, public_type),
        ])

    def test_no_rule_attendance_on_public_holiday(self):
        """14h attendance (06:00-20:00) on a public holiday with no time rule active.

        Without a rule the source attendance leave (14h) is not split; the public
        holiday absence is fully trimmed by time_on (attendance covers all schedule
        slots 08:00-12:00 + 13:00-17:00) -> 0h public holiday entry.
        Result: 14h att_type only.
        """
        self.time_rule.active = False
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTPH3', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 20),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 14, self.att_type),
        ])

    def test_timing_window_overtime(self):
        """Three timing rules cover the out-of-schedule slot (old test_14).

        Rules:   morning [00:00-08:00], lunch [12:00-13:00], afternoon [17:00-23:59]
        Schedule: Mon-Fri 08:00-12:00 + 13:00-17:00 (8h/day, all UTC)

        With attendance 06:00-20:00 (14h) each rule fires on its window:
          morning   06:00-08:00 = 2h  (0h scheduled in window -> all excess)
          lunch     12:00-13:00 = 1h  (0h scheduled in window -> all excess)
          afternoon 17:00-20:00 = 3h  (0h scheduled in window -> all excess)
        Total overtime = 6h; remaining attendance = 8h att_type.
        """
        self.time_rule.active = False
        for name, t_start, t_stop in [
            ('Morning OT', 0.0, 8.0),
            ('Lunch OT', 12.0, 13.0),
            ('Afternoon OT', 17.0, 23.99),
        ]:
            self.env['hr.time.rule'].create({
                'name': name,
                'working_hours_mode': 'schedule_day',
                'timing_start': t_start,
                'timing_stop': t_stop,
                'work_entry_type_id': self.overtime_type.id,
                'condition_work_entry_type_ids': [self.att_type.id],
            })
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        att_dur = sum(v['duration'] for v in vals if v['work_entry_type_id'] == self.att_type)
        ot_dur = sum(v['duration'] for v in vals if v['work_entry_type_id'] == self.overtime_type)
        self.assertAlmostEqual(att_dur, 8, places=5,
                               msg=f"Expected 8h att, got {att_dur}h")
        self.assertAlmostEqual(ot_dur, 6, places=5,
                               msg=f"Expected 6h overtime, got {ot_dur}h")

    def test_timezone_generation_boundary(self):
        """generate_work_entries date range accounts for the employee's timezone.

        Attendance starts Sunday 22:00 UTC = Monday 07:00 Asia/Tokyo.
        Requesting Monday in Tokyo should include this attendance even though
        the check_in is technically Sunday in UTC.
        """
        emp_tokyo = self.env['hr.employee'].create({
            'name': 'Tokyo Employee',
            'tz': 'Asia/Tokyo',
            'attendance_based': True,
            'resource_calendar_id': False,
            'date_version': '2024-10-01',
            'contract_date_start': '2024-10-01',
            'wage': 3500,
        })
        monday_morning_tokyo = datetime(2024, 10, 20, 22, 0, 0)  # 22:00 Sun UTC = 07:00 Mon Tokyo
        self.env['hr.attendance'].create({
            'employee_id': emp_tokyo.id,
            'check_in': monday_morning_tokyo,
            'check_out': datetime(2024, 10, 21, 6, 0, 0),  # 15:00 Mon Tokyo
        })
        vals = emp_tokyo.version_id.generate_work_entries(date(2024, 10, 21), date(2024, 10, 21))
        vals = [v for v in vals if v['date'] >= date(2024, 10, 21)]
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals[0]['date'], date(2024, 10, 21))
        self.assertAlmostEqual(vals[0]['duration'], 8, places=5)

    def test_attendance_spanning_midnight(self):
        """Attendance crossing midnight produces entries on both days.

        Flex employee UTC: check_in Mon 22:00, check_out Tue 06:00 (8h total).
        Expecting separate work entries: Mon 2h + Tue 6h.
        """
        self.env['hr.attendance'].create({
            'employee_id': self.flex_emp.id,
            'check_in': datetime(2022, 12, 12, 22, 0),   # Monday
            'check_out': datetime(2022, 12, 13, 6, 0),    # Tuesday
        })
        vals = self.flex_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 13))
        vals = sorted(vals, key=lambda v: v['date'])
        self.assertEqual(len(vals), 2)
        self.assertEqual(vals[0]['date'], date(2022, 12, 12))
        self.assertAlmostEqual(vals[0]['duration'], 2, places=5)
        self.assertEqual(vals[1]['date'], date(2022, 12, 13))
        self.assertAlmostEqual(vals[1]['duration'], 6, places=5)

    def test_consecutive_spanning_attendances_no_crash(self):
        """Two back-to-back attendances each crossing midnight don't crash.

        Regression: multi-day attendance intervals that share a boundary point
        (Mon 22:00-Tue 06:00, Tue 06:00-Wed 06:00) should not cause singleton
        or constraint errors during work entry generation.
        """
        self.env['hr.attendance'].create([
            {
                'employee_id': self.flex_emp.id,
                'check_in': datetime(2022, 12, 12, 22, 0),
                'check_out': datetime(2022, 12, 13, 6, 0),
            },
            {
                'employee_id': self.flex_emp.id,
                'check_in': datetime(2022, 12, 13, 6, 0),
                'check_out': datetime(2022, 12, 14, 6, 0),
            },
        ])
        # Must not raise
        self.flex_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 14))

    # Refused output leave is excluded from overtime
    def test_refused_output_leave_excluded_from_overtime(self):
        """Refusing an output leave removes it from the overtime total.

        Calendar employee works 14h on an 8h day: the time rule fires and
        creates a 6h overtime output leave.  After that leave is refused,
        get_attendace_data_by_employee should report 0 overtime hours.
        """
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        start = datetime(2022, 12, 12, 0, 0)
        stop = datetime(2022, 12, 12, 23, 59, 59)

        data_before = self.cal_emp.get_attendace_data_by_employee(start, stop)
        self.assertGreater(data_before[self.cal_emp.id]['overtime_hours'], 0,
                           "Overtime should be counted before refusal")

        self.cal_emp.version_id.generate_work_entries(
            date(2022, 12, 12), date(2022, 12, 12),
        )
        overtime_leave = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ], limit=1)
        self.assertTrue(overtime_leave, "Time rule should have generated an output leave")

        overtime_leave.with_context(
            leave_skip_state_check=True,
        ).write({'state': 'refuse'})

        data_after = self.cal_emp.get_attendace_data_by_employee(start, stop)
        self.assertEqual(data_after[self.cal_emp.id]['overtime_hours'], 0,
                         "Refused output leave should not count as overtime")

    def test_flex_overlapping_leaves_no_singleton(self):
        """Overlapping personal + global absence leaves on a flex employee don't raise an error"""
        sick_type = self.env['hr.work.entry.type'].search([('code', '=', 'LEAVE110')], limit=1)
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTESTOV', 'count_as': 'absence',
        })
        flex_emp = self.env['hr.employee'].create({
            'name': 'Flex Overlap',
            'attendance_based': True,
            'resource_calendar_id': False,
            'date_version': '2025-06-01',
            'contract_date_start': '2025-06-01',
            'wage': 5000,
        })
        self.env['resource.calendar.leaves'].create([
            {
                'name': 'Sick Leave',
                'date_from': datetime(2025, 6, 25),
                'date_to': datetime(2025, 6, 29),
                'resource_id': flex_emp.resource_id.id,
                'work_entry_type_id': sick_type.id,
            },
            {
                'name': 'Public Holiday',
                'date_from': datetime(2025, 6, 27),
                'date_to': datetime(2025, 6, 27, 23, 59, 59),
                'calendar_id': False,
                'work_entry_type_id': public_type.id,
            },
        ])
        flex_emp.generate_work_entries(date(2025, 6, 25), date(2025, 6, 29))

    # Rule with no work_entry_type_id : detect excess but produce no output
    def test_no_output_when_rule_has_no_work_entry_type(self):
        """Rule with work_entry_type_id=False: excess detected but source leave untouched."""
        self.time_rule.work_entry_type_id = False
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h, 6h excess vs 8h schedule
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        # No work_entry_type_id -> _apply_output skips entirely; full 14h source leave remains
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 14, self.att_type),
        ])

    def test_incomplete_attendance_no_work_time_leave(self):
        """Attendance with no check_out: no work-time leave and no output leaves."""
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
        })
        self.assertFalse(att.work_time_leave_id, "No check_out -> no work-time leave")
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_leaves, "No source leave -> no output leaves from time rules")

    def test_attendance_write_triggers_time_rule_recompute(self):
        """Extending check_out replaces the old output leave with a correctly sized new one."""
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 18),  # 10h -> 2h overtime
        })
        output_before = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_before), 1)
        self.assertAlmostEqual(
            (output_before.date_to - output_before.date_from).total_seconds() / 3600,
            2.0, places=5, msg="Initial overtime should be 2h",
        )

        att.write({'check_out': datetime(2022, 12, 12, 20)})  # extend to 12h -> 4h overtime

        output_after = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_after), 1, "Still one output leave after recompute")
        self.assertAlmostEqual(
            (output_after.date_to - output_after.date_from).total_seconds() / 3600,
            4.0, places=5, msg="Extended overtime should be 6h",
        )

    def test_time_rule_recompute_scoped_to_date_range(self):
        """Processing one day's attendance does not delete another day's output leaves."""
        # Day A: 14h -> 6h overtime output
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        ot_day_a = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('date_from', '>=', datetime(2022, 12, 12)),
            ('date_to', '<=', datetime(2022, 12, 12, 23, 59, 59)),
        ])
        self.assertEqual(len(ot_day_a), 1, "Day A should produce one output leave")

        # Day B: exactly 8h -> no overtime, but rule recompute runs for Day B
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 13, 8),
            'check_out': datetime(2022, 12, 13, 16),
        })
        # Day A's output leave must survive the Day B recompute
        self.assertTrue(ot_day_a.exists(), "Day A output leave must not be deleted by Day B recompute")

    def test_source_leave_split_and_remainder(self):
        """After time rule fires the source leave is trimmed and output leave links back."""
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h: 8h on schedule + 6h excess
        })
        att.invalidate_recordset(fnames=['work_time_leave_id'])
        source_leave = att.work_time_leave_id
        self.assertTrue(source_leave, "Source leave should exist")

        output_leaves = self.env['hr.leave'].search([
            ('source_leave_id', '=', source_leave.id),
        ])
        self.assertEqual(len(output_leaves), 1, "One output leave for the excess")
        self.assertTrue(output_leaves.is_time_rule_output)
        self.assertEqual(output_leaves.time_rule_id, self.time_rule)

        source_dur = (source_leave.date_to - source_leave.date_from).total_seconds() / 3600
        output_dur = (output_leaves.date_to - output_leaves.date_from).total_seconds() / 3600
        self.assertAlmostEqual(output_dur, 6.0, places=5, msg="Output covers the 6h excess")
        self.assertAlmostEqual(source_dur + output_dur, 14.0, places=5,
                               msg="Source + output must total the original attendance duration")

    def test_deficit_rule(self):
        """threshold_operator='less_than': output leave created for unworked schedule gap."""
        gap_type = self.env['hr.work.entry.type'].create({
            'name': 'Under Time', 'code': 'DEFTEST', 'count_as': 'absence', 'requires_allocation': False,
        })
        self.time_rule.write({
            'threshold_operator': 'less_than',
            'work_entry_type_id': gap_type.id,
        })
        # Work only the morning block (4h) on an 8h day; gap = afternoon block [13:00-17:00]
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 12),
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_leaves), 1)
        duration = (output_leaves.date_to - output_leaves.date_from).total_seconds() / 3600
        self.assertAlmostEqual(duration, 4.0, places=5,
                               msg="Deficit output should cover the unworked 4h afternoon slot")
        self.assertEqual(output_leaves.work_entry_type_id, gap_type)

    def test_weekly_aggregate_overtime(self):
        """working_hours_mode='week' evaluates total attendance across the whole week."""
        self.time_rule.active = False
        weekly_rule = self.env['hr.time.rule'].create({
            'name': 'Weekly OT',
            'working_hours_mode': 'week',
            'expected_hours': 16.0,  # expect 16h/week
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        # Two days x 9h = 18h total for the week -> 2h overtime
        self.env['hr.attendance'].create([
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 12, 8),   # Monday
                'check_out': datetime(2022, 12, 12, 17),  # 9h
            },
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 13, 8),   # Tuesday
                'check_out': datetime(2022, 12, 13, 17),  # 9h
            },
        ])
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', weekly_rule.id),
        ])
        self.assertEqual(len(output_leaves), 1)
        duration = (output_leaves.date_to - output_leaves.date_from).total_seconds() / 3600
        self.assertAlmostEqual(duration, 2.0, places=5, msg="2h excess over the 16h weekly limit")

    def test_leave_compensation_allocation_on_excess(self):
        """leave_compensation_rate > 0 creates a compensatory allocation when overtime fires."""
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Compensatory Rest',
            'code': 'COMPREST',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        self.time_rule.write({
            'leave_compensation_rate': 50.0,  # 50% of excess hours -> allocation days
            'allocation_type_id': comp_type.id,
        })
        # 14h on 8h day -> 6h excess -> 6 * 50% = 3 allocation days
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        allocation = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', comp_type.id),
        ])
        self.assertEqual(len(allocation), 1, "Allocation should be auto-created")
        self.assertAlmostEqual(allocation.number_of_days, 3.0, places=5,
                               msg="6h * 50% = 3 compensatory days")

    def test_employee_domain_filters_rule(self):
        """employee_domain limits rule application to matching employees only."""
        self.time_rule.employee_domain = f"[('id', '=', {self.cal_emp.id})]"

        other_emp = self.env['hr.employee'].create({
            'name': 'Excluded Employee',
            'tz': 'UTC',
            'attendance_based': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })
        # Both employees work 14h on an 8h day : rule only applies to cal_emp
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        self.env['hr.attendance'].create({
            'employee_id': other_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        cal_outputs = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(cal_outputs), 1, "Rule should fire for the matching employee")

        other_outputs = self.env['hr.leave'].search([
            ('employee_id', '=', other_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(other_outputs, "Rule should not fire for the excluded employee")

    def test_reference_calendar_uses_reference_hours(self):
        """calendar_source='reference' uses the specified calendar as expected-hours baseline."""
        ref_calendar = self.env['resource.calendar'].create({
            'name': '12h Reference',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 6})
                for wd in ['0', '1', '2', '3', '4']
                for h in [6, 13]
            ],
        })
        self.time_rule.write({
            'calendar_source': 'reference',
            'resource_calendar_id': ref_calendar.id,
        })
        # Employee (8h/day schedule) works 10h.  With employee calendar -> 2h excess.
        # With reference calendar (12h/day) -> 10h < 12h -> no overtime output.
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 18),  # 10h
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_leaves,
                         "10h worked < 12h reference baseline -> no overtime output")

    def test_overlapping_rules_sequence_priority(self):
        """When two rules both fire for the same excess interval, lowest sequence wins."""
        second_ot_type = self.env['hr.work.entry.type'].create({
            'name': 'Double Overtime', 'code': 'DBLOVT',
        })
        self.env['hr.time.rule'].create({
            'name': 'Lower Priority Rule',
            'sequence': self.time_rule.sequence + 10,
            'work_entry_type_id': second_ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h -> 6h excess
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_leaves), 1, "Overlapping rules must produce one merged output")
        self.assertEqual(
            output_leaves.work_entry_type_id, self.overtime_type,
            "Lower sequence (cls.time_rule) must determine the output work entry type",
        )

    def test_rule_skips_excluded_weekday(self):
        """Rule with apply_saturday=False does not fire on Saturday attendance."""
        self.time_rule.apply_saturday = False
        # Saturday: no schedule -> would all be excess if rule fired
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),   # Saturday
            'check_out': datetime(2022, 12, 10, 17),
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_leaves, "Rule must not fire on excluded Saturday")

    def test_rule_skips_public_holiday_when_excluded(self):
        """apply_on_public_holidays=False removes the PH day from rule_intervals."""
        self.time_rule.apply_on_public_holidays = False
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PHEXCL', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        # 14h on a Monday public holiday : would fire without the exclusion flag
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 20),
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_leaves, "Rule must not fire on excluded public holiday")

    def test_employee_tolerance_prevents_small_deficit(self):
        """Deficit below employee_tolerance is ignored by _evaluate_period."""
        gap_type = self.env['hr.work.entry.type'].create({
            'name': 'Early Out', 'code': 'EARLOUT', 'count_as': 'absence',
        })
        self.time_rule.write({
            'threshold_operator': 'less_than',
            'work_entry_type_id': gap_type.id,
            'employee_tolerance': 1.0,  # ignore deficits ≤ 1h
        })
        # Works 7.5h -> 0.5h deficit < 1h tolerance -> no output
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 15, 30),  # 7h30m
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_leaves, "0.5h deficit < 1h employee_tolerance -> no output")

    def test_timing_window_creates_remainder_leave(self):
        """Output cut from the middle of an attendance splits the source into head + tail."""
        self.time_rule.active = False
        self.env['hr.time.rule'].create({
            'name': 'Lunch Premium',
            'working_hours_mode': 'day',
            'expected_hours': 0.0,
            'timing_start': 12.0,
            'timing_stop': 13.0,
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # 8:00-20:00: lunch [12:00-13:00] = 1h excess cut from the middle
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 20),
        })
        att.invalidate_recordset(fnames=['work_time_leave_id'])
        source_leave = att.work_time_leave_id

        # Output: 1h lunch window [12:00-13:00]
        output_leaves = self.env['hr.leave'].search([
            ('source_leave_id', '=', source_leave.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_leaves), 1, "One output leave for the lunch window")
        self.assertAlmostEqual(
            (output_leaves.date_to - output_leaves.date_from).total_seconds() / 3600,
            1.0, places=5, msg="1h lunch excess",
        )
        # Tail remainder: [13:00-20:00] = 7h (remainder[1:] branch in _apply_output)
        tail_leaves = self.env['hr.leave'].search([
            ('source_leave_id', '=', source_leave.id),
            ('is_time_rule_output', '=', False),
        ])
        self.assertEqual(len(tail_leaves), 1, "Tail remainder leave for [13:00-20:00]")
        self.assertAlmostEqual(
            (tail_leaves.date_to - tail_leaves.date_from).total_seconds() / 3600,
            7.0, places=5, msg="7h tail [13:00-20:00]",
        )
        # Source trimmed to head [8:00-12:00] = 4h
        source_leave.invalidate_recordset()
        self.assertAlmostEqual(
            (source_leave.date_to - source_leave.date_from).total_seconds() / 3600,
            4.0, places=5, msg="Source trimmed to head [8:00-12:00]",
        )

    def test_source_zeroed_when_entire_attendance_is_excess(self):
        """When excess covers the entire source leave, date_to is set to date_from."""
        # Saturday: no schedule -> expected_duration=0 -> all 6h = excess -> no remainder
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),   # Saturday
            'check_out': datetime(2022, 12, 10, 17),
        })
        att.invalidate_recordset(fnames=['work_time_leave_id'])
        source_leave = att.work_time_leave_id
        source_leave.invalidate_recordset()
        self.assertEqual(
            source_leave.date_to, source_leave.date_from,
            "Source leave must be zeroed (date_to = date_from) when entirely excess",
        )
        output_leaves = self.env['hr.leave'].search([
            ('source_leave_id', '=', source_leave.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_leaves), 1)
        self.assertAlmostEqual(
            (output_leaves.date_to - output_leaves.date_from).total_seconds() / 3600,
            6.0, places=5,
        )

    def test_multiple_timing_windows_create_separate_outputs(self):
        """Two non-overlapping timing windows each produce an independent output leave."""
        self.time_rule.active = False
        morning_type = self.env['hr.work.entry.type'].create({'name': 'Morning OT', 'code': 'MOROT2', 'requires_allocation': False, 'count_as': 'working_time'})
        evening_type = self.env['hr.work.entry.type'].create({'name': 'Evening OT', 'code': 'EVOT2', 'requires_allocation': False, 'count_as': 'working_time'})
        for name, t_start, t_stop, wet in [
            ('Pre-Schedule', 0.0, 8.0, morning_type),
            ('Post-Schedule', 17.0, 24.0, evening_type),
        ]:
            self.env['hr.time.rule'].create({
                'name': name,
                'working_hours_mode': 'day',
                'expected_hours': 0.0,
                'timing_start': t_start,
                'timing_stop': t_stop,
                'work_entry_type_id': wet.id,
                'condition_work_entry_type_ids': [self.att_type.id],
            })
        # 6:00-20:00: [6:00-8:00]=2h morning, [8:00-17:00]=9h on-schedule, [17:00-20:00]=3h evening
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        morning_out = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', morning_type.id),
            ('is_time_rule_output', '=', True),
        ])
        evening_out = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', evening_type.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(morning_out), 1)
        self.assertEqual(len(evening_out), 1)
        self.assertAlmostEqual(
            (morning_out.date_to - morning_out.date_from).total_seconds() / 3600,
            2.0, places=5, msg="2h before schedule [6:00-8:00]",
        )
        self.assertAlmostEqual(
            (evening_out.date_to - evening_out.date_from).total_seconds() / 3600,
            3.0, places=5, msg="3h after schedule [17:00-20:00]",
        )

    def test_pure_timing_window_no_threshold(self):
        """Rule with expected_hours=0 marks all attendance in the window as excess."""
        self.time_rule.active = False
        self.env['hr.time.rule'].create({
            'name': 'Night Shift Premium',
            'working_hours_mode': 'day',
            'expected_hours': 0.0,  # has_threshold=False: skip comparison, all windowed = excess
            'timing_start': 0.0,
            'timing_stop': 6.0,
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # Mon 22:00 -> Tue 04:00 (6h total): Tue window [00:00-06:00] captures [00:00-04:00] = 4h
        self.env['hr.attendance'].create({
            'employee_id': self.flex_emp.id,
            'check_in': datetime(2022, 12, 12, 22),
            'check_out': datetime(2022, 12, 13, 4),
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.flex_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_leaves), 1)
        self.assertAlmostEqual(
            (output_leaves.date_to - output_leaves.date_from).total_seconds() / 3600,
            4.0, places=5,
            msg="4h in [Tue 00:00-04:00] is excess with no threshold check",
        )

    def test_deficit_compensation_deducts_from_allocation(self):
        """Deficit rule with leave_compensation_rate deducts from a compensatory allocation."""
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Flexi Leave', 'code': 'FLEXIDEF',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        allocation = self.env['hr.leave.allocation'].sudo().create({
            'employee_id': self.cal_emp.id,
            'work_entry_type_id': comp_type.id,
            'number_of_days': 10.0,
            'state': 'confirm',
        })
        allocation.action_approve()
        gap_type = self.env['hr.work.entry.type'].create({
            'name': 'Short Shift', 'code': 'DEFDEDUCT', 'count_as': 'absence', 'requires_allocation': False
        })
        self.time_rule.write({
            'threshold_operator': 'less_than',
            'work_entry_type_id': gap_type.id,
            'leave_compensation_rate': 100.0,
            'allocation_type_id': comp_type.id,
        })
        # Morning block only [8:00-12:00] -> gap [13:00-17:00] = 4h -> 4h * 100% = 4 days deducted
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 12),
        })
        allocation.invalidate_recordset()
        self.assertAlmostEqual(
            allocation.number_of_days, 6.0, places=5,
            msg="10 initial - 4 deducted = 6 remaining days",
        )

    def test_daily_and_weekly_rules_combined(self):
        """Daily and weekly rules fire independently on the same source leaves.

        Schedule: Mon-Fri 08:00-12:00 + 13:00-17:00 (8h/day, 40h/week).
        Mon: 10h attendance -> 2h daily excess.
        Tue-Fri: 8h each -> no daily excess.
        Week total: 42h -> 2h weekly excess.

        Both rules create output leaves independently; total = 4h across both.
        """
        weekly_type = self.env['hr.work.entry.type'].create({
            'name': 'Weekly OT', 'code': 'WEEKOTCOMB', 'requires_allocation': False,
        })
        weekly_rule = self.env['hr.time.rule'].create({
            'name': 'Weekly Rule',
            'working_hours_mode': 'week',
            'expected_hours': 40.0,
            'work_entry_type_id': weekly_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # Create one at a time to mirror real usage and exercise incremental rule firing.
        for day, check_out_hour in [(12, 18), (13, 16), (14, 16), (15, 16), (16, 16)]:
            self.env['hr.attendance'].create({
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, day, 8),
                'check_out': datetime(2022, 12, day, check_out_hour),
            })
        daily_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', self.time_rule.id),
        ])
        weekly_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', weekly_rule.id),
        ])
        daily_total = sum((l.date_to - l.date_from).total_seconds() / 3600 for l in daily_leaves)
        weekly_total = sum((l.date_to - l.date_from).total_seconds() / 3600 for l in weekly_leaves)
        self.assertAlmostEqual(daily_total, 2.0, places=5, msg="Mon 10h - 8h = 2h daily OT")
        self.assertAlmostEqual(weekly_total, 2.0, places=5, msg="42h - 40h = 2h weekly OT")

    def test_calendar_employee_cross_midnight_timezone(self):
        """Calendar employee in UTC+9: an attendance crossing UTC midnight is attributed
        to the correct calendar day in the employee's timezone and OT is computed against
        that day's schedule.

        Sun 22:00 UTC -> Mon 08:00 UTC = 10h (= Mon 07:00-17:00 Tokyo).
        Calendar expects 8h on Monday -> 2h overtime, both on Monday.
        """
        tokyo_emp = self.env['hr.employee'].create({
            'name': 'Tokyo Cal Employee',
            'tz': 'Asia/Tokyo',
            'attendance_based': False,
            'resource_calendar_id': self.calendar.id,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3500,
        })
        self.env['hr.attendance'].create({
            'employee_id': tokyo_emp.id,
            'check_in': datetime(2022, 12, 11, 22, 0),  # Sun 22:00 UTC = Mon 07:00 Tokyo
            'check_out': datetime(2022, 12, 12, 8, 0),   # Mon 08:00 UTC = Mon 17:00 Tokyo
        })
        vals = tokyo_emp.version_id.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        # All 10h land on Monday in Tokyo; 8h expected -> 2h OT, no Sunday entry.
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
            (date(2022, 12, 12), 2, self.overtime_type),
        ])

    def test_multiple_deficit_rules_least_consequent_wins(self):
        """When two deficit rules apply to the same day, the one with the smaller
        deficit (closest to zero) wins — the other is suppressed via sequence priority.

        Rules: deficit-A expects 8h (sequence 10), deficit-B expects 10h (sequence 20).
        Employee works 5h -> deficit-A = 3h, deficit-B = 5h.
        Only the 3h deficit output should be created (lowest sequence wins).
        """
        gap_type_a = self.env['hr.work.entry.type'].create({
            'name': 'Undertime A', 'code': 'DEFA', 'count_as': 'absence', 'requires_allocation': False,
        })
        gap_type_b = self.env['hr.work.entry.type'].create({
            'name': 'Undertime B', 'code': 'DEFB', 'count_as': 'absence', 'requires_allocation': False,
        })
        self.time_rule.write({
            'threshold_operator': 'less_than',
            'work_entry_type_id': gap_type_a.id,
            'sequence': 10,
        })
        self.env['hr.time.rule'].create({
            'name': 'Deficit B',
            'threshold_operator': 'less_than',
            'working_hours_mode': 'day',
            'expected_hours': 10.0,
            'work_entry_type_id': gap_type_b.id,
            'condition_work_entry_type_ids': [self.att_type.id],
            'sequence': 20,
        })
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 13),  # 5h
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_leaves), 1, "Only the lowest-sequence deficit rule should produce an output")
        self.assertEqual(output_leaves.work_entry_type_id, gap_type_a)
        duration = (output_leaves.date_to - output_leaves.date_from).total_seconds() / 3600
        self.assertAlmostEqual(duration, 3.0, places=5)

    def test_deficit_builds_and_clears_with_incremental_attendances(self):
        """Incremental attendance creates correctly update the deficit output.

        Schedule: 8h/day.  Three creates in sequence:
          1. 4h morning  -> 4h deficit
          2. +4h afternoon -> deficit cleared (exactly 8h worked)
          3. +1h extra   -> deficit gone, 1h overtime instead
        """
        gap_type = self.env['hr.work.entry.type'].create({
            'name': 'Undertime', 'code': 'DEFINCR', 'count_as': 'absence', 'requires_allocation': False,
        })
        self.env['hr.time.rule'].create({
            'name': 'Deficit Rule',
            'threshold_operator': 'less_than',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': gap_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        def _deficit_duration():
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', self.cal_emp.id),
                ('is_time_rule_output', '=', True),
                ('work_entry_type_id', '=', gap_type.id),
            ])
            return sum((l.date_to - l.date_from).total_seconds() / 3600 for l in leaves)

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 12),  # 4h
        })
        self.assertAlmostEqual(_deficit_duration(), 4.0, places=5, msg="4h worked -> 4h deficit")

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 13),
            'check_out': datetime(2022, 12, 12, 17),  # +4h = 8h total
        })
        self.assertAlmostEqual(_deficit_duration(), 0.0, places=5, msg="8h worked -> deficit cleared")

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 17),
            'check_out': datetime(2022, 12, 12, 18),  # +1h = 9h total
        })
        self.assertAlmostEqual(_deficit_duration(), 0.0, places=5, msg="9h worked -> no deficit, only OT")
        ot_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('work_entry_type_id', '=', self.overtime_type.id),
        ])
        ot_duration = sum((l.date_to - l.date_from).total_seconds() / 3600 for l in ot_leaves)
        self.assertAlmostEqual(ot_duration, 1.0, places=5, msg="1h excess -> 1h overtime output")

    def test_calendar_employee_overtime_spanning_midnight(self):
        """Calendar employee: a single attendance crossing midnight generates overtime
        on both days independently.

        Fri 08:00 -> Sat 03:00 (19h total).
        Fri schedule: 8h expected -> 11h worked on Fri (08:00-23:59) -> wait,
        the source leave is split at midnight, so:
          Fri portion: 08:00-00:00 = 16h, expected 8h -> 8h OT
          Sat portion: 00:00-03:00 = 3h,  no schedule  -> 3h OT
        Total OT = 11h across two work entries.
        """
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 9, 8),    # Friday
            'check_out': datetime(2022, 12, 10, 3),   # Saturday 03:00
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 9), date(2022, 12, 10))
        ot_vals = [v for v in vals if v['work_entry_type_id'] == self.overtime_type]
        total_ot = sum(v['duration'] for v in ot_vals)
        self.assertAlmostEqual(total_ot, 11.0, places=5,
                               msg="8h Fri OT + 3h Sat OT = 11h total")

    def test_total_overtime_reflects_output_leaves(self):
        """employee.total_overtime sums validated output leave hours and excludes refused ones.
        """
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),   # Saturday
            'check_out': datetime(2022, 12, 10, 17),   # 6h, no schedule -> 6h OT
        })
        self.cal_emp.invalidate_recordset(['total_overtime'])
        self.assertAlmostEqual(self.cal_emp.total_overtime, 6.0, places=5,
                               msg="6h on Saturday -> 6h OT output -> total_overtime=6")

        output_leave = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ], limit=1)
        output_leave.with_context(leave_skip_state_check=True).write({'state': 'refuse'})
        self.cal_emp.invalidate_recordset(['total_overtime'])
        self.assertAlmostEqual(self.cal_emp.total_overtime, 0.0, places=5,
                               msg="Refused output leave must not count toward total_overtime")

    def test_overtime_fires_when_absence_leave_approved(self):
        """Approving an absence leave on a worked day triggers overtime; refusing clears it.
        """
        absence_type = self.env['hr.work.entry.type'].create({
            'name': 'Sick', 'code': 'SICKOT1', 'count_as': 'absence', 'requires_allocation': False,
        })
        def _output_leaves():
            return self.env['hr.leave'].search([
                ('employee_id', '=', self.cal_emp.id),
                ('is_time_rule_output', '=', True),
                ('state', '!=', 'refuse'),
            ])

        # Monday 8h attendance -> exactly 8h expected -> 0h OT
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 16),
        })
        self.cal_emp.invalidate_recordset(['total_overtime'])
        self.assertAlmostEqual(self.cal_emp.total_overtime, 0.0, places=5,
                               msg="8h worked = 8h scheduled -> no OT before leave")
        self.assertFalse(_output_leaves(), "No output leave expected before absence is approved")

        # Approve absence leave: effective schedule drops to 0h -> 8h OT
        leave = self.env['hr.leave'].sudo().create({
            'name': 'Sick Day',
            'employee_id': self.cal_emp.id,
            'work_entry_type_id': absence_type.id,
            'request_date_from': date(2022, 12, 12),
            'request_date_to': date(2022, 12, 12),
            'state': 'confirm',
        })
        leave.sudo()._action_validate(check_state=False)
        self.cal_emp.invalidate_recordset(['total_overtime'])
        self.assertAlmostEqual(self.cal_emp.total_overtime, 8.0, places=5,
                               msg="Absence approved -> schedule 0h -> all 8h attendance = OT")
        ot_leaves = _output_leaves()
        self.assertEqual(len(ot_leaves), 1, "One output leave created after absence approved")
        ot_duration = (ot_leaves.date_to - ot_leaves.date_from).total_seconds() / 3600
        self.assertAlmostEqual(ot_duration, 8.0, places=5,
                               msg="Output leave covers the full 8h attendance")
        self.assertEqual(ot_leaves.work_entry_type_id, self.overtime_type)

        # Refuse the leave: schedule restores to 8h -> OT disappears
        leave.sudo().action_refuse()
        self.cal_emp.invalidate_recordset(['total_overtime'])
        self.assertAlmostEqual(self.cal_emp.total_overtime, 0.0, places=5,
                               msg="Leave refused -> schedule 8h -> 0h OT")
        self.assertFalse(_output_leaves(), "Output leave must be cleared after absence refused")

    def test_get_attendance_data_worked_hours_and_overtime_hours(self):
        """get_attendace_data_by_employee returns correct worked_hours and overtime_hours.

        Jan 1 2021 (Friday): 8-12 + 13-20 = 11h, schedule 8h -> 3h OT.
        Jan 2 2021 (Saturday): 4-20 = 16h, no schedule -> 16h OT.
        Feb 2 2021: 5h attendance, outside the Jan query window.
        """
        self.env['hr.attendance'].create([
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2021, 1, 1, 8),
                'check_out': datetime(2021, 1, 1, 12),
            },
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2021, 1, 1, 13),
                'check_out': datetime(2021, 1, 1, 20),
            },
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2021, 1, 2, 4),
                'check_out': datetime(2021, 1, 2, 20),
            },
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2021, 2, 2, 8),
                'check_out': datetime(2021, 2, 2, 13),   # outside Jan window
            },
        ])
        data = self.cal_emp.get_attendace_data_by_employee(
            datetime(2021, 1, 1, 0, 0), datetime(2021, 1, 31, 23, 59),
        )
        emp_data = data[self.cal_emp.id]
        self.assertAlmostEqual(emp_data['worked_hours'], 27.0, places=5,
                               msg="11h + 16h from Jan attendances")
        self.assertAlmostEqual(emp_data['overtime_hours'], 19.0, places=5,
                               msg="3h (Fri excess) + 16h (Sat, no schedule) = 19h OT")

    def _make_working_time_leave(self, date_from, date_to):
        wt_type = self.env['hr.work.entry.type'].create({
            'name': 'Training Day', 'code': f'TRAIN{date_from.day}', 'requires_allocation': False,
            'count_as': 'working_time',
            'request_unit': 'hour',
            'sequence': 10,  # beats source/remainder rcls (default seq=25)
        })
        leave = self.env['hr.leave'].with_context(
            leave_fast_create=True,
            leave_exact_dates=True,
            leave_skip_state_check=True,
        ).sudo().create({
            'employee_id': self.cal_emp.id,
            'work_entry_type_id': wt_type.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': date_from.date(),
            'request_date_to': date_to.date(),
            'state': 'validate',
        })
        return leave, wt_type

    def test_working_time_leave_before_attendance_overlapping(self):
        _, wt_type = self._make_working_time_leave(
            datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 17),
        )

        # must not raise despite overlapping working_time leave already existing.
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h
        })
        output_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        ot_duration = sum(
            (l.date_to - l.date_from).total_seconds() / 3600 for l in output_leaves
        )
        self.assertAlmostEqual(ot_duration, 6.0, places=5,
                               msg="working_time leave does not reduce the time rule's expected hours")

        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))

        self._check_work_entries(vals, [
            (date(2022, 12, 12), 2, self.att_type),
            (date(2022, 12, 12), 9, wt_type),
            (date(2022, 12, 12), 3, self.overtime_type),
        ])

    def test_attendance_before_working_time_leave_overlapping(self):
        """
        attendance fires the time rule (6h OT output).
        then an overlapping manual working_time leave is then created.
        """
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h -> 6h OT output created
        })
        output_before = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_before), 1, "Attendance should produce one OT output leave")

        # must not raise despite overlapping with the attendance source leave.
        _, wt_type = self._make_working_time_leave(
            datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 17),
        )
        wt_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', wt_type.id),
        ])
        self.assertEqual(len(wt_leaves), 1, "working_time leave created successfully alongside OT output")
        output_after = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_after), 1, "OT output leave unaffected by working_time leave creation")

        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 2, self.att_type),
            (date(2022, 12, 12), 9, wt_type),
            (date(2022, 12, 12), 3, self.overtime_type),
        ])
