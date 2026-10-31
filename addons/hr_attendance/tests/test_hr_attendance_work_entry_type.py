# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'attendance_wet')
class TestHrAttendanceWorkEntryType(TransactionCase):
    '''Test suite covering automatic selection and resolution of work entry types on attendance records.'''

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.default_work_type = cls.company._get_default_attendance_work_entry_type()
        cls.company.attendance_work_entry_type_id = cls.default_work_type

        cls.telework_type, cls.training_type, cls.custom_override_type = cls.env['hr.work.entry.type'].create([{
            'name': 'Telework',
            'code': 'TEST_TELEWORK',
        }, {
            'name': 'Training',
            'code': 'TEST_TRAINING',
        }, {
            'name': 'Custom Override',
            'code': 'TEST_OVERRIDE',
        }])

        # Working Schedules
        cls.calendar_no_wet, cls.calendar_with_wets = cls.env['resource.calendar'].create([{
            'name': 'Calendar Without WET',
            'company_id': cls.company.id,
            'attendance_ids': [
                Command.create({'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                Command.create({'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
            ],
        }, {
            'name': 'Calendar With WETs',
            'company_id': cls.company.id,
            'attendance_ids': [
                Command.create({'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'work_entry_type_id': False}),
                Command.create({'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'work_entry_type_id': cls.training_type.id}),
                Command.create({'dayofweek': '2', 'hour_from': 8, 'hour_to': 18, 'work_entry_type_id': cls.training_type.id}),
                Command.create({'dayofweek': '4', 'hour_from': 9, 'hour_to': 13, 'work_entry_type_id': cls.telework_type.id}),
                Command.create({'dayofweek': '4', 'hour_from': 14, 'hour_to': 18, 'work_entry_type_id': cls.telework_type.id}),
            ],
        }])

        # Employees
        cls.employee_with_schedule, cls.employee_no_wet_schedule, cls.employee_tokyo = cls.env['hr.employee'].create([{
            'name': 'Scheduled Employee (UTC)',
            'tz': 'UTC',
            'resource_calendar_id': cls.calendar_with_wets.id,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        }, {
            'name': 'Default Schedule Employee',
            'tz': 'UTC',
            'resource_calendar_id': cls.calendar_no_wet.id,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        }, {
            'name': 'Tokyo Employee (UTC+9)',
            'tz': 'Asia/Tokyo',
            'resource_calendar_id': cls.calendar_with_wets.id,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        }])

    def test_01_no_wet_on_schedule_defaults_to_company_work(self):
        '''When no time type is configured on the working schedule line, defaults to company work type.'''
        # 2026-06-08 is Monday
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_no_wet_schedule.id,
            'check_in': datetime(2026, 6, 8, 8, 30),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.default_work_type,
            'Attendance should default to company\'s attendance work entry type when schedule has none configured.',
        )

    def test_02_single_wet_configured_for_day(self):
        '''When a time type is configured on a day's schedule, attendance inherits that time type.'''
        # 2026-06-12 is Friday (Telework configured for the day)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 12, 10, 0),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.telework_type,
            'Attendance record should inherit the time type configured for that day.',
        )

    def test_03_single_wet_configured_for_day_early_checkin(self):
        '''When an employee clocks in early on a day with a configured time type, it still applies.'''
        # 2026-06-12 is Friday, shift starts at 09:00; employee checks in at 08:45 (15 min early)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 12, 8, 45),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.telework_type,
            'Early check-in on a day with a single configured time type should still inherit that time type.',
        )

    def test_04_single_wet_configured_for_day_break_checkin(self):
        '''Check-in between split periods on a single-type day inherits the day's time type.'''
        # 2026-06-12 is Friday, break is 13:00 - 14:00; employee clocks in at 13:35
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 12, 13, 35),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.telework_type,
            'Check-in during midday break on a single-type day should still inherit that time type.',
        )

    def test_05_multi_period_day_morning_checkin(self):
        '''Multi-period day: check-in during morning shift (08:00 - 12:00) inherits morning type (Default).'''
        # 2026-06-08 is Monday, 08:30 (Morning has no WET set -> defaults to Work)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 8, 8, 30),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.default_work_type,
            'Check-in falling in the morning period should inherit the morning period\'s time type.',
        )

    def test_06_multi_period_day_afternoon_checkin(self):
        '''Multi-period day: check-in during afternoon shift (13:00 - 17:00) inherits afternoon type (Training).'''
        # 2026-06-08 is Monday, 14:00 (Afternoon has WET = Training)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 8, 14, 0),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.training_type,
            'Check-in falling in the afternoon period should inherit the afternoon period\'s time type.',
        )

    def test_07_multi_period_day_early_morning_checkin(self):
        '''Multi-period day: checking in early for the morning shift matches the closest (morning) period.'''
        # 2026-06-08 is Monday, 07:50 (10 min before 08:00 morning shift)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 8, 7, 50),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.default_work_type,
            'Early check-in before the first period on a multi-period day should match the closest morning period.',
        )

    def test_08_multi_period_day_early_afternoon_checkin(self):
        '''Multi-period day: checking in early for the afternoon shift matches the closest (afternoon) period.'''
        # 2026-06-08 is Monday, 12:50 (10 min before 13:00 afternoon training shift)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 8, 12, 50),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.training_type,
            'Check-in before afternoon period on a multi-period day should match the closest afternoon period.',
        )

    def test_09_unscheduled_day_fallback_to_default(self):
        '''Check-in on an unscheduled day (e.g. Sunday) falls back cleanly to the company default.'''
        # 2026-06-14 is Sunday
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 14, 10, 0),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.default_work_type,
            'Attendance on an unscheduled day should fall back to company default time type.',
        )

    def test_10_single_schedule_for_entire_day(self):
        '''Check-in on a single scheduled worked day'''
        # 2026-06-10 is Wednesday
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 10, 7, 0),
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.training_type,
            'Attendance on an unscheduled day should fall back to company default time type.',
        )

    def test_11_manual_override_on_create_is_preserved(self):
        '''User explicitly providing a different time type upon creation/updating must not be overwritten.'''
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_with_schedule.id,
            'check_in': datetime(2026, 6, 12, 10, 0),  # Friday = Telework
            'work_entry_type_id': self.custom_override_type.id,
        })
        self.assertEqual(
            attendance.work_entry_type_id, self.custom_override_type,
            'Explicit user-selected work_entry_type_id in create() must be preserved.',
        )

        attendance.write({'work_entry_type_id': self.default_work_type.id})
        self.assertEqual(
            attendance.work_entry_type_id, self.default_work_type,
            'Manual edit on an existing attendance must be preserved.',
        )

    def test_12_form_view_dynamic_onchange_and_save(self):
        '''Simulate UI form interaction: selecting employee and check-in dynamically sets time type.'''
        with Form(self.env['hr.attendance']) as form:
            form.employee_id = self.employee_with_schedule
            # Check-in on Friday (Telework)
            form.check_in = datetime(2026, 6, 12, 10, 0)
            self.assertEqual(
                form.work_entry_type_id, self.telework_type,
                'Form view should dynamically select Friday\'s configured Telework time type.',
            )

            # Change check-in to Monday afternoon (Training)
            form.check_in = datetime(2026, 6, 8, 14, 0)
            self.assertEqual(
                form.work_entry_type_id, self.training_type,
                'Form view should dynamically update to Monday afternoon\'s Training time type.',
            )

            # Manually override in the form view
            form.work_entry_type_id = self.custom_override_type

        saved_attendance = form.record
        self.assertEqual(
            saved_attendance.work_entry_type_id, self.custom_override_type,
            'Manually overridden value in the form view must be saved.',
        )

    def test_13_employee_timezone_conversion(self):
        '''Check-in times in UTC are correctly localized to the employee's timezone.'''
        # Tokyo is UTC+9.
        # Monday afternoon in Tokyo (14:00 JST) corresponds to Monday morning in UTC (05:00 UTC).
        attendance_afternoon = self.env['hr.attendance'].create({
            'employee_id': self.employee_tokyo.id,
            'check_in': datetime(2026, 6, 8, 5, 0),  # 14:00 in Tokyo -> Afternoon Training
        })
        self.assertEqual(
            attendance_afternoon.work_entry_type_id, self.training_type,
            'Check-in at 05:00 UTC is 14:00 Tokyo time and should inherit afternoon Training type.',
        )
