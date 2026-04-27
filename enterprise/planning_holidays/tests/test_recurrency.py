# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from .test_common import TestCommon

class TestPlanningLeaves(TestCommon):
    def test_recurrency_public_holiday(self):
        # Create a public holiday
        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'calendar_id': self.calendar.id,
            'date_from': datetime(2024, 3, 13, 7, 0),
            'date_to': datetime(2024, 3, 13, 16, 0),
        })
        occuring_slot = self.env['planning.slot'].create({  # this should land on a Monday
            'start_datetime': self.random_monday_date + timedelta(hours=8),
            'end_datetime': self.random_monday_date + timedelta(hours=10),
            'resource_id': self.resource_bert.id,
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2024, 3, 15, 17, 0),
            'repeat_interval': 1,
            'repeat_unit': 'day',
        })

        self.assertEqual(
            len(occuring_slot.recurrency_id.slot_ids),
            4,
            'Since one of the recurring shifts land on a public holiday, it won\'t be generated and thus only 4 shifts will be generated.'
        )

    def test_recurrency_employee_leave(self):
        leave = self.env['hr.leave'].sudo().create({
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_bert.id,
            'request_date_from': '2024-3-13',
            'request_date_to': '2024-3-13',
        })  # time off should land on Wednesday
        leave.action_validate()

        occuring_slot = self.env['planning.slot'].create({  # this should land on a Monday
            'start_datetime': self.random_monday_date + timedelta(hours=8),
            'end_datetime': self.random_monday_date + timedelta(hours=10),
            'resource_id': self.resource_bert.id,
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2024, 3, 15, 17, 0),
            'repeat_interval': 1,
            'repeat_unit': 'day',
        })

        self.assertEqual(
            len(occuring_slot.recurrency_id.slot_ids),
            5,
            'All recurrent slots should be generated.'
        )
        self.assertEqual(
            len([slot for slot in occuring_slot.recurrency_id.slot_ids if slot.resource_id]),
            4,
            'Four out of the five slots should have been normally generated and assigned to resource bert, since he is available on those dates.'
        )
        self.assertFalse(
            occuring_slot.recurrency_id.slot_ids[2].resource_id,
            'Since the resource is on time-off on Wednesday, the recurring shift will be generated as an open shift.'
        )
