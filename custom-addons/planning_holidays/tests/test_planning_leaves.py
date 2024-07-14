# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from freezegun import freeze_time
from .test_common import TestCommon


@freeze_time('2020-01-01')
class TestPlanningLeaves(TestCommon):
    def test_simple_employee_leave(self):
        leave = self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.patrick.id,
            'request_date_from': '2020-1-1',
            'request_date_to': '2020-1-1',
        })

        slot_1 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 1, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 1, 17, 0),
        })
        slot_2 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 2, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 2, 17, 0),
        })

        self.assertNotEqual(slot_1.leave_warning, False,
                    "leave is not validated , but warning for requested time off")

        leave.action_validate()

        self.assertNotEqual(slot_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        # The warning should display the whole concerned leave period
        self.assertEqual(slot_1.leave_warning,
                         "patrick is on time off from 01/01/2020 at 09:00:00 to 01/01/2020 at 18:00:00. \n")

        self.assertEqual(slot_2.leave_warning, False,
                         "employee is not on leave, no warning")

    def test_multiple_leaves(self):
        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.patrick.id,
            'request_date_from': '2020-1-6',
            'request_date_to': '2020-1-7',
        }).action_validate()

        self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.patrick.id,
            'request_date_from': '2020-1-8',
            'request_date_to': '2020-1-10',
        }).action_validate()

        slot_1 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 6, 17, 0),
        })

        self.assertNotEqual(slot_1.leave_warning, False,
                            "employee is on leave, should have a warning")
        # The warning should display the whole concerned leave period
        self.assertEqual(slot_1.leave_warning,
                         "patrick is on time off from 01/06/2020 to 01/07/2020. \n")

        slot_2 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 7, 17, 0),
        })
        self.assertEqual(slot_2.leave_warning,
                         "patrick is on time off from 01/06/2020 to 01/07/2020. \n")

        slot_3 = self.env['planning.slot'].create({
            'resource_id': self.res_patrick.id,
            'start_datetime': datetime.datetime(2020, 1, 6, 8, 0),
            'end_datetime': datetime.datetime(2020, 1, 10, 17, 0),
        })
        self.assertEqual(slot_3.leave_warning, "patrick is on time off from 01/06/2020 to 01/10/2020. \n",
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
                'working_day': slot.working_days_count,
                'allocated_hours': slot.allocated_hours,
            }

            # Add the public holiday
            public_holiday = self.env['resource.calendar.leaves'].create({
                'name': 'Public holiday',
                'calendar_id': ethan.resource_id.calendar_id.id,
                'date_from': datetime.datetime(2020, 4, 21, 8, 0), # Wednesday
                'date_to': datetime.datetime(2020, 4, 21, 17, 0),
            })

            self.assertNotEqual(slot.working_days_count, initial_slot.get('working_day'), 'Working days should be updated')
            self.assertNotEqual(slot.allocated_hours, initial_slot.get('allocated_hours'), 'Allocated hours should be updated')

            # Unlink the public holiday
            public_holiday.unlink()
            self.assertDictEqual(initial_slot, {
                'working_day': slot.working_days_count,
                'allocated_hours': slot.allocated_hours
                }, "The Working days and Allocated hours should be updated")
