# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import re

from odoo.tests import freeze_time
from .test_common import TestCommon
from pytz import utc

from odoo import Command

@freeze_time('2020-01-01')
class TestPlanningLeaves(TestCommon):
    def test_simple_employee_leave(self):
        self.leave_type.responsible_ids = [Command.link(self.env.ref('base.user_admin').id)]
        leave = self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-1-1',
            'request_date_to': '2020-1-1',
        })

        slot_1 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 1, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 1, 17, 0),
        })
        slot_2 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 2, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 2, 17, 0),
        })

        self.assertNotEqual(slot_1.leave_warning, False, "leave is not validated , but warning for requested time off")

        leave.action_validate()

        self.assertNotEqual(slot_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        # The warning should display the whole concerned leave period
        self.assertEqual(slot_1.leave_warning,
                         "bert is on time off on 01/01/2020. \n")

        self.assertEqual(slot_2.leave_warning, False,
                         "employee is not on leave, no warning")

    def test_multiple_leaves(self):
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-1-6',
            'request_date_to': '2020-1-7',
        }).action_validate()

        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-1-8',
            'request_date_to': '2020-1-10',
        }).action_validate()

        slot_1 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 6, 17, 0),
        })

        self.assertNotEqual(slot_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        # The warning should display the whole concerned leave period
        self.assertEqual(slot_1.leave_warning,
                         "bert is on time off from 01/06/2020 to 01/07/2020. \n")

        slot_2 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 7, 17, 0),
        })
        self.assertEqual(slot_2.leave_warning,
                         "bert is on time off from 01/06/2020 to 01/07/2020. \n")

        slot_3 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 10, 17, 0),
        })
        self.assertEqual(slot_3.leave_warning, "bert is on time off from 01/06/2020 to 01/10/2020. \n",
                         "should show the start of the 1st leave and end of the 2nd")

    def test_shift_update_according_time_off(self):
        """ working day and allocated hours of planning slot are update according to public holiday
        Test Case
        ---------
            1) Create slot
            2) Add public holiday
            3) Checked the allocated hour and working days count of slot
            4) Unlink the public holiday
            5) Checked the allocated hour and working days count of slot
        """
        with freeze_time("2020-04-10"):
            today = datetime.datetime.today()
            self.env.cr._now = today # used to force create_date, as sql is not wrapped by freeze gun

            ethan = self.env['hr.employee'].create({
                'create_date': today,
                'name': 'ethan',
                'tz': 'UTC',
                'employee_type': 'freelance',
            })

            slot = self.env['planning.slot'].create({
                'resource_id': ethan.resource_id.id,
                'employee_id': ethan.id,
                'start_datetime': datetime.datetime(2020, 4, 20, 8, 0), # Monday
                'end_datetime': datetime.datetime(2020, 4, 24, 17, 0),
            })

            initial_slot = {
                'allocated_hours': slot.allocated_hours,
            }

            # Add the public holiday
            public_holiday = self.env['resource.calendar.leaves'].create({
                'name': 'Public holiday',
                'calendar_id': ethan.resource_id.calendar_id.id,
                'date_from': datetime.datetime(2020, 4, 21, 8, 0), # Wednesday
                'date_to': datetime.datetime(2020, 4, 21, 17, 0),
            })

            self.assertNotEqual(slot.allocated_hours, initial_slot.get('allocated_hours'), 'Allocated hours should be updated')

            # Unlink the public holiday
            public_holiday.unlink()
            self.assertDictEqual(initial_slot, {
                'allocated_hours': slot.allocated_hours
                }, "The Working days and Allocated hours should be updated")

    def test_half_day_employee_leave(self):
        leave_1, leave_2 = self.env['hr.leave'].create([{
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-01-01 09:00:00',
            'request_date_to': '2020-01-01 13:00:00',
            'request_unit_half': True,
            'request_date_from_period': 'am',
        }, {
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-01-02 14:00:00',
            'request_date_to': '2020-01-02 18:00:00',
            'request_unit_half': True,
            'request_date_from_period': 'pm',
        }])

        slot_1, slot_2 = self.env['planning.slot'].create([{
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 1, 9, 0),
            'end_datetime': datetime.datetime(2020, 1, 1, 13, 0),
        }, {
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 2, 14, 0),
            'end_datetime': datetime.datetime(2020, 1, 2, 18, 0),
        }])
        slot_3 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 3, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 3, 17, 0),
        })

        self.assertNotEqual(slot_1.leave_warning, False,
                             "Leave is not validated, but there is a warning for requested time off")
        self.assertNotEqual(slot_2.leave_warning, False,
                             "Leave is not validated, but there is a warning for requested time off")

        (leave_1 + leave_2).action_validate()

        self.assertNotEqual(slot_1.leave_warning, False,
                             "Employee is on leave, there should be a warning")
        self.assertNotEqual(slot_2.leave_warning, False,
                             "Employee is on leave, there should be a warning")
        self.assertEqual(
            re.sub(r'\s+', ' ', slot_1.leave_warning),
            "bert requested time off on 01/01/2020 from 9:00 AM to 1:00 PM. ",
        )
        self.assertEqual(
            re.sub(r'\s+', ' ', slot_2.leave_warning),
            "bert requested time off on 01/02/2020 from 2:00 PM to 6:00 PM. ",
        )
        self.assertEqual(slot_3.leave_warning, False,
                         "Employee is not on leave, there should be no warning")

    def test_progress_bar_with_holiday(self):
        """
        Test Case
        ---------
            1) Create one day time-off
            2) Create weekly shift
            3) Calculate percentage and verify
        """
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-1-9',
            'request_date_to': '2020-1-9',
        }).action_validate()

        self.env['planning.slot'].sudo().create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 7, 0, 0),
            'end_datetime': datetime.datetime(2020, 1, 10, 17, 0),
        })
        planning_hours_info = self.env['planning.slot']._gantt_progress_bar(
            'resource_id', self.resource_bert.ids, datetime.datetime(2020, 1, 5, 8, 0), datetime.datetime(2020, 1, 11, 17, 0)
        )
        self.assertEqual(75, (planning_hours_info[self.resource_bert.id]['value'] / planning_hours_info[self.resource_bert.id]['max_value']) * 100)

    def test_half_day_off_leave_of_flexible_resource(self):
        """
        Test half-day off leave for a flexible resource.
        The leave intervals should be set to 00:00:00 - 12:00:00 for AM half-day off
        and 12:00:00 - 23:59:59 for PM half-day off in the planning_gantt view.
        """
        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flex Calendar',
            'tz': 'UTC',
            'flexible_hours': True,
            'hours_per_day': 8,
            'full_time_required_hours': 40,
            'attendance_ids': [],
        })
        employee = self.employee_bert
        employee.resource_calendar_id = flexible_calendar

        # Test AM half-day leave
        leave_am = self.env['hr.leave'].sudo().create({
            'name': 'AM Half Day Off',
            'employee_id': employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2025-03-05',
            'request_date_to': '2025-03-05',
            'request_unit_half': True,
            'request_date_from_period': 'am',
            'state': 'confirm',
        })
        leave_am.sudo().action_validate()

        start_dt_am = datetime.datetime(2025, 3, 5, 8, 0, 0, tzinfo=utc)
        end_dt_am = datetime.datetime(2025, 3, 5, 12, 0, 0, tzinfo=utc)

        intervals_am = flexible_calendar._leave_intervals_batch(start_dt_am, end_dt_am, [employee.resource_id])
        intervals_list_am = list(intervals_am[employee.resource_id.id])
        self.assertEqual(len(intervals_list_am), 1, "There should be one leave interval for AM half-day")
        interval_am = intervals_list_am[0]
        self.assertEqual(interval_am[0], start_dt_am, "The start of the interval should be 08:00:00")
        self.assertEqual(interval_am[1], end_dt_am, "The end of the interval should be 12:00:00")

        # Test PM half-day leave on next day
        leave_pm = self.env['hr.leave'].sudo().create({
            'name': 'PM Half Day Off',
            'employee_id': employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2025-03-06',
            'request_date_to': '2025-03-06',
            'request_unit_half': True,
            'request_date_from_period': 'pm',
            'state': 'confirm',
        })
        leave_pm.sudo().action_validate()

        start_dt_pm = datetime.datetime(2025, 3, 6, 12, 0, 0, tzinfo=utc)
        end_dt_pm = datetime.datetime(2025, 3, 6, 16, 0, 0, 0, tzinfo=utc)

        intervals_pm = flexible_calendar._leave_intervals_batch(start_dt_pm, end_dt_pm, [employee.resource_id])
        intervals_list_pm = list(intervals_pm[employee.resource_id.id])
        self.assertEqual(len(intervals_list_pm), 1, "There should be one leave interval for PM half-day")
        interval_pm = intervals_list_pm[0]
        self.assertEqual(interval_pm[0], datetime.datetime(2025, 3, 6, 12, 0, 0, tzinfo=utc), "The start of the interval should be 12:00:00")
        self.assertEqual(interval_pm[1], end_dt_pm, "The end of the interval should be 16:00:00")

    def test_multiple_leaves_with_one_refusal_and_approval(self):
        """
        Test by creating 2 leaves for same date and same employee
        having a resource calendar of flexible hours with state of
        one refused and another approved.
        """
        self.employee_bert.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Flex Calendar',
            'tz': 'UTC',
            'flexible_hours': True,
            'hours_per_day': 8,
            'full_time_required_hours': 40,
            'attendance_ids': [],
        })
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-1-6',
            'request_date_to': '2020-1-7',
        }).action_refuse()
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2020-1-6',
            'request_date_to': '2020-1-7',
        }).action_validate()

        slot_1 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 6, 17, 0),
        })

        self.assertEqual(slot_1.leave_warning,
                         "bert is on time off from 01/06/2020 to 01/07/2020. \n")

    def test_two_half_day_off_leaves_on_same_day_of_flexible_resource(self):
        """
        Test half-day off leave for a flexible resource.
        The leave intervals should be set to 08:00:00 - 16:00:00
        if 2 half-day offs on the same day(am and pm).
        """
        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flex Calendar',
            'tz': 'UTC',
            'flexible_hours': True,
            'hours_per_day': 8,
            'full_time_required_hours': 40,
            'attendance_ids': [],
        })
        self.employee_bert.resource_calendar_id = flexible_calendar
        leave_am, leave_pm = self.env['hr.leave'].sudo().create([
            {
                'name': 'AM Half Day Off',
                'employee_id': self.employee_bert.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2025-04-30',
                'request_date_to': '2025-04-30',
                'request_unit_half': True,
                'request_date_from_period': 'am',
                'state': 'confirm',
            }, {
                'name': 'PM Half Day Off',
                'employee_id': self.employee_bert.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2025-04-30',
                'request_date_to': '2025-04-30',
                'request_unit_half': True,
                'request_date_from_period': 'pm',
                'state': 'confirm',
            },
        ])
        leave_am.sudo().action_validate()
        leave_pm.sudo().action_validate()
        start_dt = datetime.datetime(2025, 4, 30, 0, 0, 0, tzinfo=utc)
        end_dt = datetime.datetime(2025, 4, 30, 23, 59, 59, 999999, tzinfo=utc)
        intervals = flexible_calendar._leave_intervals_batch(start_dt, end_dt, [self.employee_bert.resource_id])
        interval = next(iter(intervals[self.employee_bert.resource_id.id]))
        self.assertEqual(interval[0], datetime.datetime(2025, 4, 30, 8, 0, 0, tzinfo=utc), "The start of the interval should be 08:00:00")
        self.assertEqual(interval[1], datetime.datetime(2025, 4, 30, 16, 0, 0, tzinfo=utc), "The end of the interval should be 16:00:00")

    def test_planning_gantt_unavailabilities_flexible_employee_public_holiday(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'UTC',
        })
        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flex Calendar',
            'tz': 'UTC',
            'flexible_hours': True,
            'hours_per_day': 8,
            'full_time_required_hours': 40,
            'attendance_ids': [],
        })
        employee.resource_calendar_id = flexible_calendar

        public_holiday = self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime.datetime(2019, 1, 5, 0, 0, 0),
            'date_to': datetime.datetime(2019, 1, 5, 23, 59, 59),
        })

        unavailabilities = self.env['planning.slot']._gantt_unavailability(
            'resource_id',
            [employee.resource_id.id],
            datetime.datetime(2019, 1, 1),
            datetime.datetime(2019, 1, 7),
            'week',
        )

        self.assertEqual(unavailabilities[employee.resource_id.id][0]['start'], public_holiday.date_from.astimezone(utc))
        self.assertEqual(unavailabilities[employee.resource_id.id][0]['stop'], public_holiday.date_to.astimezone(utc))
