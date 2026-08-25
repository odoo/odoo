# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
from datetime import date, datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, freeze_time


@tagged('-at_install', 'post_install', 'work_entry_pipeline')
class TestTimeRulePipeline(TransactionCase):

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
        """3h worked on 8h day (under threshold) -> 3h att only, no schedule fill."""
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

        self.env['hr.attendance'].create([
            {'employee_id': self.flex_emp.id, 'check_in': datetime(2022, 12, 12, 8), 'check_out': datetime(2022, 12, 12, 12)},
            {'employee_id': self.flex_emp.id, 'check_in': datetime(2022, 12, 12, 13), 'check_out': datetime(2022, 12, 12, 17)},
        ])
        vals = self.flex_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 8, self.att_type),
        ])

    def test_attendance_unlink_removes_outputs(self):
        """Saturday source repurposed in-place as OT; unlinking it leaves no orphan records."""
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),  # Saturday -> all excess
            'check_out': datetime(2022, 12, 10, 17),
        })
        att.invalidate_recordset()
        self.assertTrue(att.active, "Source stays active as the repurposed OT record")
        self.assertEqual(att.work_entry_type_id, self.overtime_type,
                         "Source WET changed to overtime type (in-place repurpose)")
        self.assertFalse(att.overtime_attendance_ids,
                         "No child records; source IS the OT")
        att_id = att.id
        att.unlink()
        self.assertFalse(
            self.env['hr.attendance'].search([('id', '=', att_id)]),
            "Record deleted; no OT entry remains for this slot",
        )

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
        """14h attendance on full-day PH: all 14h becomes OT, PH fully trimmed by worked time."""
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
            (date(2022, 12, 26), 14, self.overtime_type),
        ])

    def test_public_holiday_intuitive_with_timing_rule(self):
        """No-threshold timing rule scoped only to public holidays captures all 14h attendance as PH-worked type."""
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
        """3h on PH (09:00-12:00) -> 3h OT + 5h remaining PH (schedule minus attendance window)."""
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PUBTEST3', 'count_as': 'absence',
        })
        self._make_public_holiday(
            datetime(2022, 12, 26, 0, 0, 0), datetime(2022, 12, 26, 23, 59, 59), public_type,
        )
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 26, 9),
            'check_out': datetime(2022, 12, 26, 12),
        })
        vals = self.cal_version.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26))
        self._check_work_entries(vals, [
            (date(2022, 12, 26), 3, self.overtime_type),
            (date(2022, 12, 26), 5, public_type),
        ])

    def test_employer_tolerance(self):
        """8h30min worked, 1h employer tolerance: 30min excess < tolerance -> no overtime."""
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

    def test_employer_tolerance_non_working_day(self):
        """Weekend rule, 1h tolerance: 10min below (no OT), 1h equal (no OT), 4h above -> full 4h OT."""
        self.time_rule.active = False
        ot_type = self.env['hr.work.entry.type'].create({
            'name': 'Weekend OT', 'code': 'WKENDOTR', 'requires_allocation': False,
        })
        self.env['hr.time.rule'].create({
            'name': 'Weekend Tolerance Rule',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'apply_monday': False,
            'apply_tuesday': False,
            'apply_wednesday': False,
            'apply_thursday': False,
            'apply_friday': False,
            'employer_tolerance': 1.0,
            'work_entry_type_id': ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        def _ot_atts(employee):
            return self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('is_time_rule_output', '=', True),
            ])

        # jan 2, 9, 16 2021 are all saturdays
        # 10 min: below 1h tolerance → no overtime created
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2021, 1, 2, 8, 0),
            'check_out': datetime(2021, 1, 2, 8, 10),
        })
        self.assertFalse(_ot_atts(self.cal_emp),
            "10 min < 1h tolerance: no overtime attendance expected")

        # 1h: equal to tolerance → still no overtime (must be strictly greater)
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2021, 1, 9, 8, 0),
            'check_out': datetime(2021, 1, 9, 9, 0),
        })
        self.assertFalse(_ot_atts(self.cal_emp),
            "1h == 1h tolerance: no overtime attendance expected")

        # 4h: above tolerance → full 4h overtime (not 4 - 1 = 3)
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2021, 1, 16, 8, 0),
            'check_out': datetime(2021, 1, 16, 12, 0),
        })
        ot = _ot_atts(self.cal_emp)
        self.assertTrue(ot, "4h > 1h tolerance: overtime attendance expected")
        self.assertAlmostEqual(
            sum(a.worked_hours for a in ot), 4.0, places=5,
            msg="overtime is the full 4h worked, not 4 - 1 = 3h",
        )

    def test_overtime_multiple_attendances_same_day(self):

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

    def test_touching_attendances_no_overlap(self):
        """Two attendances sharing an exact boundary must produce 2 distinct non-overlapping OT records."""
        self.time_rule.active = False
        self.env['hr.time.rule'].create({
            'name': 'Full Day OT',
            'working_hours_mode': 'day',
            'expected_hours': 0.0,
            'timing_start': 0.0,
            'timing_stop': 24.0,
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        self.env['hr.attendance'].create([
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 12, 5, 59, 58),
                'check_out': datetime(2022, 12, 12, 7, 6, 13),
            },
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 12, 7, 6, 13),
                'check_out': datetime(2022, 12, 12, 14, 24, 5),
            },
        ])
        outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', self.overtime_type.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(outputs), 2, "Expected 2 distinct OT records for two touching attendances")
        sorted_out = sorted(outputs, key=lambda a: a.check_in)
        self.assertLessEqual(
            sorted_out[0].check_out, sorted_out[1].check_in,
            "OT outputs must not overlap at the shared boundary",
        )

    def test_flex_public_holiday_trimmed_by_attendance(self):
        """PH (06:00-18:00, 12h) trimmed by 4h attendance -> 8h PH + 4h att."""
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

    def test_public_holiday_preshift_attendance(self):
        """5h pre-schedule attendance on full-day PH -> 5h OT + 5h remaining PH."""
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
            (date(2022, 12, 26), 5, self.overtime_type),
            (date(2022, 12, 26), 5, public_type),
        ])

    def test_public_holiday_small_attendance(self):
        """1h mid-schedule attendance on full-day PH -> 1h OT + 7h remaining PH."""
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
            (date(2022, 12, 26), 1, self.overtime_type),
            (date(2022, 12, 26), 7, public_type),
        ])

    def test_no_rule_attendance_on_public_holiday(self):
        """No active rule: 14h attendance on PH produces 14h att_type; PH fully trimmed."""
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
        """Three out-of-schedule timing rules (morning/lunch/afternoon): 6h total OT, 8h att."""
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
        """Tokyo employee: attendance at Sun 22:00 UTC (= Mon 07:00 Tokyo) is attributed to Monday."""
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
        """Flex UTC: midnight-crossing attendance (Mon 22:00 - Tue 06:00) split into Mon 2h + Tue 6h."""
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
        """Regression: consecutive midnight-crossing attendances sharing a boundary point must not crash."""
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

    def test_output_attendance_counts_in_overtime(self):

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        start = datetime(2022, 12, 12, 0, 0)
        stop = datetime(2022, 12, 12, 23, 59, 59)
        data = self.cal_emp.get_attendace_data_by_employee(start, stop)
        self.assertAlmostEqual(data[self.cal_emp.id]['overtime_hours'], 6.0, places=5,
                               msg="6h excess should show in overtime_hours")

    def test_flex_overlapping_leaves_no_singleton(self):

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

    def test_incomplete_attendance_no_outputs(self):

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
        })
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_atts, "No check_out -> no output attendances from time rules")

    def test_attendance_write_triggers_time_rule_recompute(self):
        """Extending check_out after manually deleting the stale OT output creates a correctly-sized new one."""
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 18),  # 10h -> 2h overtime
        })
        output_before = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_before), 1)
        self.assertAlmostEqual(output_before.worked_hours, 2.0, places=5,
                               msg="Initial overtime should be 2h")

        # extending att (now shrunk to 16h) to 20h overlaps the OT child (16h-18h)
        # -> must delete the output first, then extend
        output_before.unlink()
        att.write({'check_out': datetime(2022, 12, 12, 20)})  # 12h worked -> 4h excess

        output_after = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_after), 1, "One new OT output after extending and re-evaluating")
        self.assertAlmostEqual(output_after.worked_hours, 4.0, places=5,
                               msg="Extended attendance (8h-20h) -> 12h worked -> 4h overtime")

    def test_source_output_cleared_when_excess_drops(self):
        """Shrinking check_out re-evaluates but stale OT child persists (engine is additive-only)."""
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 18),  # 10h -> 2h excess -> source shrunk, output child created
        })
        att.invalidate_recordset()
        # source is shrunk to 16:00 (OT starts after check_in); it stays active
        self.assertTrue(att.active, "Source stays active when OT starts after check_in")
        self.assertEqual(att.check_out, datetime(2022, 12, 12, 16), "Source shrunk to first OT start")

        att.write({'check_out': datetime(2022, 12, 12, 16)})  # no-op value; triggers re-evaluation

        att.invalidate_recordset()
        self.assertTrue(att.active, "Source remains active")
        output_atts = self.env['hr.attendance'].search([
            ('source_attendance_id', '=', att.id),
        ])
        # stale output persists: engine is additive-only, no automatic cleanup when excess drops
        self.assertEqual(len(output_atts), 1,
                         "Stale OT child persists even though excess dropped to zero")
        self.assertAlmostEqual(output_atts.worked_hours, 2.0, places=5)

    def test_weekly_output_persists_when_week_excess_drops(self):
        """Reducing Mon so the weekly total drops to threshold: stale weekly output persists (additive-only)."""
        self.time_rule.active = False
        weekly_rule = self.env['hr.time.rule'].create({
            'name': 'Weekly OT',
            'working_hours_mode': 'week',
            'expected_hours': 40.0,
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # Mon-Fri: Mon 10h, Tue-Fri 8h each -> 42h total -> 2h weekly excess
        mon = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 18),  # 10h
        })
        for day in range(13, 17):
            self.env['hr.attendance'].create({
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, day, 8),
                'check_out': datetime(2022, 12, day, 16),  # 8h
            })
        weekly_outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', weekly_rule.id),
        ])
        self.assertEqual(len(weekly_outputs), 1, "2h weekly output should exist")
        self.assertAlmostEqual(weekly_outputs.worked_hours, 2.0, places=5)

        # Reduce Mon to 8h -> week total drops to 40h -> no new output, but stale one persists
        mon.write({'check_out': datetime(2022, 12, 12, 16)})

        weekly_outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', weekly_rule.id),
        ])
        self.assertEqual(len(weekly_outputs), 1,
                         "Stale weekly output persists; engine is additive-only")
        self.assertAlmostEqual(weekly_outputs.worked_hours, 2.0, places=5)

    def test_time_rule_recompute_scoped_to_date_range(self):

        # Day A: 14h -> 6h overtime output
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        ot_day_a = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('check_in', '>=', datetime(2022, 12, 12)),
            ('check_out', '<=', datetime(2022, 12, 12, 23, 59, 59)),
        ])
        self.assertEqual(len(ot_day_a), 1, "Day A should produce one output attendance")

        # Day B: exactly 8h -> no overtime, but rule recompute runs for Day B
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 13, 8),
            'check_out': datetime(2022, 12, 13, 16),
        })
        # Day A's output must survive the Day B recompute
        self.assertTrue(ot_day_a.exists(),
                        "Day A output attendance must not be deleted by Day B recompute")

    def test_source_attendance_split_and_remainder(self):

        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h: 8h on schedule + 6h excess
        })
        output_atts = self.env['hr.attendance'].search([
            ('source_attendance_id', '=', att.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 1, "One output attendance for the excess")
        self.assertEqual(output_atts.time_rule_id, self.time_rule)

        att.invalidate_recordset()
        # source stays active but is shrunk to [06:00-14:00]; OT covers [14:00-20:00]
        self.assertTrue(att.active, "Source stays active; only its check_out is shrunk")
        output_dur = output_atts.worked_hours
        self.assertAlmostEqual(output_dur, 6.0, places=5, msg="Output covers the 6h excess")
        self.assertAlmostEqual(att.worked_hours + output_dur, 14.0, places=5,
                               msg="Shrunk source + output must total the original attendance duration")

    def test_deficit_rule(self):

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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 1)
        self.assertAlmostEqual(output_atts.worked_hours, 4.0, places=5,
                               msg="Deficit output should cover the unworked 4h afternoon slot")
        self.assertEqual(output_atts.work_entry_type_id, gap_type)

    def test_weekly_aggregate_overtime(self):

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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', weekly_rule.id),
        ])
        self.assertEqual(len(output_atts), 1)
        self.assertAlmostEqual(output_atts.worked_hours, 2.0, places=5,
                               msg="2h excess over the 16h weekly limit")

    def test_leave_compensation_allocation_on_excess(self):
        """50% rate on 6h excess -> 3 compensatory allocation days auto-created."""
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Compensatory Rest',
            'code': 'COMPREST',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        self.time_rule.write({
            'leave_compensation_rate': 0.5,  # 50%
            'allocation_type_id': comp_type.id,
        })
        # 14h on 8h day -> 6h excess -> 6h * 50% / 8h_per_day = 0.375 allocation days
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
        self.assertAlmostEqual(allocation.number_of_days, 0.375, places=5,
                               msg="6h * 50% / 8h/day = 0.375 compensatory days")

    def test_allocation_no_wet_rule(self):
        """Allocate-only rule (no work_entry_type_id) must still create an allocation for excess hours.

        Saturday attendance: 4h, schedule=0h -> all 4h is excess.
        Rule: no output WET, 100% allocation rate.
        Expected: 4h * 100% / 8h_per_day = 0.5 compensatory days allocated.
        """
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Comp No WET',
            'code': 'COMPNOWET',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        self.time_rule.write({
            'work_entry_type_id': False,
            'leave_compensation_rate': 1.0,
            'allocation_type_id': comp_type.id,
        })
        # Saturday: 0h scheduled -> all 4h are excess
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 10),   # Saturday
            'check_out': datetime(2022, 12, 10, 14),   # 4h
        })
        allocation = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', comp_type.id),
        ])
        self.assertEqual(len(allocation), 1,
                         "Allocation should be created for an allocate-only rule with no output WET")
        self.assertAlmostEqual(
            allocation.number_of_days, 0.5, places=5,
            msg="4h excess * 100% / 8h/day = 0.5 comp days",
        )

    def test_allocation_inplace_update(self):
        """Allocation must be created even when the source record is updated in-place (whole source is excess).

        Saturday attendance: 6h, schedule=0h -> all 6h is excess.
        The source is repurposed in-place as the OT record (no child output created).
        Rule: output WET=OT, 100% allocation rate.
        Expected: 6h * 100% / 8h/day = 0.75 compensatory days allocated.
        """
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Comp Inplace',
            'code': 'COMPINPL',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        self.time_rule.write({
            'leave_compensation_rate': 1.0,
            'allocation_type_id': comp_type.id,
        })
        # Saturday: 0h scheduled -> all 6h excess -> source repurposed in-place as OT
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 10),   # Saturday
            'check_out': datetime(2022, 12, 10, 16),   # 6h
        })
        att.invalidate_recordset()
        self.assertEqual(att.work_entry_type_id, self.overtime_type,
                         "Source should be repurposed in-place as OT (prerequisite)")
        self.assertFalse(att.overtime_attendance_ids,
                         "No child outputs; source IS the OT record (in-place update)")

        allocation = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', comp_type.id),
        ])
        self.assertEqual(len(allocation), 1,
                         "Allocation must be created even when source is updated in-place")
        self.assertAlmostEqual(
            allocation.number_of_days, 0.75, places=5,
            msg="6h excess * 100% / 8h/day = 0.75 comp days",
        )

    def test_fixed_threshold_attendance_alloc_only(self):
        """Allocate-only rule with fixed 2h/day threshold: 3h attendance -> 1h excess -> 0.125d allocated.

        Exercises the code path where:
        - working_hours_mode='day' (expected_hours=2, no calendar source)
        - rule has no work_entry_type_id (allocate-only)
        - threshold is evaluated (Fix C: no early-exit for has_threshold=True)
        - excess interval keeps source WET (Fix D)
        - pp-only path in _apply_output records the excess for allocation (Fix A)
        """
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Comp Fixed Att',
            'code': 'CFATT',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        self.time_rule.write({
            'work_entry_type_id': False,
            'working_hours_mode': 'day',
            'expected_hours': 2.0,
            'leave_compensation_rate': 1.0,
            'allocation_type_id': comp_type.id,
        })
        # monday 8h-11h: 3h worked, 2h fixed threshold -> 1h excess
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 11),
        })
        allocation = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', comp_type.id),
        ])
        self.assertEqual(len(allocation), 1,
                         "Allocation must be created for allocate-only rule with fixed threshold")
        self.assertAlmostEqual(
            allocation.number_of_days, 0.125, places=5,
            msg="1h excess * 100% / 8h/day = 0.125 comp days",
        )

    def test_fixed_threshold_attendance_alloc_with_premium_pay(self):
        """Fixed 2h/day threshold: 3h attendance -> 1h excess reclassified to premium OT + allocation.

        'Premium pay' variant: the rule has both a WET (OT at 1.5x rate) and an allocation,
        so the excess hours are simultaneously reclassified and compensated with leave days.
        """
        premium_type = self.env['hr.work.entry.type'].create({
            'name': 'Premium OT 150%',
            'code': 'OT150',
            'count_as': 'working_time',
            'amount_rate': 1.5,
        })
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Comp Premium',
            'code': 'CPPREM',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        self.time_rule.write({
            'work_entry_type_id': premium_type.id,
            'working_hours_mode': 'day',
            'expected_hours': 2.0,
            'leave_compensation_rate': 0.5,
            'allocation_type_id': comp_type.id,
        })
        # monday 8h-11h: 3h worked, 2h threshold -> 1h excess -> premium OT output + 0.0625d
        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 11),
        })
        att.invalidate_recordset()
        # 1h of the attendance should be reclassified to premium OT
        ot_output = att.overtime_attendance_ids
        self.assertEqual(len(ot_output), 1, "1h excess must produce one OT child record")
        self.assertAlmostEqual(
            (ot_output.check_out - ot_output.check_in).total_seconds() / 3600, 1.0, places=5,
            msg="OT output must be exactly 1h",
        )
        self.assertEqual(ot_output.work_entry_type_id, premium_type,
                         "Excess classified to the premium OT type")
        allocation = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', comp_type.id),
        ])
        self.assertEqual(len(allocation), 1,
                         "Allocation must also be created alongside premium pay reclassification")
        self.assertAlmostEqual(
            allocation.number_of_days, 0.0625, places=5,
            msg="1h excess * 50% / 8h/day = 0.0625 comp days",
        )

    def test_overlapping_rules_both_alloc_first_rule_credited(self):
        """When R2 (output WET) reclassifies intervals already tagged by R1 (allocate-only),
        R1's allocation credit must NOT be dropped.

        R1: allocate-only (no WET, no threshold) -> tags all Saturday intervals, WET preserved.
        R2: output WET=OT, no threshold, condition=[att_type] -> reclassifies R1's intervals.

        Before fix: R2 overwrote cls_rule=R1 -> R1 allocation silently lost.
        After fix:  orphaned credit for R1 is preserved and included in excess_alloc.

        Expected: ALLOC_R1 and ALLOC_R2 each created for 6h (0.375d at 50%).
        """
        alloc_r1 = self.env['hr.work.entry.type'].create({
            'name': 'Rest R1', 'code': 'RSTR1',
            'requires_allocation': True, 'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        alloc_r2 = self.env['hr.work.entry.type'].create({
            'name': 'Rest R2', 'code': 'RSTR2',
            'requires_allocation': True, 'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        ot_r2 = self.env['hr.work.entry.type'].create({'name': 'OT R2', 'code': 'OTR2'})

        self.time_rule.active = False

        # R1: allocate-only (no WET), Saturday all-day, no threshold
        self.env['hr.time.rule'].create({
            'name': 'R1 Saturday Alloc-Only',
            'sequence': 10,
            'apply_monday': False, 'apply_tuesday': False, 'apply_wednesday': False,
            'apply_thursday': False, 'apply_friday': False,
            'apply_saturday': True, 'apply_sunday': False,
            'work_entry_type_id': False,
            'leave_compensation_rate': 0.5,
            'allocation_type_id': alloc_r1.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # R2: output WET, Saturday all-day, no threshold, same condition
        self.env['hr.time.rule'].create({
            'name': 'R2 Saturday OT',
            'sequence': 20,
            'apply_monday': False, 'apply_tuesday': False, 'apply_wednesday': False,
            'apply_thursday': False, 'apply_friday': False,
            'apply_saturday': True, 'apply_sunday': False,
            'work_entry_type_id': ot_r2.id,
            'leave_compensation_rate': 0.5,
            'allocation_type_id': alloc_r2.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # 6h Saturday: both R1 and R2 claim all 6h -> both should allocate 0.375d
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 10),   # Saturday
            'check_out': datetime(2022, 12, 10, 16),   # 6h
        })
        found_r1 = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', alloc_r1.id),
        ])
        found_r2 = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', alloc_r2.id),
        ])
        self.assertEqual(len(found_r1), 1,
                         "R1 allocation must survive even though R2 reclassifies R1's intervals")
        self.assertEqual(len(found_r2), 1, "R2 allocation must be created")
        self.assertAlmostEqual(found_r1.number_of_days, 0.375, places=5,
                               msg="R1: 6h * 50% / 8h/day = 0.375 days")
        self.assertAlmostEqual(found_r2.number_of_days, 0.375, places=5,
                               msg="R2: 6h * 50% / 8h/day = 0.375 days")

    def test_overlapping_rules_r2_targets_r1_wet_alloc(self):
        """When R2 conditions on R1's output WET and both have allocation, R1 must still be credited.

        R1: output WET=SAT_TYPE, no threshold, condition=[att], allocation=ALLOC_R1.
        R2: output WET=OVER_TYPE, no threshold, condition=[SAT_TYPE], allocation=ALLOC_R2.

        R2 reclassifies R1's SAT_TYPE intervals -> R1's allocation credit was previously lost.

        Expected: ALLOC_R1 and ALLOC_R2 each allocated for 4h (0.25d at 50%).
        """
        sat_type = self.env['hr.work.entry.type'].create({'name': 'Saturday', 'code': 'SAT'})
        over_type = self.env['hr.work.entry.type'].create({'name': 'Override', 'code': 'OVER'})
        alloc_r1 = self.env['hr.work.entry.type'].create({
            'name': 'Rest SAT', 'code': 'RSAT',
            'requires_allocation': True, 'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        alloc_r2 = self.env['hr.work.entry.type'].create({
            'name': 'Rest OVER', 'code': 'ROVER',
            'requires_allocation': True, 'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        self.time_rule.active = False

        # R1: matches att_type -> outputs SAT_TYPE for all Saturday time
        self.env['hr.time.rule'].create({
            'name': 'R1 Saturday',
            'sequence': 10,
            'apply_monday': False, 'apply_tuesday': False, 'apply_wednesday': False,
            'apply_thursday': False, 'apply_friday': False,
            'apply_saturday': True, 'apply_sunday': False,
            'work_entry_type_id': sat_type.id,
            'leave_compensation_rate': 0.5,
            'allocation_type_id': alloc_r1.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # R2: matches SAT_TYPE (R1's output) -> outputs OVER_TYPE for all of it
        self.env['hr.time.rule'].create({
            'name': 'R2 Saturday Override',
            'sequence': 20,
            'apply_monday': False, 'apply_tuesday': False, 'apply_wednesday': False,
            'apply_thursday': False, 'apply_friday': False,
            'apply_saturday': True, 'apply_sunday': False,
            'work_entry_type_id': over_type.id,
            'leave_compensation_rate': 0.5,
            'allocation_type_id': alloc_r2.id,
            'condition_work_entry_type_ids': [sat_type.id],
        })
        # 4h Saturday attendance -> R1 claims all 4h, R2 reclassifies all 4h
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 10),   # Saturday
            'check_out': datetime(2022, 12, 10, 14),   # 4h
        })
        found_r1 = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', alloc_r1.id),
        ])
        found_r2 = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', alloc_r2.id),
        ])
        self.assertEqual(len(found_r1), 1,
                         "R1 allocation must survive even though R2 reclassifies R1's WET output")
        self.assertEqual(len(found_r2), 1, "R2 allocation must be created")
        self.assertAlmostEqual(found_r1.number_of_days, 0.25, places=5,
                               msg="R1: 4h * 50% / 8h/day = 0.25 days")
        self.assertAlmostEqual(found_r2.number_of_days, 0.25, places=5,
                               msg="R2: 4h * 50% / 8h/day = 0.25 days")

    def test_employee_domain_filters_rule(self):

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
        cal_outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(cal_outputs), 1, "Rule should fire for the matching employee")

        other_outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', other_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(other_outputs, "Rule should not fire for the excluded employee")

    def test_reference_calendar_uses_reference_hours(self):
        """calendar_source='reference': 12h/day reference baseline means 10h worked produces no OT."""
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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_atts,
                         "10h worked < 12h reference baseline -> no overtime output")

    def test_reference_calendar_fires_for_fully_flexible_employee(self):
        """calendar_source='reference' must fire even for employees with no own schedule.
        """
        ref_calendar = self.env['resource.calendar'].create({
            'name': '8h Reference',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        self.time_rule.active = False
        ot_type = self.env['hr.work.entry.type'].create({
            'name': 'Flex OT', 'code': 'FLXOT',
        })
        self.env['hr.time.rule'].create({
            'name': 'Reference Rule for Flex Emp',
            'calendar_source': 'reference',
            'resource_calendar_id': ref_calendar.id,
            'quantity_period': 'day',
            'work_entry_type_id': ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        # flex_emp has no own schedule; works 10h — 2h above the 8h reference baseline.
        self.env['hr.attendance'].create({
            'employee_id': self.flex_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 18),  # 10h
        })
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.flex_emp.id),
            ('work_entry_type_id', '=', ot_type.id),
        ])
        self.assertTrue(output_atts,
                        "reference-calendar rule must fire for fully-flexible employee")
        total_ot = sum((a.check_out - a.check_in).total_seconds() / 3600 for a in output_atts)
        self.assertAlmostEqual(total_ot, 2.0, places=4,
                               msg="2h excess above 8h reference baseline expected")

    def test_sequential_rules_second_rule_finds_no_excess(self):
        """Sequential pipeline: R2 with the same threshold sees 0h excess after R1 already claimed it."""
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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 1, "Only R1 should produce output; R2 sees 0h excess after R1 fires")
        self.assertEqual(
            output_atts.work_entry_type_id, self.overtime_type,
            "The single output must be R1's overtime record",
        )

    def test_sequential_r2_targets_r1_excess(self):
        """R2 (condition=[OT]) fires on R1's 6h OT output, reclassifying the top 3h as DoubleOT."""
        double_ot_type = self.env['hr.work.entry.type'].create({
            'name': 'Double Overtime', 'code': 'DBLOT2',
        })
        self.env['hr.time.rule'].create({
            'name': 'Double OT Rule',
            'sequence': self.time_rule.sequence + 10,
            'working_hours_mode': 'day',
            'expected_hours': 3.0,
            'work_entry_type_id': double_ot_type.id,
            'condition_work_entry_type_ids': [self.overtime_type.id],
        })
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h -> 6h OT -> top 3h DoubleOT
        })
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ], order='check_in')
        self.assertEqual(len(output_atts), 2, "R1 produces OT(3h); R2 reclassifies the top 3h as DoubleOT")
        ot_att = output_atts.filtered(lambda a: a.work_entry_type_id == self.overtime_type)
        dbl_att = output_atts.filtered(lambda a: a.work_entry_type_id == double_ot_type)
        self.assertTrue(ot_att, "R1 must produce an OT output record")
        self.assertTrue(dbl_att, "R2 must produce a DoubleOT output record")
        ot_hours = (ot_att.check_out - ot_att.check_in).total_seconds() / 3600
        dbl_hours = (dbl_att.check_out - dbl_att.check_in).total_seconds() / 3600
        self.assertAlmostEqual(ot_hours, 3.0, places=4, msg="OT output must be 3h (6h excess - 3h threshold)")
        self.assertAlmostEqual(dbl_hours, 3.0, places=4, msg="DoubleOT output must be 3h (top 3h of the 6h excess)")

    def test_sequential_no_threshold_r2_classifies_att_remainder(self):
        """R2 (no threshold, condition=[ATT]) reclassifies the entire 8h ATT remainder after R1 takes 6h OT."""
        dblovt_type = self.env['hr.work.entry.type'].create({
            'name': 'Double Overtime Alt', 'code': 'DBLA',
        })
        self.env['hr.time.rule'].create({
            'name': 'Remainder Reclassify Rule',
            'sequence': self.time_rule.sequence + 10,
            'working_hours_mode': 'day',
            # expected_hours=0 (default for 'day' mode) -> no threshold
            'work_entry_type_id': dblovt_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h -> 6h OT + 8h DBLOVT
        })
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 2, "R1 produces OT(6h); R2 produces DBLOVT(8h) for the remaining ATT")
        ot_att = output_atts.filtered(lambda a: a.work_entry_type_id == self.overtime_type)
        dblovt_att = output_atts.filtered(lambda a: a.work_entry_type_id == dblovt_type)
        self.assertTrue(ot_att, "R1 must produce an OT output record")
        self.assertTrue(dblovt_att, "R2 must produce a DBLOVT output record for the ATT remainder")
        ot_hours = (ot_att.check_out - ot_att.check_in).total_seconds() / 3600
        dblovt_hours = (dblovt_att.check_out - dblovt_att.check_in).total_seconds() / 3600
        self.assertAlmostEqual(ot_hours, 6.0, places=4, msg="OT must be 6h (14h worked - 8h schedule)")
        self.assertAlmostEqual(dblovt_hours, 8.0, places=4, msg="DBLOVT must cover the full 8h ATT remainder")
        remainder_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', False),
            ('active', '=', True),
        ])
        self.assertFalse(remainder_atts, "Source fully consumed by outputs; no ATT remainder record expected")

    def test_sequential_pipeline_chained_thresholds(self):
        """R1 (>7h) -> OT1(3h); R2 (>5h, condition=[ATT]) -> OT2(2h); ATT remainder = 5h."""
        ot1_type = self.env['hr.work.entry.type'].create({'name': 'OT1', 'code': 'CCOT1'})
        ot2_type = self.env['hr.work.entry.type'].create({'name': 'OT2', 'code': 'CCOT2'})
        self.time_rule.active = False

        self.env['hr.time.rule'].create({
            'name': 'R1 >7h',
            'sequence': 10,
            'working_hours_mode': 'day',
            'expected_hours': 7.0,
            'work_entry_type_id': ot1_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        self.env['hr.time.rule'].create({
            'name': 'R2 >5h',
            'sequence': 20,
            'working_hours_mode': 'day',
            'expected_hours': 5.0,
            'work_entry_type_id': ot2_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        # Sunday 08:00-18:00 UTC = 10h ATT
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 11, 8),
            'check_out': datetime(2022, 12, 11, 18),
        })

        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 2, "R1->OT1(3h) and R2->OT2(2h); two output records")

        ot1_att = output_atts.filtered(lambda a: a.work_entry_type_id == ot1_type)
        ot2_att = output_atts.filtered(lambda a: a.work_entry_type_id == ot2_type)
        self.assertTrue(ot1_att, "R1 must produce an OT1 record")
        self.assertTrue(ot2_att, "R2 must produce an OT2 record")

        ot1_hours = (ot1_att.check_out - ot1_att.check_in).total_seconds() / 3600
        ot2_hours = (ot2_att.check_out - ot2_att.check_in).total_seconds() / 3600
        self.assertAlmostEqual(ot1_hours, 3.0, places=4,
                               msg="OT1 = 10h worked - 7h threshold")
        self.assertAlmostEqual(ot2_hours, 2.0, places=4,
                               msg="OT2 = 7h ATT remainder - 5h threshold")

        remainder_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', False),
            ('active', '=', True),
        ])
        self.assertEqual(len(remainder_atts), 1, "Exactly one ATT remainder record")
        rem_hours = (remainder_atts.check_out - remainder_atts.check_in).total_seconds() / 3600
        self.assertAlmostEqual(rem_hours, 5.0, places=4,
                               msg="ATT remainder = 10h - 3h(OT1) - 2h(OT2) = 5h")

        # OT1 and OT2 must not overlap and must be contiguous with the remainder
        self.assertLessEqual(ot2_att.check_out, ot1_att.check_in,
                             "OT2 must end where OT1 begins (no gap between the two excess bands)")

    def test_rule_skips_excluded_weekday(self):

        self.time_rule.apply_saturday = False
        # Saturday: no schedule -> would all be excess if rule fired
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),   # Saturday
            'check_out': datetime(2022, 12, 10, 17),
        })
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_atts, "Rule must not fire on excluded Saturday")

    def test_rule_skips_public_holiday_when_excluded(self):

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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_atts, "Rule must not fire on excluded public holiday")

    def test_employee_tolerance_prevents_small_deficit(self):

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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertFalse(output_atts, "0.5h deficit < 1h employee_tolerance -> no output")

    def test_employer_tolerance_expected_hours(self):
        """employer_tolerance applies to expected_hours rules (no calendar_source).
        """
        self.time_rule.active = False
        ot_type = self.env['hr.work.entry.type'].create({
            'name': 'OT Tol EH', 'code': 'OTTOLEH',
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Expected Hours Tolerance Exceed',
            'working_hours_mode': 'day',
            'expected_hours': 8.0,
            'employer_tolerance': 0.5,
            'work_entry_type_id': ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        def _ot_atts(check_in, check_out):
            return self.env['hr.attendance'].create({
                'employee_id': self.cal_emp.id,
                'check_in': check_in,
                'check_out': check_out,
            })

        # 8.3h worked: 0.3h excess < 0.5h employer_tolerance → no overtime
        att1 = _ot_atts(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 16, 18))
        output1 = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', ot_type.id),
        ])
        self.assertFalse(output1, "0.3h excess < 0.5h employer_tolerance → no overtime")

        att1.with_context(skip_time_rules=True).unlink()

        # 9h worked: 1h excess > 0.5h employer_tolerance → overtime created
        _ot_atts(datetime(2022, 12, 19, 8), datetime(2022, 12, 19, 17))
        output2 = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', ot_type.id),
        ])
        self.assertTrue(output2, "1h excess > 0.5h employer_tolerance → overtime expected")
        rule.active = False

    def test_employee_tolerance_expected_hours(self):
        """employee_tolerance applies to expected_hours rules (no calendar_source).
        """
        self.time_rule.active = False
        gap_type = self.env['hr.work.entry.type'].create({
            'name': 'Gap Tol EH', 'code': 'GAPTOLEH', 'count_as': 'absence',
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Expected Hours Tolerance Deficit',
            'working_hours_mode': 'day',
            'expected_hours': 8.0,
            'employee_tolerance': 0.5,
            'threshold_operator': 'less_than',
            'work_entry_type_id': gap_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        # 7.7h worked: 0.3h deficit < 0.5h employee_tolerance → no output
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 15, 42),  # 7h42m
        })
        output = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', gap_type.id),
        ])
        self.assertFalse(output, "0.3h deficit < 0.5h employee_tolerance → no output")
        rule.active = False

    def test_timing_window_creates_remainder_attendance(self):
        """Lunch window cut from the middle: source shrunk to head [8:00-12:00], tail [13:00-20:00] becomes remainder child."""
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

        # Output: 1h lunch window [12:00-13:00]
        output_atts = self.env['hr.attendance'].search([
            ('source_attendance_id', '=', att.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 1, "One output attendance for the lunch window")
        self.assertAlmostEqual(output_atts.worked_hours, 1.0, places=5, msg="1h lunch excess")

        # Source is shrunk to [8:00-12:00] (head); tail [13:00-20:00] becomes a remainder child
        att.invalidate_recordset()
        self.assertTrue(att.active, "Source stays active; it is shrunk to the head segment")
        self.assertEqual(att.check_out, datetime(2022, 12, 12, 12), "Source shrunk to first OT start")

        remainder_atts = self.env['hr.attendance'].search([
            ('source_attendance_id', '=', att.id),
            ('is_time_rule_output', '=', False),
        ])
        self.assertEqual(len(remainder_atts), 1, "Only the tail [13:00-20:00] is a remainder child; head is the source")
        self.assertAlmostEqual(remainder_atts.worked_hours, 7.0, places=5, msg="Tail remainder [13:00-20:00] = 7h")

    def test_source_zeroed_when_entire_attendance_is_excess(self):

        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),   # Saturday
            'check_out': datetime(2022, 12, 10, 17),
        })
        att.invalidate_recordset()
        self.assertTrue(att.active,
                        "Source is repurposed in-place; it stays active as the OT record")
        self.assertEqual(att.work_entry_type_id, self.overtime_type,
                         "Source WET changed to overtime type")
        self.assertEqual(att.time_rule_id, self.time_rule,
                         "Source time_rule_id set to the firing rule")
        self.assertFalse(att.overtime_attendance_ids,
                         "No child output records; source IS the output")
        self.assertAlmostEqual(att.worked_hours, 6.0, places=5)

    def test_multiple_timing_windows_create_separate_outputs(self):

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
        morning_out = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', morning_type.id),
            ('is_time_rule_output', '=', True),
        ])
        evening_out = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', evening_type.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(morning_out), 1)
        self.assertEqual(len(evening_out), 1)
        self.assertAlmostEqual(morning_out.worked_hours, 2.0, places=5,
                               msg="2h before schedule [6:00-8:00]")
        self.assertAlmostEqual(evening_out.worked_hours, 3.0, places=5,
                               msg="3h after schedule [17:00-20:00]")

    def test_pure_timing_window_no_threshold(self):

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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.flex_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 1)
        self.assertAlmostEqual(output_atts.worked_hours, 4.0, places=5,
                               msg="4h in [Tue 00:00-04:00] is excess with no threshold check")

    def test_deficit_compensation_deducts_from_allocation(self):
        """4h deficit at 100% rate deducts 4 days from an existing compensatory allocation."""
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
            'leave_compensation_rate': 1.0,  # 100%
            'allocation_type_id': comp_type.id,
        })
        # Morning block only [8:00-12:00] -> gap [13:00-17:00] = 4h -> 4h * 100% / 8h_per_day = 0.5 days deducted
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 12),
        })
        allocation.invalidate_recordset()
        self.assertAlmostEqual(
            allocation.number_of_days, 9.5, places=5,
            msg="10 initial - 0.5 deducted (4h * 100% / 8h/day) = 9.5 remaining days",
        )

    def test_daily_and_weekly_rules_combined(self):
        """Daily and weekly rules fire independently: 2h daily OT on Mon + 2h weekly OT from the 42h week."""
        weekly_type = self.env['hr.work.entry.type'].create({
            'name': 'Weekly OT', 'code': 'WEEKOTCOMB', 'requires_allocation': False,
        })
        weekly_rule = self.env['hr.time.rule'].create({
            'name': 'Weekly Rule',
            'working_hours_mode': 'week',
            'expected_hours': 40.0,
            'work_entry_type_id': weekly_type.id,
            # include daily OT type so Mon_OT(2h) counts toward the weekly 40h total
            'condition_work_entry_type_ids': [self.att_type.id, self.overtime_type.id],
        })
        # Create one at a time to mirror real usage and exercise incremental rule firing.
        for day, check_out_hour in [(12, 18), (13, 16), (14, 16), (15, 16), (16, 16)]:
            self.env['hr.attendance'].create({
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, day, 8),
                'check_out': datetime(2022, 12, day, check_out_hour),
            })
        daily_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', self.time_rule.id),
        ])
        weekly_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('time_rule_id', '=', weekly_rule.id),
        ])
        daily_total = sum(a.worked_hours for a in daily_atts)
        weekly_total = sum(a.worked_hours for a in weekly_atts)
        self.assertAlmostEqual(daily_total, 2.0, places=5, msg="Mon 10h - 8h = 2h daily OT")
        self.assertAlmostEqual(weekly_total, 2.0, places=5, msg="42h - 40h = 2h weekly OT")

    def test_calendar_employee_cross_midnight_timezone(self):
        """Tokyo employee (UTC+9): midnight-crossing attendance attributed to Monday, 2h OT on Monday."""
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
        """Two deficit rules: lowest-sequence (3h deficit) wins; second rule (5h deficit) is suppressed."""
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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_atts), 1,
                         "Only the lowest-sequence deficit rule should produce an output")
        self.assertEqual(output_atts.work_entry_type_id, gap_type_a)
        self.assertAlmostEqual(output_atts.worked_hours, 3.0, places=5)

    def test_deficit_builds_and_clears_with_incremental_attendances(self):
        """Incremental attendance: 4h deficit -> manually delete output, +4h -> no deficit, +1h -> 1h OT (additive-only)."""
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

        def _deficit_hours():
            atts = self.env['hr.attendance'].search([
                ('employee_id', '=', self.cal_emp.id),
                ('is_time_rule_output', '=', True),
                ('work_entry_type_id', '=', gap_type.id),
            ])
            return sum(a.worked_hours for a in atts)

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),
            'check_out': datetime(2022, 12, 12, 12),  # 4h
        })
        self.assertAlmostEqual(_deficit_hours(), 4.0, places=5, msg="4h worked -> 4h deficit")

        # deficit output occupies 13h-17h and would block the afternoon attendance
        # -> user must delete the stale output first (engine is additive-only)
        self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('work_entry_type_id', '=', gap_type.id),
        ]).with_context(skip_time_rules=True).unlink()

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 13),
            'check_out': datetime(2022, 12, 12, 17),  # +4h = 8h total
        })
        self.assertAlmostEqual(_deficit_hours(), 0.0, places=5,
                               msg="8h worked -> no deficit output created")

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 17),
            'check_out': datetime(2022, 12, 12, 18),  # +1h = 9h total
        })
        self.assertAlmostEqual(_deficit_hours(), 0.0, places=5, msg="9h worked -> no deficit, only OT")
        ot_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('work_entry_type_id', '=', self.overtime_type.id),
        ])
        ot_hours = sum(a.worked_hours for a in ot_atts)
        self.assertAlmostEqual(ot_hours, 1.0, places=5, msg="1h excess -> 1h overtime output")

    def test_calendar_employee_overtime_spanning_midnight(self):
        """Fri-Sat midnight crossing: Fri 8h OT + Sat 3h OT = 11h total."""
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

    def test_midnight_crossing_with_same_day_followup(self):
        self.env['hr.attendance'].create([
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 12, 22, 0),   # Monday
                'check_out': datetime(2022, 12, 13, 10, 0),   # Tuesday
            },
            {
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, 13, 14, 0),
                'check_out': datetime(2022, 12, 13, 18, 0),
            },
        ])
        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 13))
        monday_ot = [v for v in vals if v['date'] == date(2022, 12, 12) and v['work_entry_type_id'] == self.overtime_type]
        self.assertFalse(monday_ot, "2h worked on Mon (below 8h schedule) must not produce overtime")
        tuesday_ot = [v for v in vals if v['date'] == date(2022, 12, 13) and v['work_entry_type_id'] == self.overtime_type]
        self.assertAlmostEqual(
            sum(v['duration'] for v in tuesday_ot), 6.0, places=5,
            msg="midnight-10:00 (10h) + 14:00-18:00 (4h) - 8h schedule = 6h OT on Tue",
        )

    def test_total_overtime_reflects_output_attendances(self):

        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 10, 11),   # Saturday
            'check_out': datetime(2022, 12, 10, 17),   # 6h, no schedule -> 6h OT
        })
        self.cal_emp.invalidate_recordset(['total_overtime'])
        self.assertAlmostEqual(self.cal_emp.total_overtime, 6.0, places=5,
                               msg="6h on Saturday -> 6h OT output -> total_overtime=6")

    @unittest.skip("cross-trigger (absence leave validated -> time rule re-evaluate) not yet implemented")
    def test_overtime_fires_when_absence_leave_approved(self):
        """Approving an absence leave on a worked day triggers overtime; refusing clears it."""
        pass

    def test_get_attendance_data_worked_hours_and_overtime_hours(self):
        """Jan: 11h Fri + 16h Sat = 27h worked, 3h+16h = 19h OT; Feb attendance outside window excluded."""
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
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        ot_duration = sum(a.worked_hours for a in output_atts)
        self.assertAlmostEqual(ot_duration, 6.0, places=5,
                               msg="working_time leave does not reduce the time rule's expected hours")

        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))

        self._check_work_entries(vals, [
            (date(2022, 12, 12), 2, self.att_type),
            (date(2022, 12, 12), 9, wt_type),
            (date(2022, 12, 12), 3, self.overtime_type),
        ])

    def _ot_hours_on_day(self, employee, day):
        """Sum of output-attendance hours whose check_in falls on `day` (datetime.date)."""
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        atts = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('is_time_rule_output', '=', True),
            ('check_in', '>=', day_start),
            ('check_in', '<', day_end),
        ])
        return sum(a.worked_hours for a in atts)

    def test_public_holiday_create_does_not_clear_overtime(self):
        """Adding a PH after OT exists leaves OT stale (additive-only; no cleanup on re-eval)."""
        self.time_rule.apply_on_public_holidays = False
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PHCLEAR', 'count_as': 'absence',
        })
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 12)), 6.0, places=5,
            msg="6h OT before PH is added",
        )
        self._make_public_holiday(
            datetime(2022, 12, 12, 0, 0, 0), datetime(2022, 12, 12, 23, 59, 59), public_type,
        )
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 12)), 6.0, places=5,
            msg="OT output persists (stale) after PH added; engine does not delete existing outputs",
        )

    def test_public_holiday_unlink_restores_overtime(self):
        """Deleting a PH triggers re-evaluation and creates fresh 6h OT output."""
        self.time_rule.apply_on_public_holidays = False
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PHRESTORE', 'count_as': 'absence',
        })
        ph = self._make_public_holiday(
            datetime(2022, 12, 12, 0, 0, 0), datetime(2022, 12, 12, 23, 59, 59), public_type,
        )
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 12)), 0.0, places=5,
            msg="No OT while PH active and rule excludes PHs",
        )
        ph.unlink()
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 12)), 6.0, places=5,
            msg="6h OT restored after PH deleted",
        )

    def test_public_holiday_write_date_shifts_overtime(self):
        """Moving a PH between worked days doesn't change existing OT (additive-only; no cleanup on re-eval)."""
        self.time_rule.apply_on_public_holidays = False
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PHSHIFT', 'count_as': 'absence',
        })
        for day in (12, 13):
            self.env['hr.attendance'].create({
                'employee_id': self.cal_emp.id,
                'check_in': datetime(2022, 12, day, 6),
                'check_out': datetime(2022, 12, day, 20),
            })
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 12)), 6.0, places=5,
            msg="Mon: 6h OT before PH",
        )
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 13)), 6.0, places=5,
            msg="Tue: 6h OT before PH",
        )

        ph = self._make_public_holiday(
            datetime(2022, 12, 12, 0, 0, 0), datetime(2022, 12, 12, 23, 59, 59), public_type,
        )
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 12)), 6.0, places=5,
            msg="Mon OT persists (stale) despite PH; engine does not clear existing outputs",
        )
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 13)), 6.0, places=5,
            msg="Tue OT unaffected by Mon PH",
        )

        ph.write({
            'date_from': datetime(2022, 12, 13, 0, 0, 0),
            'date_to': datetime(2022, 12, 13, 23, 59, 59),
        })
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 12)), 6.0, places=5,
            msg="Mon OT persists (stale) after PH moved to Tue",
        )
        self.assertAlmostEqual(
            self._ot_hours_on_day(self.cal_emp, date(2022, 12, 13)), 6.0, places=5,
            msg="Tue OT persists (stale) after PH moved there; engine does not clear existing outputs",
        )

    def test_public_holiday_update_after_time_rule_output(self):
        """Regression: updating a PH when OT output attendances exist must not crash."""
        public_type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday', 'code': 'PHUPDATE', 'count_as': 'absence',
        })
        # Monday 2022-12-12: employee works 14h -> 6h overtime output leave created
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        output_before = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_before), 1,
                         "Overtime output attendance should exist before PH update")

        # Create a public holiday on that same day, then update it
        ph = self._make_public_holiday(
            datetime(2022, 12, 12, 0, 0, 0), datetime(2022, 12, 12, 23, 59, 59), public_type,
        )
        ph.write({'name': 'Updated Holiday'})   # this must not raise

    def test_attendance_before_working_time_leave_overlapping(self):
        self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),  # 14h -> 6h OT output created
        })
        output_before = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_before), 1, "Attendance should produce one OT output attendance")

        # must not raise despite overlapping with the attendance.
        _, wt_type = self._make_working_time_leave(
            datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 17),
        )
        wt_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('work_entry_type_id', '=', wt_type.id),
        ])
        self.assertEqual(len(wt_leaves), 1, "working_time leave created successfully alongside OT output")
        output_after = self.env['hr.attendance'].search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertEqual(len(output_after), 1,
                         "OT output attendance unaffected by working_time leave creation")

        vals = self.cal_version.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12))
        self._check_work_entries(vals, [
            (date(2022, 12, 12), 2, self.att_type),
            (date(2022, 12, 12), 9, wt_type),
            (date(2022, 12, 12), 3, self.overtime_type),
        ])

    def test_multiple_attendances_overtime_spanning_utc_day(self):
        """Brussels employee: two back-to-back Sat attendances -> 10h Sat OT + 2h Sun OT."""
        emp = self.env['hr.employee'].create({
            'name': 'Brussels Overtime Employee',
            'tz': 'Europe/Brussels',
            'attendance_based': False,
            'resource_calendar_id': self.calendar.id,
            'date_version': '2026-01-01',
            'contract_date_start': '2026-01-01',
            'wage': 3000,
        })
        self.env['hr.attendance'].create([{
            'employee_id': emp.id,
            'check_in': datetime(2026, 4, 11, 12, 0, 0),
            'check_out': datetime(2026, 4, 11, 18, 0, 0),
        }, {
            'employee_id': emp.id,
            'check_in': datetime(2026, 4, 11, 18, 0, 0),
            'check_out': datetime(2026, 4, 12, 0, 0, 0),
        }])

        vals = emp.version_id.generate_work_entries(date(2026, 4, 11), date(2026, 4, 12))
        vals = [v for v in vals if v['duration'] > 0]

        sat_total = sum(v['duration'] for v in vals if v['date'] == date(2026, 4, 11))
        sun_total = sum(v['duration'] for v in vals if v['date'] == date(2026, 4, 12))

        self.assertAlmostEqual(sat_total, 10.0, places=5,
            msg="Saturday Brussels: att0 6h + att1 Sat portion 4h = 10h overtime (0h schedule)")
        self.assertAlmostEqual(sun_total, 2.0, places=5,
            msg="Sunday Brussels: att1 Sun portion 00:00-02:00 Brussels = 2h overtime (0h schedule)")

        # check the output attendances
        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', emp.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertTrue(
            all(a.work_entry_type_id == self.overtime_type for a in output_atts),
            "All output attendances must be of the overtime type",
        )
        total_ot = sum(a.worked_hours for a in output_atts)
        self.assertAlmostEqual(total_ot, 12.0, places=5,
            msg="Total output attendance hours: 10h Sat + 2h Sun = 12h")

        # Saturday Brussels = [2026-04-10 22:00 UTC, 2026-04-11 22:00 UTC)
        sat_atts = output_atts.filtered(
            lambda a: datetime(2026, 4, 10, 22) <= a.check_in < datetime(2026, 4, 11, 22)
        )
        sat_ot = sum(a.worked_hours for a in sat_atts)
        self.assertAlmostEqual(sat_ot, 10.0, places=5,
            msg="Output attendances attributed to Saturday Brussels must total 10h")

        # Sunday Brussels = [2026-04-11 22:00 UTC, 2026-04-12 22:00 UTC)
        sun_atts = output_atts.filtered(
            lambda a: datetime(2026, 4, 11, 22) <= a.check_in < datetime(2026, 4, 12, 22)
        )
        sun_ot = sum(a.worked_hours for a in sun_atts)
        self.assertAlmostEqual(sun_ot, 2.0, places=5,
            msg="Output attendances attributed to Sunday Brussels must total 2h")

        # the Sunday Brussels output must end at exactly UTC midnight
        self.assertTrue(
            any(a.check_out == datetime(2026, 4, 12, 0, 0, 0) for a in sun_atts),
            "The Sunday Brussels output attendance must end at 00:00 UTC Apr 12",
        )

    def test_auto_check_out_employee_time_off(self):
        """Auto-check-out with personal leave (15:00-17:00): check_out trimmed, 0.1h OT output created."""
        Attendance = self.env['hr.attendance']
        company = self.env.company
        company.write({'auto_check_out': True, 'auto_check_out_tolerance': 0.1})

        # personal resource leave 15:00-17:00 UTC on 2024-01-01 (Monday)
        # count_as defaults to 'absence', so the time rule deducts it from the schedule
        self.env['resource.calendar.leaves'].create({
            'name': 'Time Off',
            'calendar_id': self.calendar.id,
            'resource_id': self.cal_emp.resource_id.id,
            'date_from': datetime(2024, 1, 1, 15, 0),
            'date_to': datetime(2024, 1, 1, 17, 0),
        })

        attendance = Attendance.create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2024, 1, 1, 8, 0),
        })

        with freeze_time('2024-01-01 17:06:00'):
            Attendance._cron_auto_check_out()

        output_atts = Attendance.search([
            ('employee_id', '=', self.cal_emp.id),
            ('is_time_rule_output', '=', True),
            ('check_in', '>=', datetime(2024, 1, 1)),
            ('check_in', '<', datetime(2024, 1, 2)),
        ])
        self.assertAlmostEqual(
            sum(a.worked_hours for a in output_atts), 0.1, places=4,
            msg="Time rule should generate 0.1h overtime output attendance",
        )
        all_atts = Attendance.search([
            ('employee_id', '=', self.cal_emp.id),
            ('check_in', '>=', datetime(2024, 1, 1)),
            ('check_in', '<', datetime(2024, 1, 2)),
        ])
        self.assertAlmostEqual(
            sum(a.worked_hours for a in all_atts), 6.1, places=4,
            msg="Total attendance (source + output) should equal 6.1h",
        )
        self.assertEqual(
            attendance.check_in, datetime(2024, 1, 1, 8, 0),
            "Source attendance check_in must be unchanged",
        )

    def test_two_quantity_rules_priority(self):
        """Seq=10 rule (>4h) claims 1h as type2; seq=20 rule (any-hours) claims remaining 4h as type1."""
        self.time_rule.write({'active': False})

        type1 = self.env['hr.work.entry.type'].create({'name': 'OT Base', 'code': 'TSTOTP1'})
        type2 = self.env['hr.work.entry.type'].create({'name': 'OT Premium', 'code': 'TSTOTP2'})

        # seq=10 -> fires first; expected_hours=4 (has_threshold=True) -> excess above 4h -> type2
        self.env['hr.time.rule'].create({
            'name': 'Above 4h',
            'working_hours_mode': 'day',
            'expected_hours': 4,
            'work_entry_type_id': type2.id,
            'condition_work_entry_type_ids': [self.att_type.id],
            'sequence': 10,
        })
        # seq=20 -> fires second; expected_hours=0 (has_threshold=False) -> reclassifies remaining att_type -> type1
        self.env['hr.time.rule'].create({
            'name': 'Any OT',
            'working_hours_mode': 'day',
            'expected_hours': 0,
            'work_entry_type_id': type1.id,
            'condition_work_entry_type_ids': [self.att_type.id],
            'sequence': 20,
        })

        # batch create: engine evaluates both attendances together (5h combined)
        self.env['hr.attendance'].create([
            {
                'employee_id': self.flex_emp.id,
                'check_in': datetime(2022, 12, 12, 8),
                'check_out': datetime(2022, 12, 12, 11),  # 3h
            },
            {
                'employee_id': self.flex_emp.id,
                'check_in': datetime(2022, 12, 12, 12),
                'check_out': datetime(2022, 12, 12, 14),  # 2h
            },
        ])

        # sources may be type-changed in-place (is_time_rule_output=True but no child link)
        all_outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', self.flex_emp.id),
            ('is_time_rule_output', '=', True),
            ('check_in', '>=', datetime(2022, 12, 12, 0)),
            ('check_out', '<=', datetime(2022, 12, 13, 0)),
        ])
        type1_hours = sum(a.worked_hours for a in all_outputs if a.work_entry_type_id == type1)
        type2_hours = sum(a.worked_hours for a in all_outputs if a.work_entry_type_id == type2)

        self.assertAlmostEqual(type1_hours, 4.0, places=5,
            msg="4h classified by 'Any OT' rule (hours at or below the 4h mark)")
        self.assertAlmostEqual(type2_hours, 1.0, places=5,
            msg="1h classified by 'Above 4h' rule (the hour exceeding the threshold)")

    def test_excess_day1_deficit_day2_two_rules(self):
        """att1 Mon 8-18: 2h OT child. att2 Mon 22-Tue 6: Mon tail repurposed in-place as 2h OT, Tue gets 2h deficit output."""
        undertime_type = self.env['hr.work.entry.type'].create({
            'name': 'Undertime', 'code': 'EXDEF_UT', 'count_as': 'absence', 'requires_allocation': False,
        })
        deficit_rule = self.env['hr.time.rule'].create({
            'name': 'Deficit Rule',
            'threshold_operator': 'less_than',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': undertime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        att1 = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 8),   # Mon
            'check_out': datetime(2022, 12, 12, 18),  # Mon 18:00 - 10h, 2h above threshold
        })
        att2 = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 12, 12, 22),   # Mon 22:00
            'check_out': datetime(2022, 12, 13, 6),   # Tue 06:00
        })

        att1_ot = att1.overtime_attendance_ids.filtered(
            lambda a: a.time_rule_id == self.time_rule
        )
        att2_deficit = att2.overtime_attendance_ids.filtered(
            lambda a: a.time_rule_id == deficit_rule
        )

        self.assertAlmostEqual(
            sum(a.worked_hours for a in att1_ot), 2.0, places=5,
            msg="att1: 10h worked, 8h threshold -> 2h OT child",
        )
        # att2's Mon portion (22:00-24:00) is the 2h excess tail (Mon ATT total = att1(8h)+att2(2h)=10h)
        # -> att2 repurposed in-place as 2h OT; no separate OT child linked to att2
        att2.invalidate_recordset()
        self.assertEqual(att2.work_entry_type_id, self.overtime_type,
                         "att2 type-changed in-place: Mon 22:00-24:00 is the 2h OT tail")
        self.assertEqual(att2.time_rule_id, self.time_rule)
        self.assertAlmostEqual(att2.worked_hours, 2.0, places=5,
                               msg="att2 now spans 22:00-24:00 (2h)")
        self.assertAlmostEqual(
            sum(a.worked_hours for a in att2_deficit), 2.0, places=5,
            msg="att2 Tue portion (00:00-06:00, 6h) < 8h threshold -> 2h deficit output",
        )

    def test_overtime_duration_precision(self):
        # 5-second overtime must not be truncated by pipeline or generate_work_entries.
        self.time_rule.write({'active': False})
        self.env['hr.time.rule'].create({
            'name': 'Precision Rule 9h',
            'working_hours_mode': 'day',
            'expected_hours': 9.0,
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        att = self.env['hr.attendance'].create({
            'employee_id': self.cal_emp.id,
            'check_in': datetime(2022, 1, 3, 8, 0, 0),
            'check_out': datetime(2022, 1, 3, 17, 0, 5),
        })

        expected_ot_hours = 5 / 3600  # 0.001388..

        # pipeline output: source trimmed to 9 h; OT child holds the 5-second tail
        ot_atts = att.overtime_attendance_ids.filtered(
            lambda a: a.work_entry_type_id == self.overtime_type
        )
        self.assertAlmostEqual(
            sum(a.worked_hours for a in ot_atts), expected_ot_hours, places=5,
            msg="5-second OT must survive the pipeline without being rounded to zero",
        )

        # payslip path: generate_work_entries must also carry the 5-second OT entry
        vals = self.cal_version.generate_work_entries(date(2022, 1, 3), date(2022, 1, 3))
        ot_total = sum(v['duration'] for v in vals if v['work_entry_type_id'] == self.overtime_type)
        self.assertAlmostEqual(
            ot_total, expected_ot_hours, places=5,
            msg="generate_work_entries must not truncate 5-second OT to zero",
        )
        # sanity: the source work entry must carry exactly 9 h
        att_total = sum(v['duration'] for v in vals if v['work_entry_type_id'] == self.att_type)
        self.assertAlmostEqual(att_total, 9.0, places=5)

    def test_multiple_overlapping_overtimes_rounding(self):
        """Brussels midnight crossing with weekday+weekend rules: Fri 2h30m28s OT + Sat 1h29m44s OT."""
        self.time_rule.active = False

        weekday_ot_type = self.env['hr.work.entry.type'].create({
            'name': 'Weekday Overtime', 'code': 'WDOTR', 'requires_allocation': False,
        })
        weekend_ot_type = self.env['hr.work.entry.type'].create({
            'name': 'Weekend Overtime', 'code': 'WEOTR', 'requires_allocation': False,
        })
        self.env['hr.time.rule'].create({
            'name': 'Weekday Rule',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'apply_saturday': False,
            'apply_sunday': False,
            'work_entry_type_id': weekday_ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        self.env['hr.time.rule'].create({
            'name': 'Weekend Rule',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'apply_monday': False,
            'apply_tuesday': False,
            'apply_wednesday': False,
            'apply_thursday': False,
            'apply_friday': False,
            'work_entry_type_id': weekend_ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })

        emp = self.env['hr.employee'].create({
            'name': 'Brussels Employee',
            'tz': 'Europe/Brussels',
            'attendance_based': False,
            'resource_calendar_id': self.calendar.id,
            'date_version': '2026-01-01',
            'contract_date_start': '2026-01-01',
            'wage': 3500,
        })
        att = self.env['hr.attendance'].create({
            'employee_id': emp.id,
            'check_in': datetime(2026, 1, 23, 12, 29, 32),
            'check_out': datetime(2026, 1, 24, 0, 29, 44),
        })

        weekday_ot = att.overtime_attendance_ids.filtered(
            lambda a: a.work_entry_type_id == weekday_ot_type
        )
        weekend_ot = att.overtime_attendance_ids.filtered(
            lambda a: a.work_entry_type_id == weekend_ot_type
        )
        self.assertAlmostEqual(
            sum(a.worked_hours for a in weekday_ot), 9028 / 3600, places=4,
            msg="2h 30m 28s weekday OT on Friday (Brussels)",
        )
        self.assertAlmostEqual(
            sum(a.worked_hours for a in weekend_ot), 5384 / 3600, places=4,
            msg="1h 29m 44s weekend OT on Saturday (Brussels)",
        )


@tagged('-at_install', 'post_install', 'work_entry_pipeline')
class TestTimeRuleCronBehavior(TransactionCase):
    """
    Attendances recorded today are not processed immediately, the daily cron handles them the next morning.
    Past-dated attendances (retroactive entry or modification) re-trigger immediately so outputs stay consistent.
    Day and week crons are independent: each fires only its own rule period and leaves the other's outputs untouched.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.calendar = cls.env['resource.calendar'].create({
            'name': '40h/week (cron tests)',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar
        cls.att_type = cls.env.company._get_default_attendance_work_entry_type()
        cls.env.company.attendance_work_entry_type_id = cls.att_type

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.day_ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Daily OT (cron)', 'code': 'CRNDAYOT', 'requires_allocation': False,
            'request_unit': 'hour',
        })
        cls.week_ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Weekly OT (cron)', 'code': 'CRNWKOT', 'requires_allocation': False,
            'request_unit': 'hour',
        })

        cls.emp = cls.env['hr.employee'].create({
            'name': 'Cron Test Employee',
            'tz': 'UTC',
            'attendance_based': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3500,
        })

    def _outputs_for(self, att_id, ot_type=None):
        att = self.env['hr.attendance'].browse(att_id)
        # in-place repurpose: the source itself is the output (time_rule_id set, no source link)
        if att.is_time_rule_output and not att.source_attendance_id:
            all_outputs = att
            if ot_type:
                all_outputs = all_outputs.filtered(lambda a: a.work_entry_type_id == ot_type)
            return all_outputs
        # separate child records created by the pipeline
        direct = self.env['hr.attendance'].search([
            ('source_attendance_id', '=', att_id),
            ('is_time_rule_output', '=', True),
        ])
        # one level deeper (e.g. week-OT whose source is a day-OT child of att)
        indirect = self.env['hr.attendance'].search([
            ('source_attendance_id', 'in', direct.ids),
            ('is_time_rule_output', '=', True),
        ]) if direct else self.env['hr.attendance']
        all_outputs = direct | indirect
        if ot_type:
            all_outputs = all_outputs.filtered(lambda a: a.work_entry_type_id == ot_type)
        return all_outputs

    def test_today_attendance_deferred_to_day_cron(self):
        """Today's attendance with expected_hours=0 creates output immediately (all hours are excess)."""
        rule = self.env['hr.time.rule'].create({
            'name': 'All hours -> daily OT',
            'working_hours_mode': 'day',
            'expected_hours': 0,
            'work_entry_type_id': self.day_ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        try:
            with freeze_time('2022-12-12'):
                att = self.env['hr.attendance'].create({
                    'employee_id': self.emp.id,
                    'check_in': datetime(2022, 12, 12, 8),
                    'check_out': datetime(2022, 12, 12, 14),  # 6h
                })

                outputs = self._outputs_for(att.id)
                self.assertTrue(outputs, "overtime output should be created immediately")
                self.assertAlmostEqual(
                    sum(o.worked_hours for o in outputs), 6.0, places=5,
                    msg="all 6h reclassified to daily OT",
                )
        finally:
            rule.write({'active': False})

    def test_day_and_week_cron_independence_overtime_attendance(self):
        day_rule = self.env['hr.time.rule'].create({
            'name': 'Daily > 4h',
            'working_hours_mode': 'day',
            'expected_hours': 4,
            'work_entry_type_id': self.day_ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        week_rule = self.env['hr.time.rule'].create({
            'name': 'Weekly > 5h',
            'working_hours_mode': 'week',
            'expected_hours': 5,
            'work_entry_type_id': self.week_ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id, self.day_ot_type.id],
        })
        try:
            with freeze_time('2022-12-12'):
                att = self.env['hr.attendance'].create({
                    'employee_id': self.emp.id,
                    'check_in': datetime(2022, 12, 12, 8),
                    'check_out': datetime(2022, 12, 12, 14),  # 6h
                })
                day_h = sum(o.worked_hours for o in self._outputs_for(att.id, self.day_ot_type))
                week_h = sum(o.worked_hours for o in self._outputs_for(att.id, self.week_ot_type))
                self.assertAlmostEqual(day_h, 2.0, places=5, msg="2h daily OT created immedaitely")
                self.assertAlmostEqual(week_h, 0.0, places=5, msg="week rules wait for the cron")

            with freeze_time('2022-12-19'):
                # Mon 2022-12-19: week cron processes Mon 12 - Sun 18.
                self.env['hr.attendance']._cron_process_week_time_rules()

            day_h = sum(o.worked_hours for o in self._outputs_for(att.id, self.day_ot_type))
            week_h = sum(o.worked_hours for o in self._outputs_for(att.id, self.week_ot_type))
            self.assertAlmostEqual(day_h, 1.0, places=5,
                msg="Day OT cut by weekly rule (last 1 hour is converted into weekly overtime)")
            self.assertAlmostEqual(week_h, 1.0, places=5,
                msg="1h weekly OT by week cron (6h - 5h threshold)")
        finally:
            day_rule.write({'active': False})
            week_rule.write({'active': False})

    def test_retroactive_attendance_triggers_immediate_reprocess(self):
        rule = self.env['hr.time.rule'].create({
            'name': 'All hours -> daily OT (retro)',
            'working_hours_mode': 'day',
            'expected_hours': 0,
            'work_entry_type_id': self.day_ot_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
        })
        try:
            # date.today() is well past 2022-12-12 -> create() triggers immediately
            att = self.env['hr.attendance'].create({
                'employee_id': self.emp.id,
                'check_in': datetime(2022, 12, 12, 8),
                'check_out': datetime(2022, 12, 12, 14),  # 6h
            })
            outputs = self._outputs_for(att.id)
            self.assertTrue(outputs, "Past-date attendance should produce output immediately")
            self.assertAlmostEqual(
                sum(o.worked_hours for o in outputs), 6.0, places=5,
            )
        finally:
            rule.write({'active': False})


@tagged('-at_install', 'post_install', 'work_entry_pipeline')
class TestTimeRulePipelineLeaves(TransactionCase):
    """Leave-based time rule pipeline tests.

    Covers create/write/validate/refuse triggers, the past-vs-today day split,
    current-week deferral for weekly rules, cron methods, and edge cases.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.src_type = cls.env['hr.work.entry.type'].create({
            'name': 'Leave Src (pipeline)', 'code': 'LVSRC',
            'count_as': 'absence', 'requires_allocation': False, 'time_off_selectable': False,
            'request_unit': 'hour',
        })
        cls.out_type = cls.env['hr.work.entry.type'].create({
            'name': 'Leave Out (pipeline)', 'code': 'LVOUT',
            'count_as': 'absence', 'requires_allocation': False, 'time_off_selectable': False,
            'request_unit': 'hour',
        })

        cls.emp = cls.env['hr.employee'].create({
            'name': 'Leave Pipeline Employee',
            'tz': 'UTC',
            'attendance_based': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })

    def _make_leave(self, date_from_dt, date_to_dt, *, state='validate', skip_rules=False, emp=None, wet=None):
        ctx = dict(leave_fast_create=True, leave_exact_dates=True, leave_skip_state_check=True)
        if skip_rules:
            ctx['skip_time_rules'] = True
        leave = self.env['hr.leave'].with_context(**ctx).sudo().create({
            'employee_id': (emp or self.emp).id,
            'work_entry_type_id': (wet or self.src_type).id,
            'date_from': date_from_dt,
            'date_to': date_to_dt,
            'request_date_from': date_from_dt.date(),
            'request_date_to': date_to_dt.date(),
            'state': state,
        })
        return leave.with_context({})

    def _outputs(self, leave, out_type=None):
        domain = [('source_leave_id', '=', leave.id)]
        if out_type:
            domain.append(('work_entry_type_id', '=', out_type.id))
        return self.env['hr.leave'].sudo().search(domain)

    def _output_hours(self, leave, out_type=None):
        return sum((l.date_to - l.date_from).total_seconds() / 3600 for l in self._outputs(leave, out_type))

    def test_past_leave_exceed_creates_output(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h/day',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))  # 6h past
            self.assertAlmostEqual(self._output_hours(leave), 2.0, places=5,
                                   msg="6h leave with 4h threshold -> 2h output")
        finally:
            rule.write({'active': False})

    def test_past_leave_less_than_creates_output(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Less than 8h/day',
            'working_hours_mode': 'day',
            'threshold_operator': 'less_than',
            'expected_hours': 8,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))  # 6h past
            self.assertTrue(self._outputs(leave), "Past leave with less_than rule must produce output")
        finally:
            rule.write({'active': False})

    def test_fixed_threshold_leave_alloc_only(self):
        """Allocate-only rule (no WET) with fixed 2h/day threshold: 3h leave -> 1h excess -> 0.125d allocated."""
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Comp Fixed Leave',
            'code': 'CFLV',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Alloc-only 2h/day leave',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 2.0,
            'work_entry_type_id': False,
            'condition_work_entry_type_ids': [self.src_type.id],
            'leave_compensation_rate': 1.0,
            'allocation_type_id': comp_type.id,
        })
        try:
            # 3h past leave: 2h fixed threshold -> 1h excess -> 0.125d allocated
            self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11))
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', self.emp.id),
                ('work_entry_type_id', '=', comp_type.id),
            ])
            self.assertEqual(len(allocation), 1,
                             "Allocation must be created for allocate-only leave rule with fixed threshold")
            self.assertAlmostEqual(
                allocation.number_of_days, 0.125, places=5,
                msg="1h excess * 100% / 8h/day = 0.125 comp days",
            )
        finally:
            rule.write({'active': False})

    def test_fixed_threshold_leave_alloc_with_premium_pay(self):
        """Fixed 2h/day leave rule: 3h leave -> 1h excess reclassified to output type + allocation.

        Premium pay variant for leaves: rule has both a WET (out_type) and an allocation_type_id.
        """
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'Comp Leave Premium',
            'code': 'CLPREM',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'OT+Alloc 2h/day leave',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 2.0,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
            'leave_compensation_rate': 0.5,
            'allocation_type_id': comp_type.id,
        })
        try:
            # 3h past leave: 2h threshold -> 1h excess -> output leave created + 0.0625d allocated
            source = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11))
            outputs = self._outputs(source)
            self.assertEqual(len(outputs), 1, "1h excess must produce one output leave")
            self.assertAlmostEqual(
                (outputs.date_to - outputs.date_from).total_seconds() / 3600, 1.0, places=5,
                msg="Output leave must span exactly 1h",
            )
            self.assertEqual(outputs.work_entry_type_id, self.out_type,
                             "Output leave classified to out_type (premium pay WET)")
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', self.emp.id),
                ('work_entry_type_id', '=', comp_type.id),
            ])
            self.assertEqual(len(allocation), 1,
                             "Allocation must be created alongside the output leave")
            self.assertAlmostEqual(
                allocation.number_of_days, 0.0625, places=5,
                msg="1h excess * 50% / 8h/day = 0.0625 comp days",
            )
        finally:
            rule.write({'active': False})

    def test_today_leave_exceed_fires_immediately(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h/day (today)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            with freeze_time('2022-12-12'):
                leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
                self.assertTrue(self._outputs(leave), "Today's exceed leave must fire immediately")
                self.assertAlmostEqual(self._output_hours(leave), 2.0, places=5)
        finally:
            rule.write({'active': False})

    def test_today_leave_less_than_deferred(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Less than 8h/day (today)',
            'working_hours_mode': 'day',
            'threshold_operator': 'less_than',
            'expected_hours': 8,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            with freeze_time('2022-12-12'):
                leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
                self.assertFalse(self._outputs(leave), "Today's less_than leave must be deferred")
        finally:
            rule.write({'active': False})

    def test_write_check_out_extended_triggers_reprocess(self):

        att_src_wet = self.env['hr.work.entry.type'].create({
            'name': 'Att Src (write extend)', 'code': 'ATSRCW', 'requires_allocation': False,
        })
        ot_type = self.env['hr.work.entry.type'].create({
            'name': 'Write Extend OT', 'code': 'LVWEXT', 'requires_allocation': False,
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (write extend att)',
            'working_hours_mode': 'day',
            'expected_hours': 4,
            'work_entry_type_id': ot_type.id,
            'condition_work_entry_type_ids': [att_src_wet.id],
        })
        try:
            att = self.env['hr.attendance'].with_context(skip_time_rules=True).create({
                'employee_id': self.emp.id,
                'check_in': datetime(2022, 12, 12, 8),
                'check_out': datetime(2022, 12, 12, 12),  # 4h, at threshold, no excess
                'work_entry_type_id': att_src_wet.id,
                'state': 'validated',
            }).with_context(skip_time_rules=False)
            outputs = self.env['hr.attendance'].search([
                ('source_attendance_id', '=', att.id), ('is_time_rule_output', '=', True),
            ])
            self.assertFalse(outputs, "4h at 4h threshold: no excess")

            att.write({'check_out': datetime(2022, 12, 12, 16)})  # extend to 8h
            outputs = self.env['hr.attendance'].search([
                ('source_attendance_id', '=', att.id), ('is_time_rule_output', '=', True),
            ])
            self.assertAlmostEqual(
                sum(o.worked_hours for o in outputs), 4.0, places=5,
                msg="Extended to 8h -> 4h excess output",
            )
        finally:
            rule.write({'active': False})

    def test_write_date_extended_triggers_reprocess(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (write extend)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 12), skip_rules=True,  # 4h, no excess
            )
            self.assertFalse(self._outputs(leave), "4h at 4h threshold: no excess yet")

            leave.with_context(skip_time_rules=False, leave_exact_dates=True, leave_skip_state_check=True).sudo().write({
                'date_to': datetime(2022, 12, 12, 16),
                'request_date_to': date(2022, 12, 12),
            })
            self.assertAlmostEqual(self._output_hours(leave), 4.0, places=5,
                                   msg="Extended to 8h -> 4h excess output")
        finally:
            rule.write({'active': False})

    def test_two_leaves_same_day_aggregate(self):
        """Two leaves 2h+3h on same day: last 1h of leave_b is excess above 4h threshold."""
        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h/day (aggregate)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave_a = self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 10), skip_rules=True,  # 2h
            )
            leave_b = self._make_leave(
                datetime(2022, 12, 12, 10), datetime(2022, 12, 12, 13),  # 3h, triggers rules
            )
            self.assertFalse(self._outputs(leave_a), "Leave A (2h) stays under threshold")
            self.assertAlmostEqual(self._output_hours(leave_b), 1.0, places=5,
                                   msg="Leave B's last 1h is the excess above 4h threshold")
        finally:
            rule.write({'active': False})

    def test_write_state_validate_triggers_rules(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (state write)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14), state='confirm',
            )
            self.assertFalse(self._outputs(leave), "Confirmed leave has no outputs")

            leave.sudo().with_context(leave_skip_state_check=True).write({'state': 'validate'})
            self.assertTrue(self._outputs(leave), "write(state='validate') must trigger rules")
        finally:
            rule.write({'active': False})

    def test_refuse_leaves_outputs_as_stale(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (refuse)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
            self.assertTrue(self._outputs(leave), "Output must exist after validation")

            leave.sudo().action_refuse()
            self.assertTrue(self._outputs(leave), "Outputs persist as stale after source is refused")
        finally:
            rule.write({'active': False})

    def test_output_leaves_not_reprocessed(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (no recurse)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id, self.out_type.id],
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
            first_level = self._outputs(leave)
            self.assertTrue(first_level, "Source leave must produce outputs")
            for out in first_level:
                self.assertFalse(
                    self._outputs(out),
                    "Output leave must not produce nested outputs",
                )
        finally:
            rule.write({'active': False})

    def test_no_active_rule_no_output(self):

        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
        self.assertFalse(self._outputs(leave), "No active rule: no output must be created")

    def test_weekly_rule_past_complete_week_fires(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Week exceed 20h',
            'working_hours_mode': 'week',
            'threshold_operator': 'exceed',
            'expected_hours': 20,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            # Mon 2022-12-12 to Fri 2022-12-16 (past complete week): 5 days x 6h = 30h > 20h
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 16, 14))
            self.assertTrue(self._outputs(leave), "Weekly rule must fire for past complete-week leave")
        finally:
            rule.write({'active': False})

    def test_weekly_rule_current_week_deferred(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Week exceed 20h (deferred)',
            'working_hours_mode': 'week',
            'threshold_operator': 'exceed',
            'expected_hours': 20,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            with freeze_time('2022-12-14'):  # Wednesday inside Mon Dec 12 - Sun Dec 18
                leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 14, 14))
                self.assertFalse(self._outputs(leave), "Weekly rule must defer for current-week leave")
        finally:
            rule.write({'active': False})

    def test_day_cron_processes_yesterday_undertime(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Less than 8h (day cron)',
            'working_hours_mode': 'day',
            'threshold_operator': 'less_than',
            'expected_hours': 8,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            with freeze_time('2022-12-12'):
                leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
                self.assertFalse(self._outputs(leave), "Today's less_than leave deferred")

            with freeze_time('2022-12-13'):
                self.env['hr.leave']._cron_process_day_undertime_rules()

            self.assertTrue(self._outputs(leave), "Day cron must process yesterday's undertime leave")
        finally:
            rule.write({'active': False})

    def test_week_cron_processes_past_week(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Week exceed 20h (week cron)',
            'working_hours_mode': 'week',
            'threshold_operator': 'exceed',
            'expected_hours': 20,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            with freeze_time('2022-12-14'):  # Wednesday, current week Mon Dec 12-Sun Dec 18
                leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 14, 14))  # ~30h
                self.assertFalse(self._outputs(leave), "Weekly rule deferred during current week")

            with freeze_time('2022-12-19'):  # Monday: Dec 12-18 week is now complete
                self.env['hr.leave']._cron_process_week_time_rules()

            self.assertTrue(self._outputs(leave), "Week cron must fire for just-ended week's leave")
        finally:
            rule.write({'active': False})

    def test_skip_time_rules_context_prevents_trigger(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (skip ctx)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14), skip_rules=True,
            )
            self.assertFalse(self._outputs(leave), "skip_time_rules=True must prevent output creation")
        finally:
            rule.write({'active': False})

    def test_multiple_employees_independent_outputs(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (multi-emp)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        emp2 = self.env['hr.employee'].create({
            'name': 'Leave Pipeline Emp2',
            'tz': 'UTC',
            'attendance_based': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })
        try:
            leave1 = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))             # 6h
            leave2 = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11), emp=emp2)   # 3h

            self.assertAlmostEqual(self._output_hours(leave1), 2.0, places=5,
                                   msg="emp: 6h - 4h = 2h output")
            self.assertFalse(self._outputs(leave2), "emp2: 3h < 4h threshold, no output")
        finally:
            rule.write({'active': False})

    def test_sequential_rules_priority(self):
        """Rule1 (seq=10, >4h) takes 4h; remaining 4h src < 6h Rule2 threshold -> no Rule2 output."""
        out_type2 = self.env['hr.work.entry.type'].create({
            'name': 'Leave Out Seq2', 'code': 'LVOUTSEQ2',
            'count_as': 'absence', 'requires_allocation': False, 'time_off_selectable': False,
        })
        rule1 = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h/day (seq=10)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
            'sequence': 10,
        })
        rule2 = self.env['hr.time.rule'].create({
            'name': 'Exceed 6h/day (seq=20)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 6,
            'work_entry_type_id': out_type2.id,
            'condition_work_entry_type_ids': [self.src_type.id],
            'sequence': 20,
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 16))  # 8h
            # rule1 (seq=10): 8h - 4h = 4h → out_type  (hours 4-8 classified)
            # rule2 (seq=20): remaining src_type is hours 0-4 (4h) → 4h < 6h threshold → no excess
            self.assertAlmostEqual(self._output_hours(leave, self.out_type), 4.0, places=5,
                                   msg="Rule1 (seq=10): 8h - 4h = 4h output")
            self.assertAlmostEqual(self._output_hours(leave, out_type2), 0.0, places=5,
                                   msg="Rule2 (seq=20): remaining 4h < 6h threshold")
        finally:
            rule1.write({'active': False})
            rule2.write({'active': False})

    def test_day_and_week_cron_independence_undertime_leave(self):

        day_rule = self.env['hr.time.rule'].create({
            'name': 'Less than 8h/day (cron indep)',
            'working_hours_mode': 'day',
            'threshold_operator': 'less_than',
            'expected_hours': 8,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        out_type_week = self.env['hr.work.entry.type'].create({
            'name': 'Leave Week Out (indep)', 'code': 'LVWKINDEP',
            'count_as': 'absence', 'requires_allocation': False, 'time_off_selectable': False,
        })
        week_rule = self.env['hr.time.rule'].create({
            'name': 'Week exceed 3h (cron indep)',
            'working_hours_mode': 'week',
            'threshold_operator': 'exceed',
            'expected_hours': 3,
            'work_entry_type_id': out_type_week.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            with freeze_time('2022-12-12'):
                leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
                self.assertFalse(self._outputs(leave), "Today's undertime should wait for the day cron")

            with freeze_time('2022-12-13'):
                self.env['hr.leave']._cron_process_day_undertime_rules()

            self.assertTrue(self._outputs(leave, self.out_type), "Day cron must fire the undertime day rule")
            self.assertFalse(self._outputs(leave, out_type_week), "Day cron must not fire the week rule")

            with freeze_time('2022-12-19'):  # Monday: week Dec 12-18 complete
                self.env['hr.leave']._cron_process_week_time_rules()

            self.assertTrue(self._outputs(leave, out_type_week), "Week cron must fire the week rule")
            self.assertTrue(self._outputs(leave, self.out_type), "Week cron must not clear the day output")
        finally:
            day_rule.write({'active': False})
            week_rule.write({'active': False})

    def test_no_output_when_wet_not_in_conditions(self):

        other_type = self.env['hr.work.entry.type'].create({
            'name': 'Leave Other (pipeline)', 'code': 'LVOTHER',
            'count_as': 'absence', 'requires_allocation': False, 'time_off_selectable': False,
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (wrong WET)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],  # only src_type, not other_type
        })
        try:
            leave = self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14), wet=other_type,
            )
            self.assertFalse(self._outputs(leave), "Wrong WET: rule conditions not matched, no output")
        finally:
            rule.write({'active': False})

    def test_employee_domain_filters_out_employee(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (emp domain)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
            'employee_domain': '[("id", "=", -1)]',  # matches no employee
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
            self.assertFalse(self._outputs(leave), "Employee excluded by domain: no output must be created")
        finally:
            rule.write({'active': False})

    def test_source_entire_leave_is_excess(self):
        """expected_hours=0: entire leave is excess -> source repurposed in-place (no child, no archive)."""
        rule = self.env['hr.time.rule'].create({
            'name': 'All hours out (entire excess)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 0,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 13, 8), datetime(2022, 12, 13, 14))  # 6h
            leave.invalidate_recordset()
            self.assertTrue(leave.active, "Source stays active; repurposed in-place, not archived")
            self.assertEqual(leave.work_entry_type_id, self.out_type, "Source WET changed to output type")
            self.assertEqual(leave.time_rule_id, rule, "Source time_rule_id set to the firing rule")
            self.assertFalse(leave.source_leave_id, "Source is still top-level (no source_leave_id)")
            self.assertFalse(leave.output_leave_ids, "No child records; source IS the output")
        finally:
            rule.write({'active': False})

    def test_second_leave_entirely_excess_type_changed(self):
        """leave_b starts exactly at the threshold point -> entirely excess -> type-changed in-place."""
        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 2h/day (two-leave type-change)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 2,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave_a = self._make_leave(
                datetime(2022, 12, 13, 8), datetime(2022, 12, 13, 10), skip_rules=True,  # 2h, exactly at threshold
            )
            leave_b = self._make_leave(  # triggers joint evaluation; leave_b start == threshold point
                datetime(2022, 12, 13, 10), datetime(2022, 12, 13, 12),
            )
            leave_b.invalidate_recordset()
            self.assertFalse(self._outputs(leave_a), "leave_a exactly at threshold: no excess, no child")
            self.assertEqual(leave_b.work_entry_type_id, self.out_type,
                             "leave_b entirely excess: type-changed in-place")
            self.assertEqual(leave_b.time_rule_id, rule)
            self.assertFalse(leave_b.source_leave_id)
            self.assertFalse(leave_b.output_leave_ids, "No children; leave_b IS the output")
        finally:
            rule.write({'active': False})

    def test_source_leave_unlink_output_child_remains(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h (unlink stale child)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 13, 8), datetime(2022, 12, 13, 14))  # 6h -> 2h child
            child = self._outputs(leave)
            self.assertEqual(len(child), 1, "One output child must exist before deletion")
            child_id = child.id

            leave.sudo().with_context(skip_time_rules=True).unlink()

            orphan = self.env['hr.leave'].sudo().search([('id', '=', child_id)])
            self.assertEqual(len(orphan), 1, "Output child survives source deletion as a stale orphan")
            self.assertFalse(orphan.source_leave_id, "source_leave_id nulled after parent deleted")
        finally:
            rule.write({'active': False})

    def test_user_leave_blocked_by_type_changed_output(self):

        rule = self.env['hr.time.rule'].create({
            'name': 'All hours out (overlap block)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 0,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 14, 8), datetime(2022, 12, 14, 14))
            leave.invalidate_recordset()
            self.assertEqual(leave.work_entry_type_id, self.out_type,
                             "Precondition: source type-changed in-place -> is_time_rule_output=True")

            with self.assertRaises(ValidationError):
                self._make_leave(datetime(2022, 12, 14, 8), datetime(2022, 12, 14, 14))
        finally:
            rule.write({'active': False})

    def test_day_and_week_cron_independence_undertime_attendance(self):

        src_wet = self.env['hr.work.entry.type'].create({
            'name': 'Att Src (day/week indep)', 'code': 'ATSRCINDEP', 'requires_allocation': False,
            'request_unit': 'hour',
        })
        day_out_type = self.env['hr.work.entry.type'].create({
            'name': 'Att Day Out (indep)', 'code': 'ATDAYINDEP', 'requires_allocation': False,
        })
        week_out_type = self.env['hr.work.entry.type'].create({
            'name': 'Att Week Out (indep)', 'code': 'ATWKINDEP', 'requires_allocation': False,
        })
        day_rule = self.env['hr.time.rule'].create({
            'name': 'Less than 8h/day (att cron indep)',
            'working_hours_mode': 'day',
            'threshold_operator': 'less_than',
            'expected_hours': 8,
            'work_entry_type_id': day_out_type.id,
            'condition_work_entry_type_ids': [src_wet.id],
        })
        week_rule = self.env['hr.time.rule'].create({
            'name': 'Week exceed 3h (att cron indep)',
            'working_hours_mode': 'week',
            'threshold_operator': 'exceed',
            'expected_hours': 3,
            'work_entry_type_id': week_out_type.id,
            'condition_work_entry_type_ids': [src_wet.id],
        })

        def _att_outputs(att, wet=None):
            domain = [('source_attendance_id', '=', att.id), ('is_time_rule_output', '=', True)]
            if wet:
                domain.append(('work_entry_type_id', '=', wet.id))
            return self.env['hr.attendance'].sudo().search(domain)

        try:
            with freeze_time('2022-12-12'):
                att = self.env['hr.attendance'].create({
                    'employee_id': self.emp.id,
                    'check_in': datetime(2022, 12, 12, 8),
                    'check_out': datetime(2022, 12, 12, 14),  # 6h, today: both rules deferred
                    'work_entry_type_id': src_wet.id,
                    'state': 'validated',
                })
                self.assertFalse(_att_outputs(att), "Today: both rules deferred")

            with freeze_time('2022-12-13'):
                self.env['hr.attendance']._cron_process_day_undertime_rules()

            self.assertTrue(_att_outputs(att, day_out_type), "Day cron must fire the day rule")
            self.assertFalse(_att_outputs(att, week_out_type), "Day cron must not fire the week rule")

            with freeze_time('2022-12-19'):  # Monday: week Dec 12-18 complete
                self.env['hr.attendance']._cron_process_week_time_rules()

            self.assertTrue(_att_outputs(att, week_out_type), "Week cron must fire the week rule")
            self.assertTrue(_att_outputs(att, day_out_type), "Week cron must not clear the day output")
        finally:
            day_rule.write({'active': False})
            week_rule.write({'active': False})

    def test_deficit_goes_around_non_matching_type_leave(self):
        """A validated leave that is invisible to the evaluator (wrong type, count_as=working_time)
        still blocks deficit placement; the engine routes around it in two separate output records."""
        cal = self.env['resource.calendar'].create({
            'name': 'Deficit Go-Around Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': str(d), 'hour_from': 8.0, 'hour_to': 14.0})
                for d in range(5)
            ],
        })
        emp = self.env['hr.employee'].create({
            'name': 'Deficit Go-Around Employee',
            'tz': 'UTC',
            'attendance_based': False,
            'resource_calendar_id': cal.id,
            'date_version': '2022-12-01',
            'contract_date_start': '2022-12-01',
            'wage': 3000,
        })
        blocker_type = self.env['hr.work.entry.type'].create({
            'name': 'Blocker (working_time, go-around)', 'code': 'BLKWGA',
            # count_as='working_time' → not subtracted from the schedule leave pool
            # → evaluator sees full expected_duration; go-around must still avoid it
            'count_as': 'working_time', 'requires_allocation': False,
        })
        undertime_type = self.env['hr.work.entry.type'].create({
            'name': 'Undertime (go-around)', 'code': 'UTGA',
            'count_as': 'absence', 'requires_allocation': False,
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Less than schedule (go-around)',
            'working_hours_mode': 'schedule_day',
            'threshold_operator': 'less_than',
            'work_entry_type_id': undertime_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 10),
                emp=emp, skip_rules=True,
            )
            blocker = self._make_leave(
                datetime(2022, 12, 12, 13), datetime(2022, 12, 12, 14),
                emp=emp, wet=blocker_type, skip_rules=True,
            )
            with freeze_time('2022-12-13'):
                self.env['hr.leave']._cron_process_day_undertime_rules()

            outputs = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', emp.id),
                ('work_entry_type_id', '=', undertime_type.id),
            ])
            total_hours = sum((o.date_to - o.date_from).total_seconds() / 3600 for o in outputs)
            self.assertAlmostEqual(total_hours, 2.0, places=5,
                                   msg="Full 2h deficit must be placed (split around the blocker)")
            self.assertEqual(len(outputs), 2,
                             "Two output records expected: one before and one after the blocker")
            for out in outputs:
                self.assertFalse(
                    out.date_from < blocker.date_to and out.date_to > blocker.date_from,
                    f"Output {out.date_from}-{out.date_to} must not overlap with blocker",
                )
        finally:
            rule.write({'active': False})

    def test_deficit_partial_fill_when_period_mostly_blocked(self):
        """When a blocker occupies part of the deficit interval and there is not enough
        free time left in the period, the engine places only what fits (partial fill)."""
        undertime_type = self.env['hr.work.entry.type'].create({
            'name': 'Undertime (partial)', 'code': 'UTPA',
            'count_as': 'absence', 'requires_allocation': False,
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Less than 3h/day (partial fill)',
            'working_hours_mode': 'day',
            'threshold_operator': 'less_than',
            'expected_hours': 3,
            'work_entry_type_id': undertime_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 9),
                skip_rules=True,  # 1h source → deficit=2h
            )
            # blocker (out_type, NOT in condition) blocks the first hour of the deficit interval
            self._make_leave(
                datetime(2022, 12, 12, 22), datetime(2022, 12, 12, 23),
                wet=self.out_type, skip_rules=True,
            )
            with freeze_time('2022-12-13'):
                self.env['hr.leave']._cron_process_day_undertime_rules()

            outputs = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', self.emp.id),
                ('work_entry_type_id', '=', undertime_type.id),
            ])
            total_hours = sum((o.date_to - o.date_from).total_seconds() / 3600 for o in outputs)
            self.assertAlmostEqual(total_hours, 1.0, places=5,
                                   msg="Only 1h of 2h deficit fits in the free [23:00-midnight] slot")
            period_end = datetime(2022, 12, 13, 0, 0, 0)
            for out in outputs:
                self.assertLessEqual(out.date_to, period_end,
                                     "Output must not spill past midnight (period boundary)")
        finally:
            rule.write({'active': False})

    def test_multiday_absence_leave_clips_to_schedule(self):
        """Multi-day absence leave must only count scheduled working hours per day.

        Without schedule-clipping, a Mon 08:00 -> Wed 16:00 leave:
          Monday sees 16h, Tuesday 24h, Wednesday 16h (56h total).
        With clipping to the 8h/day schedule, each day sees exactly 8h (24h total).
        With a 4h/day threshold the correct excess is 4h * 3 days = 12h.
        """
        calendar = self.env['resource.calendar'].create({
            'name': '8h/day Mon-Fri (multi-day test)',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': 8, 'hour_to': 16})
                for wd in ['0', '1', '2', '3', '4']
            ],
        })
        emp = self.env['hr.employee'].create({
            'name': 'Multi-Day Leave Employee',
            'tz': 'UTC',
            'attendance_based': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })
        emp.sudo().version_id.write({'resource_calendar_id': calendar.id})

        rule = self.env['hr.time.rule'].create({
            'name': 'Exceed 4h/day (multi-day)',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4,
            'work_entry_type_id': self.out_type.id,
            'condition_work_entry_type_ids': [self.src_type.id],
        })
        try:
            leave = self._make_leave(
                datetime(2022, 12, 12, 8), datetime(2022, 12, 14, 16),
                emp=emp,
            )
            self.assertAlmostEqual(
                self._output_hours(leave, self.out_type), 12.0, places=5,
                msg="3-day absence leave: 8h/day - 4h threshold = 4h excess * 3 days = 12h total",
            )
        finally:
            rule.write({'active': False})

    def test_two_pp_only_rules_stack_alloc_acc(self):
        """Two pp-only rules fire in sequence; alloc_acc grows so each rule earns allocation credit.

        Pipeline after both rules fire on the same 6h interval:
          rule1 fires: (wet, src, rule1, {})
          rule2 fires: alloc_acc | {rule1} → (wet, src, rule2, {rule1})

        In _apply_output excess processing:
          - rule1 credited via alloc_acc loop  → excess_alloc gets (emp, rule1, 6h)
          - rule2 credited via pp-only branch  → excess_alloc gets (emp, rule2, 6h)

        Both rules target the same allocation type, so the days are accumulated into a
        single allocation record (2x credit) rather than two separate records.
        """
        comp_type = self.env['hr.work.entry.type'].create({
            'name': 'PP Stack Comp',
            'code': 'PPSC',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })

        rule1 = self.env['hr.time.rule'].create({
            'name': 'PP Only #1',
            'sequence': 1,
            'working_hours_mode': 'day',
            'condition_work_entry_type_ids': [(4, self.src_type.id)],
            'leave_compensation_rate': 1.0,
            'allocation_type_id': comp_type.id,
        })
        rule2 = self.env['hr.time.rule'].create({
            'name': 'PP Only #2',
            'sequence': 2,
            'working_hours_mode': 'day',
            'condition_work_entry_type_ids': [(4, self.src_type.id)],
            'leave_compensation_rate': 1.0,
            'allocation_type_id': comp_type.id,
        })
        try:
            leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))  # 6h

            self.assertEqual(leave.work_entry_type_id, self.src_type)

            # each rule must earn allocation credit for the full 6h interval:
            # rule1 via alloc_acc credit loop, rule2 via pp-only excess branch -> 2 credits total.
            # both excess_alloc entries target the same allocation type so the days are
            # accumulated into one allocation record with 2x the per-rule credit.
            allocations = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', leave.employee_id.id),
                ('work_entry_type_id', '=', comp_type.id),
                ('state', '=', 'validate'),
            ])
            self.assertTrue(allocations, "At least one allocation must be created for comp_type")
            hours_per_day = leave.employee_id.resource_calendar_id.hours_per_day or 8.0
            # 6h x 1.0 rate / hours_per_day x 2 rules
            expected_days = 2 * 6.0 / hours_per_day
            self.assertAlmostEqual(
                sum(a.number_of_days for a in allocations), expected_days, places=4,
                msg="alloc_acc must stack rule1 + rule2: both rules credited for the 6h interval",
            )
        finally:
            rule1.write({'active': False})
            rule2.write({'active': False})
