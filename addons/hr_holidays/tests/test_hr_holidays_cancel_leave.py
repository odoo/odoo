# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.exceptions import UserError, ValidationError

from .common import TestHrHolidaysCommon


class TestHrHolidaysCancelLeave(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        leave_start_date = date(2018, 2, 5)  # this is monday
        leave_end_date = leave_start_date + relativedelta(days=2)

        cls.hr_leave_type = cls.env['hr.leave.type'].with_user(cls.user_hrmanager).create({
            'name': 'Time Off Type',
            'requires_allocation': 'no',
        })
        cls.holiday = cls.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True).with_user(cls.user_employee).create({
            'name': 'Time Off 1',
            'employee_id': cls.employee_emp.id,
            'holiday_status_id': cls.hr_leave_type.id,
            'request_date_from': leave_start_date,
            'request_date_to': leave_end_date,
        })
        cls.holiday.with_user(cls.user_hrmanager).action_validate()

    @freeze_time('2018-02-05')  # useful to be able to cancel the validated time off
    def test_action_cancel_leave(self):
        self.assertTrue(self.holiday.with_user(self.user_employee).can_cancel)
        self.env['hr.holidays.cancel.leave'].with_user(self.user_employee).with_context(default_leave_id=self.holiday.id) \
            .new({'reason': 'Test remove holiday'}) \
            .action_cancel_leave()
        self.assertEqual(self.holiday.state, 'cancel', 'The validated leave should be canceled.')

    def test_action_cancel_leave_in_past(self):
        """ Test if the user may cancel a validated leave in the past. """
        with self.assertRaises(ValidationError, msg='The leave could not be cancel since it is leave in the past.'):
            self.env['hr.holidays.cancel.leave'].with_user(self.user_employee).with_context(default_leave_id=self.holiday.id) \
                .new({'reason': 'Test remove holiday'}) \
                .action_cancel_leave()

    def test_action_cancel_leave_from_another_person(self):
        """ Test if the user may cancel a validated leave from another person. """
        self.assertFalse(self.holiday.with_user(self.user_hruser).can_cancel, 'The user should not be able to cancel the leave from another one.')
        with self.assertRaises(ValidationError, msg='The leave could not be cancel since it is leave in the past.'):
            self.env['hr.holidays.cancel.leave'].with_user(self.user_hruser).with_context(default_leave_id=self.holiday.id) \
                .new({'reason': 'Test remove holiday'}) \
                .action_cancel_leave()

    @freeze_time('2018-02-05')  # useful to be able to cancel the validated time off
    def test_user_cannot_unarchive_leave(self):
        """ Test the user cannot manually unarchive a canceled leave """
        self.env['hr.holidays.cancel.leave'].with_user(self.user_employee).with_context(default_leave_id=self.holiday.id) \
            .new({'reason': 'Test remove holiday'}) \
            .action_cancel_leave()
        with self.assertRaises(UserError, msg='The user should not be able to manually unarchive the leave.'):
            self.holiday.with_user(self.user_employee).write({'state': 'cancel'})
