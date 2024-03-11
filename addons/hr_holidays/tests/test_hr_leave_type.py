from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.exceptions import AccessError, ValidationError
from odoo.tools import date_utils

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveType(TestHrHolidaysCommon):

    def test_time_type(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': 'no',
        })

        leave_date = date_utils.start_of((date.today() - relativedelta(days=1)), 'week')
        leave_1 = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': leave_type.id,
            'request_date_from': leave_date,
            'request_date_to': leave_date,
        })
        leave_1.action_approve()

        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_1.id)]).time_type,
            'leave'
        )

    def test_type_creation_right(self):
        # HrUser creates some holiday statuses -> crash because only HrManagers should do this
        with self.assertRaises(AccessError):
            self.env['hr.leave.type'].with_user(self.user_hruser_id).create({
                'name': 'UserCheats',
                'requires_allocation': 'no',
            })

    def test_write_unchangeable_fields(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': 'no',
            'allocation_type': 'accrual',
            'request_unit': 'hour',
            'allows_negative': False,
            'max_allowed_negative': '1',
        })

        leave_type.requires_allocation = 'yes'
        leave_type.allocation_type = 'regular'

        self.env['hr.leave.allocation'].create([{
            'name': 'leave_type_regular allocation',
            'holiday_status_id': leave_type.id,
            'date_from': date(2024, 1, 1),
            'date_to': date(2024, 12, 31),
            'employee_id': self.employee_hruser_id,
            'allocation_type': 'regular',
            'number_of_days': 1,
        }])

        with self.assertRaises(ValidationError):
            leave_type.requires_allocation = 'no'
        with self.assertRaises(ValidationError):
            leave_type.allocation_type = 'regular'

        leave_type.allows_negative = True
        leave_type.max_allowed_negative = 16

        self.env['hr.leave'].create({
            'holiday_status_id': leave_type.id,
            'employee_id': self.employee_hruser_id,
            'request_date_from': date(2024, 3, 18),
            'request_date_to': date(2024, 3, 20),
        })

        leave_type.max_allowed_negative = 24
        leave_type.max_allowed_negative = 16
        with self.assertRaises(ValidationError):
            leave_type.allows_negative = False
        with self.assertRaises(ValidationError):
            leave_type.max_allowed_negative = 15
