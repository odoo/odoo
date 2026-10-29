# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date, UTC
from zoneinfo import ZoneInfo

from odoo.tools.intervals import Intervals
from odoo.fields import Date
from odoo.tools.date_utils import sum_intervals

from odoo.tests import tagged
from odoo.tests.common import freeze_time

from .common import TestHrCommon


class TestResource(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestResource, cls).setUpClass()
        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})
        cls.employee_niv = cls.env['hr.employee'].create({
            'name': 'Sharlene Rhodes',
            'departure_date': '2022-06-01',
            'resource_calendar_id': cls.calendar_40h.id,
        })
        cls.employee_niv_create_date = '2021-01-01 10:00:00'
        cls.env.cr.execute("UPDATE hr_employee SET create_date=%s WHERE id=%s",
                           (cls.employee_niv_create_date, cls.employee_niv.id))

        cls.calendar_richard = cls.env['resource.calendar'].create({'name': 'Calendar of Richard'})
        cls.employee.resource_calendar_id = cls.calendar_richard

        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 16})
            ],
        })

        cls.contract_cdd = cls.employee.version_id
        cls.contract_cdd.write({
            'date_version': Date.to_date('2021-09-01'),
            'contract_date_start': Date.to_date('2021-09-01'),
            'contract_date_end': Date.to_date('2021-10-31'),
            'name': 'First CDD Contract for Richard',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': cls.employee.id,
        })
        cls.contract_cdi_values = {
            'date_version': Date.to_date('2021-11-01'),
            'contract_date_start': Date.to_date('2021-11-01'),
            'contract_date_end': False,
            'name': 'CDI Contract for Richard',
            'resource_calendar_id': cls.calendar_richard.id,
            'wage': 5000.0,
            'employee_id': cls.employee.id,
        }

    def test_calendars_validity_within_period_default(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            datetime(2021, 7, 1, 8, tzinfo=UTC),
            datetime(2021, 7, 30, 17, tzinfo=UTC),
        )
        interval = Intervals([(
            datetime(2021, 7, 1, 8, tzinfo=UTC),
            datetime(2021, 7, 30, 17, tzinfo=UTC),
            self.env['resource.calendar.attendance']
        )])

        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(1, len(calendars[self.employee_niv.resource_id.id]), "Niv should only have one calendar")
        niv_entry = calendars[self.employee_niv.resource_id.id]
        niv_calendar = next(iter(niv_entry))
        self.assertEqual(niv_calendar, self.calendar_40h, "It should be Niv's Calendar")
        self.assertFalse(niv_entry[niv_calendar] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - niv_entry[niv_calendar], "Calendar validity should cover all interval")

    def test_calendars_validity_within_period_creation(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            datetime(2020, 12, 1, 8, tzinfo=UTC),
            datetime(2021, 1, 31, 17, tzinfo=UTC),
        )
        interval = Intervals([(
            datetime(2020, 12, 1, 8, tzinfo=UTC),
            datetime(2021, 1, 31, 17, tzinfo=UTC),
            self.env['resource.calendar.attendance']
        )])
        niv_entry = calendars[self.employee_niv.resource_id.id]
        self.assertFalse(niv_entry[self.calendar_40h] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - niv_entry[self.calendar_40h], "Calendar validity should cover all interval")

    def test_availability_hr_infos_resource(self):
        """ Ensure that all the hr infos needed to display the avatar popover card
            are available on the model resource.resource, even if the employee is archived
        """
        user = self.env.ref('base.test_user')
        user.write({
            'email': 'test@odoo.perso',
            'phone': '+32488990011',
        })
        department = self.env['hr.department'].create([{
            'name': 'QA',
        }])
        resource = self.env['resource.resource'].create([{
            'name': 'Test resource',
            'user_id': user.id,
        }])
        employee = self.env['hr.employee'].create([{
            'name': 'Test employee',
            'active': False,
            'user_id': user.id,
            'job_title': 'Tester',
            'department_id': department.id,
            'work_email': 'test@odoo.pro',
            'work_phone': '+32800100100',
            'resource_id': resource.id,
        }])
        for field in 'email', 'phone':
            self.assertEqual(resource[field], user[field])
        for field in 'job_title', 'department_id', 'work_email', 'work_phone', 'show_hr_icon_display', 'hr_icon_display':
            self.assertEqual(resource[field], employee[field])

    def test_calendars_validity_within_period(self):
        self.employee.create_version(self.contract_cdi_values)
        tz = ZoneInfo(self.employee.tz)
        calendars = self.employee.resource_id._get_calendars_validity_within_period(
            datetime(2021, 10, 1, tzinfo=tz),
            datetime(2021, 12, 1, tzinfo=tz),
        )
        interval_35h = Intervals([(
            datetime(2021, 10, 1, tzinfo=tz),
            datetime.combine(date(2021, 10, 31), datetime.max.time(), tzinfo=tz),
            self.env['resource.calendar.attendance']
        )])
        interval_40h = Intervals([(
            datetime(2021, 11, 1, tzinfo=tz),
            datetime(2021, 12, 1, tzinfo=tz),
            self.env['resource.calendar.attendance']
        )])

        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(2, len(calendars[self.employee.resource_id.id]), "Jean should only have one calendar")
        richard_entries = calendars[self.employee.resource_id.id]
        for calendar in richard_entries:
            self.assertTrue(calendar in (self.calendar_35h | self.calendar_richard), "Each calendar should be listed")
            if calendar == self.calendar_35h:
                self.assertFalse(richard_entries[calendar] - interval_35h, "Interval 35h should cover all calendar 35h validity")
                self.assertFalse(interval_35h - richard_entries[calendar], "Calendar 35h validity should cover all interval 35h")
            elif calendar == self.calendar_richard:
                self.assertFalse(richard_entries[calendar] - interval_40h, "Interval 40h should cover all calendar 40h validity")
                self.assertFalse(interval_40h - richard_entries[calendar], "Calendar 40h validity should cover all interval 40h")

    def test_queries(self):
        employees_test = self.env['hr.employee'].create([{
            'name': 'Employee ' + str(i),
        } for i in range(0, 50)])
        for emp in employees_test:
            self.contract_cdd.copy({'employee_id': emp.id})
            self.contract_cdi_values['employee_id'] = emp.id
            self.employee.create_version(self.contract_cdi_values)

        start = datetime(2021, 9, 1, tzinfo=UTC)
        end = datetime(2021, 11, 30, 23, 59, 59, tzinfo=UTC)
        with self.assertQueryCount(165):
            work_intervals, _ = (employees_test | self.employee).resource_id._get_valid_work_intervals(start, end)

        self.assertEqual(len(work_intervals), 51)

    def test_get_valid_work_intervals(self):
        self.employee.create_version(self.contract_cdi_values)
        start = datetime(2021, 10, 24, 2, tzinfo=ZoneInfo(self.employee.tz))
        end = datetime(2021, 11, 6, 23, 59, 59, tzinfo=ZoneInfo(self.employee.tz))
        work_intervals, _ = self.employee.resource_id._get_valid_work_intervals(start, end)
        sum_work_intervals = sum_intervals(work_intervals[self.employee.resource_id.id])
        self.assertEqual(75, sum_work_intervals, "Sum of the work intervals for the employee should be 35h+40h = 75h")

    def test_multi_contract_attendance(self):
        """ Verify whether retrieving an employee's calendar attendances can
            handle multiple contracts with different calendars.
        """

        date_from = datetime(2021, 10, 1, tzinfo=UTC)
        date_to = datetime(2021, 11, 30, tzinfo=UTC)

        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(21 * 7, attendances['hours'],
            "Attendances should only include running or finished contracts.")

        self.employee.create_version(self.contract_cdi_values)

        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(21 * 7 + 21 * 8, attendances['hours'],
            "Attendances should add up multiple contracts with varying work weeks.")

    def test_calendar_attendances_working_time_leave(self):
        """ Only leaves counted as absence are deducted from the calendar attendances. """
        date_from = datetime(2021, 10, 4, tzinfo=UTC)
        date_to = datetime(2021, 10, 9, tzinfo=UTC)
        self.env['resource.calendar.leaves'].create({
            'name': 'Company training',
            'calendar_id': self.calendar_35h.id,
            'date_from': datetime(2021, 10, 6, 6),
            'date_to': datetime(2021, 10, 6, 18),
            'count_as': 'working_time',
        })
        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(attendances, {'days': 5, 'hours': 35})

        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'calendar_id': self.calendar_35h.id,
            'date_from': datetime(2021, 10, 7, 6),
            'date_to': datetime(2021, 10, 7, 18),
        })
        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(attendances, {'days': 4, 'hours': 28})

    def test_alter_resource_calendar_of_resouce(self):
        self.assertEqual(self.employee.resource_calendar_id, self.employee.resource_id.calendar_id)
        self.assertEqual(self.employee.version_id.resource_calendar_id, self.employee.resource_id.calendar_id)
        self.employee.resource_id.write({'calendar_id': self.calendar_40h})
        self.assertEqual(self.employee.resource_calendar_id, self.employee.resource_id.calendar_id)
        self.assertEqual(self.employee.version_id.resource_calendar_id, self.employee.resource_id.calendar_id)

    def test_resource_calendar_follows_current_version(self):
        """ The resource calendar follows the current version, whatever the way it changes. """
        calendar_a, calendar_b = self.env['resource.calendar'].create([
            {'name': 'Calendar A'},
            {'name': 'Calendar B'},
        ])
        employee = self.env['hr.employee'].create({
            'name': 'Versioned Employee',
            'date_version': date(2020, 1, 1),
            'resource_calendar_id': calendar_a.id,
        })
        future_version = employee.create_version({
            'date_version': date(2100, 1, 1),
            'resource_calendar_id': calendar_b.id,
        })
        self.assertEqual(employee.resource_id.calendar_id, calendar_a)

        future_version.date_version = date(2021, 1, 1)
        self.assertEqual(employee.current_version_id, future_version)
        self.assertEqual(employee.resource_id.calendar_id, calendar_b)

        future_version.action_archive()
        self.assertEqual(employee.resource_id.calendar_id, calendar_a)

        future_version.action_unarchive()
        self.assertEqual(employee.resource_id.calendar_id, calendar_b)

        new_version = employee.create_version({
            'date_version': date(2022, 1, 1),
            'resource_calendar_id': calendar_a.id,
        })
        self.assertEqual(employee.current_version_id, new_version)
        self.assertEqual(employee.resource_id.calendar_id, calendar_a)

    def test_calendar_validity_with_new_version_same_contract(self):
        """ Test that when a new version is created for the same contract with a different
            working schedule, the calendar validity is correctly split at the version
            boundary.
        """
        self.employee_niv.version_id.write({
            'contract_date_start': date(2026, 3, 1),
            'resource_calendar_id': self.calendar_40h.id,
        })
        self.employee_niv.create_version({
            'date_version': date(2026, 4, 12),
            'resource_calendar_id': self.calendar_35h.id,
        })

        tz = ZoneInfo(self.employee_niv.tz)
        # Query the week of April 13-17 (Mon-Fri), entirely after the new version date
        start = datetime(2026, 4, 13, 0, 0, 0, tzinfo=tz)
        end = datetime(2026, 4, 17, 23, 59, 59, tzinfo=tz)
        work_intervals, _ = self.employee_niv.resource_id._get_valid_work_intervals(start, end)
        total_hours = sum_intervals(work_intervals[self.employee_niv.resource_id.id])
        self.assertEqual(total_hours, 35.0)

    def test_expected_attendances_without_contract_deduct_absences(self):
        """ Without contract, leaves counted as absence are deducted from the expected attendances. """
        employee = self.env['hr.employee'].create({
            'name': 'No Contract',
            'tz': 'UTC',
            'resource_calendar_id': self.calendar_35h.id,
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Day off',
            'resource_id': employee.resource_id.id,
            'date_from': datetime(2026, 1, 5, 0, 0),
            'date_to': datetime(2026, 1, 5, 23, 59, 59),
            'count_as': 'absence',
        })
        intervals = employee._get_expected_attendances(
            datetime(2026, 1, 5, tzinfo=UTC),
            datetime(2026, 1, 9, 23, 59, 59, tzinfo=UTC),
        )
        self.assertEqual(sum_intervals(intervals), 28.0)

    def test_unusual_days_without_date_to(self):
        """ Without ``date_to``, the unusual days of the single day ``date_from`` are returned. """
        self.assertEqual(self.employee_niv._get_unusual_days('2026-01-05 00:00:00'), {'2026-01-05': False})
        self.employee_niv.version_id.contract_date_start = date(2026, 1, 1)
        self.assertEqual(self.employee_niv._get_unusual_days('2026-01-10 00:00:00'), {'2026-01-10': True})

    @freeze_time('2026-06-01')
    def test_resource_leave_calendar_on_last_version_day(self):
        """ A leave on the last day of the current version gets the calendar of that version. """
        employee = self.env['hr.employee'].create({
            'name': 'Versioned',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'resource_calendar_id': self.calendar_35h.id,
        })
        employee.create_version({
            'date_version': date(2027, 1, 1),
            'resource_calendar_id': self.calendar_40h.id,
        })
        version = employee.version_id
        self.assertEqual(version.date_end, date(2026, 12, 31))
        self.assertEqual(version.resource_calendar_id, self.calendar_35h)
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Last day off',
            'resource_id': employee.resource_id.id,
            'date_from': datetime(2026, 12, 31, 8, 0),
            'date_to': datetime(2026, 12, 31, 17, 0),
        })
        self.assertEqual(leave.calendar_id, self.calendar_35h)

    def test_employees_count_hidden_without_hr_access(self):
        """ Every internal user can read a working schedule, but the count behind
            `employees_count` needs the rights on the versions, so the field must
            not reach a user without them. """
        user = self.env['res.users'].create({
            'name': "Plain user",
            'login': "plain_user",
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        arch = self.env['resource.calendar'].with_user(user).get_view(
            self.env.ref('resource.resource_calendar_form').id)['arch']
        self.assertNotIn('employees_count', arch)
