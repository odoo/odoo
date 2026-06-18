# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

from odoo.tests.common import TransactionCase


class TestWorkingSchedule(TransactionCase):
    """Tests for the KSW_working_schedule module.

    Covers:
    - resource.calendar.group & resource.calendar.group.line (CRUD, archival)
    - resource.calendar extensions (is_temp_schedule, calendar_group_ids)
    - resource.calendar.attendance extension (optional calendar_id, calendar_group_id)
    - hr.employee extensions (main_calendar_id / temp_calendar_id sync,
      _get_calendar_attendances fallback)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Calendar group: Sun-Thu (Saudi standard) ──
        # dayofweek mapping: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Standard Sun-Thu',
        })
        cls.work_days = ['0', '1', '2', '3', '6']  # Mon-Thu + Sun
        for day in cls.work_days:
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })
            cls.env['resource.calendar.group.line'].create({
                'name': f'Break {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'break',
                'hour_from': 12.0,
                'hour_to': 13.0,
            })

        # ── Calendar with group (no standard attendance_ids) ──
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Group Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })
        # Clear standard attendance_ids so fallback is exercised
        cls.calendar.attendance_ids.unlink()

        # ── A second calendar marked as temporary ──
        cls.temp_calendar = cls.env['resource.calendar'].create({
            'name': 'Temp Summer Calendar',
            'tz': 'Asia/Riyadh',
            'is_temp_schedule': True,
        })

        # ── Employee ──
        cls.employee = cls.env['hr.employee'].create({
            'name': 'WS Test Employee',
            'main_calendar_id': cls.calendar.id,
        })

    # ==================================================================
    # resource.calendar.group
    # ==================================================================

    def test_group_create(self):
        """Creating a calendar group with lines should persist correctly."""
        self.assertEqual(self.calendar_group.name, 'Standard Sun-Thu')
        # 5 work + 5 break = 10 lines
        self.assertEqual(len(self.calendar_group.line_ids), 10)

    def test_group_archive(self):
        """Archiving a group should set active=False."""
        self.calendar_group.write({'active': False})
        self.assertFalse(self.calendar_group.active)
        # Searching without active_test should still find it
        found = self.env['resource.calendar.group'].with_context(
            active_test=False
        ).search([('id', '=', self.calendar_group.id)])
        self.assertTrue(found)

    # ==================================================================
    # resource.calendar.group.line
    # ==================================================================

    def test_line_defaults(self):
        """Lines should have sensible defaults."""
        line = self.env['resource.calendar.group.line'].create({
            'name': 'Default test',
            'calendar_group_id': self.calendar_group.id,
        })
        self.assertEqual(line.dayofweek, '0')  # Monday
        self.assertEqual(line.day_period, 'full_day')
        self.assertAlmostEqual(line.hour_from, 8.0)
        self.assertAlmostEqual(line.hour_to, 16.5)
        self.assertEqual(line.sequence, 10)

    def test_line_cascade_delete(self):
        """Deleting a group should cascade-delete its lines."""
        group = self.env['resource.calendar.group'].create({'name': 'Temp'})
        self.env['resource.calendar.group.line'].create({
            'name': 'Line 1',
            'calendar_group_id': group.id,
            'dayofweek': '0',
        })
        line_ids = group.line_ids.ids
        self.assertTrue(line_ids)
        group.unlink()
        remaining = self.env['resource.calendar.group.line'].search(
            [('id', 'in', line_ids)]
        )
        self.assertFalse(remaining)

    def test_line_date_filtering(self):
        """Lines with start_date / end_date should be filterable."""
        line = self.env['resource.calendar.group.line'].create({
            'name': 'Bounded',
            'calendar_group_id': self.calendar_group.id,
            'dayofweek': '0',
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 6, 30),
        })
        self.assertEqual(line.start_date, date(2026, 1, 1))
        self.assertEqual(line.end_date, date(2026, 6, 30))

    # ==================================================================
    # resource.calendar extensions
    # ==================================================================

    def test_is_temp_schedule_flag(self):
        """is_temp_schedule should be settable and filterable."""
        self.assertFalse(self.calendar.is_temp_schedule)
        self.assertTrue(self.temp_calendar.is_temp_schedule)

        temps = self.env['resource.calendar'].search([
            ('is_temp_schedule', '=', True),
            ('id', '=', self.temp_calendar.id),
        ])
        self.assertEqual(len(temps), 1)

    def test_calendar_group_ids_m2m(self):
        """calendar_group_ids Many2many should link groups to calendars."""
        self.assertIn(self.calendar_group, self.calendar.calendar_group_ids)

        # Add a second group
        group2 = self.env['resource.calendar.group'].create({'name': 'G2'})
        self.calendar.write({'calendar_group_ids': [(4, group2.id)]})
        self.assertIn(group2, self.calendar.calendar_group_ids)
        self.assertEqual(len(self.calendar.calendar_group_ids), 2)

        # Remove one
        self.calendar.write({'calendar_group_ids': [(3, group2.id)]})
        self.assertEqual(len(self.calendar.calendar_group_ids), 1)

    # ==================================================================
    # resource.calendar.attendance extensions
    # ==================================================================

    def test_attendance_calendar_id_not_required(self):
        """calendar_id should no longer be required on resource.calendar.attendance."""
        att = self.env['resource.calendar.attendance'].create({
            'name': 'Standalone',
            'dayofweek': '0',
            'hour_from': 9.0,
            'hour_to': 17.0,
            'calendar_group_id': self.calendar_group.id,
        })
        self.assertFalse(att.calendar_id)
        self.assertEqual(att.calendar_group_id, self.calendar_group)

    # ==================================================================
    # hr.employee: main_calendar_id / temp_calendar_id
    # ==================================================================

    def test_create_syncs_main_to_resource_calendar(self):
        """Creating an employee with main_calendar_id should sync resource_calendar_id."""
        self.assertEqual(
            self.employee.resource_calendar_id, self.calendar,
            "resource_calendar_id should match main_calendar_id on create.",
        )

    def test_create_without_main_calendar(self):
        """Creating an employee without main_calendar_id should use company default."""
        emp = self.env['hr.employee'].create({'name': 'No Main Cal'})
        # Should NOT crash; resource_calendar_id stays whatever the default is
        self.assertTrue(emp.exists())

    def test_write_main_calendar_syncs(self):
        """Writing main_calendar_id should update resource_calendar_id."""
        new_cal = self.env['resource.calendar'].create({
            'name': 'New Cal',
            'tz': 'Asia/Riyadh',
        })
        self.employee.write({'main_calendar_id': new_cal.id})
        self.assertEqual(self.employee.resource_calendar_id, new_cal)

    def test_write_resource_calendar_directly(self):
        """Explicitly setting resource_calendar_id should NOT be overwritten by main_calendar_id."""
        direct_cal = self.env['resource.calendar'].create({
            'name': 'Direct Cal',
            'tz': 'Asia/Riyadh',
        })
        self.employee.write({
            'main_calendar_id': self.calendar.id,
            'resource_calendar_id': direct_cal.id,
        })
        self.assertEqual(
            self.employee.resource_calendar_id, direct_cal,
            "Explicit resource_calendar_id should take precedence.",
        )

    def test_temp_calendar_domain(self):
        """temp_calendar_id should accept only is_temp_schedule=True calendars (domain is advisory)."""
        self.employee.write({'temp_calendar_id': self.temp_calendar.id})
        self.assertEqual(self.employee.temp_calendar_id, self.temp_calendar)

    # ==================================================================
    # hr.employee: _get_calendar_attendances fallback
    # ==================================================================

    def test_fallback_returns_days_and_hours(self):
        """When attendance_ids is empty, _get_calendar_attendances should
        use calendar_group_ids to compute days/hours."""
        # Our calendar has no attendance_ids (cleared in setUpClass)
        self.assertFalse(self.calendar.attendance_ids)

        # Monday 2026-01-05 to Friday 2026-01-09 (Mon-Thu are work, Fri is off)
        date_from = datetime(2026, 1, 5, 0, 0)  # Monday
        date_to = datetime(2026, 1, 9, 23, 59)    # Friday

        result = self.employee._get_calendar_attendances(date_from, date_to)

        # Mon-Thu = 4 work days (Fri is weekday=4, not in work_days)
        self.assertEqual(result['days'], 4)
        # Each day: 16.5 - 8.0 = 8.5 hours work, minus 1h break = 7.5h
        self.assertAlmostEqual(result['hours'], 4 * 7.5)

    def test_fallback_full_week(self):
        """Full week Sun-Sat: should count 5 work days (Sun + Mon-Thu)."""
        # Sunday 2026-01-04 to Saturday 2026-01-10
        date_from = datetime(2026, 1, 4, 0, 0)   # Sunday
        date_to = datetime(2026, 1, 10, 23, 59)   # Saturday

        result = self.employee._get_calendar_attendances(date_from, date_to)

        # Sun(6) + Mon(0) + Tue(1) + Wed(2) + Thu(3) = 5 work days
        # Fri(4) + Sat(5) = off
        self.assertEqual(result['days'], 5)
        self.assertAlmostEqual(result['hours'], 5 * 7.5)

    def test_fallback_single_work_day(self):
        """Single work day should return 1 day and correct hours."""
        date_from = datetime(2026, 1, 5, 0, 0)  # Monday
        date_to = datetime(2026, 1, 5, 23, 59)

        result = self.employee._get_calendar_attendances(date_from, date_to)

        self.assertEqual(result['days'], 1)
        self.assertAlmostEqual(result['hours'], 7.5)

    def test_fallback_single_weekend_day(self):
        """Single weekend day should return 0 days and 0 hours."""
        date_from = datetime(2026, 1, 2, 0, 0)  # Friday (weekday=4)
        date_to = datetime(2026, 1, 2, 23, 59)

        result = self.employee._get_calendar_attendances(date_from, date_to)

        self.assertEqual(result['days'], 0)
        self.assertAlmostEqual(result['hours'], 0.0)

    def test_fallback_with_date_objects(self):
        """_get_calendar_attendances should also accept date objects (not just datetime)."""
        d_from = date(2026, 1, 5)  # Monday
        d_to = date(2026, 1, 5)

        result = self.employee._get_calendar_attendances(d_from, d_to)

        self.assertEqual(result['days'], 1)
        self.assertAlmostEqual(result['hours'], 7.5)

    def test_fallback_no_calendar(self):
        """Employee with no calendar should return the super() result (likely zeros)."""
        emp = self.env['hr.employee'].create({
            'name': 'No Calendar Emp',
            'resource_calendar_id': False,
        })
        result = emp._get_calendar_attendances(
            datetime(2026, 1, 5), datetime(2026, 1, 9)
        )
        # Without a calendar, fallback can't compute anything
        self.assertIn('days', result)
        self.assertIn('hours', result)

    def test_fallback_no_group_lines(self):
        """Calendar with empty calendar_group_ids should return super() result."""
        empty_cal = self.env['resource.calendar'].create({
            'name': 'Empty Groups Cal',
            'tz': 'Asia/Riyadh',
        })
        empty_cal.attendance_ids.unlink()

        emp = self.env['hr.employee'].create({
            'name': 'Empty Groups Emp',
            'main_calendar_id': empty_cal.id,
        })

        result = emp._get_calendar_attendances(
            datetime(2026, 1, 5), datetime(2026, 1, 9)
        )
        self.assertEqual(result['days'], 0)
        self.assertAlmostEqual(result['hours'], 0.0)

    def test_fallback_respects_line_date_range(self):
        """Lines with start_date/end_date should only apply within their range."""
        # Create a separate group with bounded lines
        bounded_group = self.env['resource.calendar.group'].create({
            'name': 'Bounded Group',
        })
        # Only valid Jan 5-7, 2026 (Mon-Wed)
        for day in ['0', '1', '2']:  # Mon, Tue, Wed
            self.env['resource.calendar.group.line'].create({
                'name': f'Bounded {day}',
                'calendar_group_id': bounded_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.0,
                'start_date': date(2026, 1, 5),
                'end_date': date(2026, 1, 7),
            })

        bounded_cal = self.env['resource.calendar'].create({
            'name': 'Bounded Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, bounded_group.id)],
        })
        bounded_cal.attendance_ids.unlink()

        emp = self.env['hr.employee'].create({
            'name': 'Bounded Emp',
            'main_calendar_id': bounded_cal.id,
        })

        # Query Jan 5 (Mon) to Jan 9 (Fri)
        result = emp._get_calendar_attendances(
            datetime(2026, 1, 5), datetime(2026, 1, 9)
        )

        # Only Mon-Wed within range = 3 days
        self.assertEqual(result['days'], 3)

    def test_fallback_break_deduction(self):
        """Break lines should be deducted from total hours."""
        # Our standard group: 8.5h work - 1h break = 7.5h per day
        result = self.employee._get_calendar_attendances(
            datetime(2026, 1, 5), datetime(2026, 1, 5)  # Monday
        )
        # Without break: 16.5 - 8.0 = 8.5
        # With break: 8.5 - 1.0 = 7.5
        self.assertAlmostEqual(result['hours'], 7.5)

    def test_fallback_multiple_groups(self):
        """Calendar with multiple groups should aggregate all lines."""
        extra_group = self.env['resource.calendar.group'].create({
            'name': 'Extra Friday Group',
        })
        # Add Friday as a work day via the extra group
        self.env['resource.calendar.group.line'].create({
            'name': 'Friday work',
            'calendar_group_id': extra_group.id,
            'dayofweek': '4',  # Friday
            'day_period': 'full_day',
            'hour_from': 8.0,
            'hour_to': 12.0,
        })
        self.calendar.write({'calendar_group_ids': [(4, extra_group.id)]})

        # Query Mon-Fri (5 work days: Mon-Thu from standard + Fri from extra)
        result = self.employee._get_calendar_attendances(
            datetime(2026, 1, 5), datetime(2026, 1, 9)
        )

        # Mon-Thu: 4 days × 7.5h = 30h
        # Fri: 1 day × 4h = 4h (no break defined)
        self.assertEqual(result['days'], 5)
        self.assertAlmostEqual(result['hours'], 30.0 + 4.0)

        # Cleanup: remove the extra group
        self.calendar.write({'calendar_group_ids': [(3, extra_group.id)]})

    def test_fallback_with_standard_attendances_uses_super(self):
        """If standard attendance_ids exist and return data, super() result is used."""
        cal_with_att = self.env['resource.calendar'].create({
            'name': 'Standard Attendance Cal',
            'tz': 'Asia/Riyadh',
        })
        # The default creation of resource.calendar already populates attendance_ids
        self.assertTrue(cal_with_att.attendance_ids)

        emp = self.env['hr.employee'].create({
            'name': 'Standard Att Emp',
            'main_calendar_id': cal_with_att.id,
        })

        result = emp._get_calendar_attendances(
            datetime(2026, 1, 5), datetime(2026, 1, 9)
        )
        # Should return something from super(), not from our fallback
        self.assertIn('days', result)
        self.assertIn('hours', result)

