# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from openerp.exceptions import AccessError, ValidationError


class TestHolidaysFlow(TestHrHolidaysCommon):

    def test_00_leave_request_flow(self):
        """ Testing leave request flow """

        def _check_holidays_status(holiday_status, ml, lt, rl, vrl):
            self.assertEqual(holiday_status.max_leaves, ml,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.leaves_taken, lt,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.remaining_leaves, rl,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.virtual_remaining_leaves, vrl,
                             'hr_holidays: wrong type days computation')

        # HrUser creates some holiday statuses -> crash because only HrManagers should do this
        with self.assertRaises(AccessError):
            self.holidays_status_dummy = self.HrHolidaysStatus.sudo(
                user=self.res_users_hr_officer).create({
                    'name': 'UserCheats',
                    'limit': True,
                })

        # HrManager creates some holiday statuses
        self.holidays_status_0 = self.HrHolidaysStatus.sudo(user=self.res_users_hr_manager).create({
            'name': 'Legal New Leaves',
            'limit': True,
            'categ_id': self.CalenderEventType.sudo(user=self.res_users_hr_manager).create({
                'name': 'NotLimitedMeetingType'
            }).id
        }).id
        self.holidays_status_1 = self.HrHolidaysStatus.sudo(user=self.res_users_hr_manager).create({
            'name': 'NotLimited',
            'limit': True
        }).id
        self.holidays_status_2 = self.HrHolidaysStatus.sudo(user=self.res_users_hr_manager).create({
            'name': 'Limited',
            'limit': False,
            'double_validation': True
        }).id

        # --------------------------------------------------
        # Case1: unlimited type of leave request
        # --------------------------------------------------

        # Employee creates a leave request for another employee -> should crash
        with self.assertRaises(ValidationError):
            self.HrHolidays.sudo(user=self.res_users_employee).create({
                'name': 'Holiday11',
                'employee_id': self.hr_employee_officer,
                'holiday_status_id': self.holidays_status_1,
                'date_from': (datetime.today() - relativedelta(days=1)),
                'date_to': datetime.today(),
                'number_of_days_temp': 1
            })
        holidays11 = self.HrHolidays.search([('name', '=', 'Holiday11')])
        holidays11.unlink()

        # Employee creates a leave request in a no-limit category
        holidays12 = self.HrHolidays.sudo(user=self.res_users_employee).create({
            'name': 'Holiday12',
            'employee_id': self.hr_employee_user,
            'holiday_status_id': self.holidays_status_1,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days_temp': 1,
        })
        self.assertEqual(holidays12.state, 'confirm',
            'hr_holidays: newly created leave request should be in confirm state')

        holidays12.sudo(user=self.res_users_employee).signal_workflow('validate')
        holidays12.refresh()
        self.assertEqual(holidays12.state, 'confirm',
            'hr_holidays: employee should not be able to validate its own leave request')

        # HrUser validates the employee leave request
        holidays12.sudo(user=self.res_users_hr_manager).signal_workflow('validate')
        holidays12.refresh()
        self.assertEqual(holidays12.state, 'validate',
            'hr_holidays: validates leave request should be in validate state')

        # --------------------------------------------------
        # Case2: limited type of leave request
        # --------------------------------------------------

        # Employee creates a new leave request at the same time -> crash, avoid interlapping
        with self.assertRaises(ValidationError):
            self.HrHolidays.sudo(user=self.res_users_employee).create({
                'name': 'Holiday21',
                'employee_id': self.hr_employee_user,
                'holiday_status_id': self.holidays_status_1,
                'date_from': (datetime.today() - relativedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                'date_to': datetime.today(),
                'number_of_days_temp': 1,
            })

        # Employee creates a leave request in a limited category -> crash, not enough days left
        with self.assertRaises(ValidationError):
            self.HrHolidays.sudo(user=self.res_users_employee).create({
                'name': 'Holiday22',
                'employee_id': self.hr_employee_user,
                'holiday_status_id': self.holidays_status_2,
                'date_from': (datetime.today() + relativedelta(days=0)).strftime('%Y-%m-%d %H:%M'),
                'date_to': (datetime.today() + relativedelta(days=1)),
                'number_of_days_temp': 1,
            })
        # Clean transaction
        holidays = self.HrHolidays.search([('name', 'in', ['Holiday21', 'Holiday22'])])
        holidays.unlink()

        # HrOfficer allocates some leaves to the employee
        allocation1 = self.HrHolidays.sudo(user=self.res_users_hr_officer).create({
            'name': 'Days for limited category',
            'employee_id': self.hr_employee_user,
            'holiday_status_id': self.holidays_status_2,
            'request_type': 'add',
            'number_of_days_temp': 2,
        })
        # HrOfficer validates the allocation request
        allocation1.sudo(user=self.res_users_hr_officer).signal_workflow('validate')
        allocation1.sudo(user=self.res_users_hr_officer).signal_workflow('second_validate')

        # Checks Employee has effectively some days left
        holidays_status = self.HrHolidaysStatus.sudo(user=self.res_users_employee).browse(
            self.holidays_status_2)
        _check_holidays_status(holidays_status, 2.0, 0.0, 2.0, 2.0)

        # Employee creates a leave request in the limited category, now that he has some days left
        holidays21 = self.HrHolidays.sudo(user=self.res_users_employee).create({
            'name': 'Holiday21',
            'employee_id': self.hr_employee_user,
            'holiday_status_id': self.holidays_status_2,
            'date_from': (datetime.today() + relativedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=3)),
            'number_of_days_temp': 1,
        })

        # Check left days: - 1 virtual remaining day
        holidays_status.refresh()
        _check_holidays_status(holidays_status, 2.0, 0.0, 2.0, 1.0)

        # HrOfficer validates the first step
        holidays21.sudo(user=self.res_users_hr_officer).signal_workflow('validate')
        holidays21.refresh()
        self.assertEqual(holidays21.state, 'validate1',
            'hr_holidays: first validation should lead to validate1 state')

        # HrOfficer validates the second step
        holidays21.sudo(user=self.res_users_hr_officer).signal_workflow('second_validate')
        holidays21.refresh()
        self.assertEqual(holidays21.state, 'validate',
            'hr_holidays: second validation should lead to validate state')

        # Check left days: - 1 day taken
        holidays_status.refresh()
        _check_holidays_status(holidays_status, 2.0, 1.0, 1.0, 1.0)

        # HrManager finds an error: he refuses the leave request
        holidays21.sudo(user=self.res_users_hr_manager).signal_workflow('refuse')
        holidays21.refresh()
        self.assertEqual(holidays21.state, 'refuse',
            'hr_holidays: refuse should lead to refuse state')

        # Check left days: 2 days left again
        holidays_status.refresh()
        _check_holidays_status(holidays_status, 2.0, 0.0, 2.0, 2.0)

        # HrOfficer fix its error and tries to reset the leave request (only HrManager)
        holidays21.sudo(user=self.res_users_hr_officer).signal_workflow('reset')
        self.assertEqual(holidays21.state, 'refuse',
            'hr_holidays: hr_user should not be able to reset a refused leave request')

        # HrManager resets the request
        holidays21.sudo(user=self.res_users_hr_manager).signal_workflow('reset')
        holidays21.refresh()
        self.assertEqual(holidays21.state, 'draft',
            'hr_holidays: resetting should lead to draft state')

        # HrManager changes the date and put too much days -> crash when confirming
        holidays21.sudo(user=self.res_users_hr_manager).write({
            'date_from': (datetime.today() + relativedelta(days=4)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=7)),
            'number_of_days_temp': 4,
        })
        with self.assertRaises(ValidationError):
            holidays21.sudo(user=self.res_users_hr_manager).signal_workflow('confirm')

        # --------------------------------------------------
        # This test case explain how to correct mistake, if
        # you accidently click on "refuse" button,
        # 1.) Allocate leaves
        # 2.) Validate leaves
        # 3.) Check sufficient leaves avaialble
        # 4.) Create leaves
        # 5.) by mistake "Refuse" button clicked
        # 6.) Clicking on "Reset to Draft" button
        # 7.) Click on "Confirm" button
        # 8.) and finally click on "To Approve" button
        # --------------------------------------------------

        # HrManager allocates some leaves
        allocation2 = self.HrHolidays.sudo(user=self.res_users_hr_manager).create({
            'name': 'Days for limited category',
            'employee_id': self.hr_employee_user,
            'holiday_status_id': self.holidays_status_0,
            'request_type': 'add',
            'number_of_days_temp': 2,
        })
        # HrManager validates the allocation request
        allocation2.sudo(user=self.res_users_hr_manager).signal_workflow('validate')
        allocation2.sudo(user=self.res_users_hr_manager).signal_workflow('second_validate')

        # HrManager check leaves has effectively some days left
        available_leaves = self.HrHolidaysStatus.sudo(user=self.res_users_employee).browse(
            self.holidays_status_0)
        _check_holidays_status(available_leaves, 2.0, 0.0, 2.0, 2.0)

        # HrManager creates a leave request in the limited category, and he has some days left
        holidays31 = self.HrHolidays.sudo(user=self.res_users_hr_manager).create({
            'name': 'Holiday31',
            'employee_id': self.hr_employee_user,
            'holiday_status_id': self.holidays_status_0,
            'date_from': (datetime.today() + relativedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=3)),
            'number_of_days_temp': 1,
        })

        # For this leave request, by mistake click on "Refuse" button
        holidays31.sudo(user=self.res_users_hr_manager).signal_workflow('refuse')
        holidays31.refresh()
        self.assertEqual(holidays31.state, 'refuse',
            'hr_holidays: small mistake, click on "Refuse" button')

        # For correct mistake clicking on "Reset to Draft" button
        holidays31.sudo(user=self.res_users_hr_manager).signal_workflow('reset')
        holidays31.refresh()
        self.assertEqual(holidays31.state, 'draft',
            'hr_holidays: "reset to draft" to correct a mistake')

        # Now in draft stage, click on "Confirm" button
        holidays31.sudo(user=self.res_users_hr_manager).signal_workflow('confirm')
        holidays31.refresh()
        self.assertEqual(holidays31.state, 'confirm',
            'hr_holidays: "confirm" the leave request')

        # validate the holiday request by clicking on "To Approve" button
        holidays31.sudo(user=self.res_users_hr_manager).signal_workflow('validate')
        holidays31.refresh()
        self.assertEqual(holidays31.state, 'validate',
            'hr_holidays: validate the holiday request by clicking on "To Approve" button.')
