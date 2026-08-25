# -*- coding: utf-8 -*-
from datetime import date, datetime

from odoo.tests import Form, tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.exceptions import ValidationError


class TestAutomaticLeaveDates(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAutomaticLeaveDates, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Automatic Test',
            'time_type': 'leave',
            'requires_allocation': False,
            # Required for `request_unit_half` to be visible in the view
            'request_unit': 'half_day',
        })

    def test_no_attendances(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'No Attendances',
            'attendance_ids': [(5, 0, 0)],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)

    def test_single_attendance_on_morning_and_afternoon(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'simple morning + afternoon',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'name': 'monday lunch',
                                   'hour_from': 12,
                                   'hour_to': 13,
                                   'day_period': 'lunch',
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'name': 'monday afternoon',
                                   'hour_from': 13,
                                   'hour_to': 17,
                                   'day_period': 'afternoon',
                                   'dayofweek': '0',
                               })]
        })

        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

            leave_form.request_date_from_period = 'pm'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

    def test_multiple_attendance_on_morning(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'multi morning',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning 1',
                                   'hour_from': 8,
                                   'hour_to': 10,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'duration_days': 0.25,
                               }),
                               (0, 0, {
                                   'name': 'monday morning 2',
                                   'hour_from': 10.25,
                                   'hour_to': 12.25,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'duration_days': 0.25,
                               }),
                               (0, 0, {
                                   'name': 'monday lunch',
                                   'hour_from': 12.25,
                                   'hour_to': 13,
                                   'day_period': 'lunch',
                                   'dayofweek': '0',
                               }),
                               (0, 0, {
                                   'name': 'monday afternoon',
                                   'hour_from': 13,
                                   'hour_to': 17,
                                   'day_period': 'afternoon',
                                   'dayofweek': '0',
                                   'duration_days': 0.5,
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

            leave_form.request_date_from_period = 'pm'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, .5)
            self.assertEqual(leave_form.record.number_of_hours, 4)

    def test_attendance_on_morning(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Morning only',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'Monday All day',
                                   'hour_from': 8,
                                   'hour_to': 16,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                               })],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_unit_half = True
            # Ask for morning
            leave_form.request_date_from_period = 'am'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 1)
            self.assertEqual(leave_form.record.number_of_hours, 8)

            # Ask for afternoon
            leave_form.request_date_from_period = 'pm'

            leave_form.save()  # need to be saved to have access to record
            self.assertEqual(leave_form.record.number_of_days, 0)
            self.assertEqual(leave_form.record.number_of_hours, 0)

    def test_attendance_next_day(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'tuesday morning',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '1',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # does not work on mondays
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)
        self.assertEqual(leave.date_from, datetime(2019, 9, 2, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 2, 10, 0, 0))

    def test_attendance_previous_day(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # does not work on tuesdays
            leave_form.request_date_from = date(2019, 9, 3)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)
        self.assertEqual(leave.date_from, datetime(2019, 9, 3, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 3, 10, 0, 0))

    def test_2weeks_calendar(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'two_weeks_calendar': True,
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning odd week',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'week_type': '0',
                                   'duration_days': 0.5,
                               }),
                               (0, 0, {
                                   'name': 'monday morning even week',
                                   'hour_from': 10,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'week_type': '1',
                                   'duration_days': 0.25
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # even week, works 2 hours
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0.25)
        self.assertEqual(leave.number_of_hours, 2)
        self.assertEqual(leave.date_from, datetime(2019, 9, 2, 8, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 2, 10, 0, 0))

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # odd week, works 4 hours
            leave_form.request_date_from = date(2019, 9, 9)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0.5)
        self.assertEqual(leave.number_of_hours, 4)
        self.assertEqual(leave.date_from, datetime(2019, 9, 9, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 9, 10, 0, 0))

    def test_2weeks_calendar_next_week(self):
        self.env.user.tz = 'Europe/Brussels'
        calendar = self.env['resource.calendar'].create({
            'name': 'auto next day',
            'two_weeks_calendar': True,
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {
                                   'name': 'monday morning odd week',
                                   'hour_from': 8,
                                   'hour_to': 12,
                                   'day_period': 'morning',
                                   'dayofweek': '0',
                                   'week_type': '0',
                               })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            # even week, does not work
            leave_form.request_date_from = date(2019, 9, 2)
            leave_form.request_unit_half = True
            leave_form.request_date_from_period = 'am'

        leave = leave_form.record
        self.assertEqual(leave.number_of_days, 0)
        self.assertEqual(leave.number_of_hours, 0)
        self.assertEqual(leave.date_from, datetime(2019, 9, 2, 6, 0, 0))
        self.assertEqual(leave.date_to, datetime(2019, 9, 2, 10, 0, 0))


@tagged('post_install', '-at_install')
class TestDurationWithActivityAutomation(TestHrHolidaysCommon):
    def test_duration_with_activity_automation(self):
        """An automation that creates a "Time Off Approval" activity on leave
        creation must not reset the leave duration to 0.

        base_automation is not a dependency of hr_holidays, so skip when it is
        not installed.
        """
        if 'base.automation' not in self.env:
            self.skipTest("`base_automation` is not installed")

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Automation Duration Test',
            'time_type': 'leave',
            'requires_allocation': False,
        })

        # The activity must be assigned to a user other than the one creating the
        # leave: only then is a notification sent, which renders the leave's
        # display_name (reading number_of_days) mid-create and triggers the bug.
        approver = self.env['res.users'].create({
            'name': 'TOA Approver',
            'login': 'toa_approver',
            'email': 'toa_approver@example.com',
        })

        model = self.env['ir.model']._get('hr.leave')
        automation = self.env['base.automation'].create({  # noqa: OLS03001
            'name': 'Create Time Off Approval activity',
            'trigger': 'on_create_or_write',
            'model_id': model.id,
        })
        self.addCleanup(self.env['base.automation']._unregister_hook)
        self.env['ir.actions.server'].create({
            'name': 'Create TOA activity',
            'base_automation_id': automation.id,
            'model_id': model.id,
            'state': 'next_activity',
            'activity_type_id': self.env.ref('hr_holidays.mail_act_leave_approval').id,
            'activity_user_type': 'specific',
            'activity_user_id': approver.id,
        })

        leave = self.env['hr.leave'].create({
            'holiday_status_id': leave_type.id,
            'employee_id': self.employee_emp_id,
            'request_date_from': date(2019, 9, 2),
            'request_date_to': date(2019, 9, 4),
        })
        self.assertTrue(leave.activity_ids)
        self.assertEqual(leave.number_of_days, 3.0)
        self.assertEqual(leave.number_of_hours, 24.0)
