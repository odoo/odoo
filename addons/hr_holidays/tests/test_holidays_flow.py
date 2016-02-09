# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo.fields import Date, Datetime
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import test_reports
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


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
                self.user_hr_user_id).create({
                    'name': 'UserCheats',
                    'limit': True,
                })

        # HrManager creates some holiday statuses
        self.holidays_status_0 = self.HrHolidaysStatus.sudo(self.user_hr_manager_id).create({
            'name': 'WithMeetingType',
            'limit': True,
            'categ_id': self.env['calendar.event.type'].sudo(self.user_hr_manager_id).create({'name': 'NotLimitedMeetingType'}).id,
        }).id
        self.holidays_status_1 = self.HrHolidaysStatus.sudo(self.user_hr_manager_id).create({
            'name': 'NotLimited',
            'limit': True,
        }).id
        self.holidays_status_2 = self.HrHolidaysStatus.sudo(self.user_hr_manager_id).create({
            'name': 'Limited',
            'limit': False,
            'double_validation': True,
        }).id

        now = Datetime.from_string(Datetime.now())
        # --------------------------------------------------
        # Case1: unlimited type of leave request
        # --------------------------------------------------

        # Employee creates a leave request for another employee -> should crash
        with self.assertRaises(ValidationError):
            self.HrHolidays.sudo(self.user_employee_id).create({
                'name': 'holiday110',
                'employee_id': self.emp_hr_user_id,
                'holiday_status_id': self.holidays_status_1,
                'date_from': now - relativedelta(days=1),
                'date_to': now,
                'number_of_days_temp': 1,
            })
        self.HrHolidays.search([('name', '=', 'holiday110')]).unlink()

        # Employee creates a leave request in a no-limit category
        holiday11 = self.HrHolidays.sudo(self.user_employee_id).create({
            'name': 'holiday111',
            'employee_id': self.emp_user_id,
            'holiday_status_id': self.holidays_status_1,
            'date_from': now - relativedelta(days=1),
            'date_to': now,
            'number_of_days_temp': 1,
        })
        self.assertEqual(holiday11.state, 'confirm', 'hr_holidays: newly created leave request should be in confirm state')

        # Employee validates its leave request -> should not work
        holiday11.sudo(self.user_employee_id).signal_workflow('validate')
        holiday11.refresh()
        self.assertEqual(holiday11.state, 'confirm', 'hr_holidays: employee should not be able to validate its own leave request')

        # HrUser validates the employee leave request
        holiday11.sudo(self.user_hr_manager_id).signal_workflow('validate')
        holiday11.refresh()
        self.assertEqual(holiday11.state, 'validate', 'hr_holidays: validates leave request should be in validate state')

        # --------------------------------------------------
        # Case2: limited type of leave request
        # --------------------------------------------------

        # Employee creates a new leave request at the same time -> crash, avoid interlapping
        with self.assertRaises(ValidationError):
            self.HrHolidays.sudo(self.user_employee_id).create({
                'name': 'Hol21',
                'employee_id': self.emp_user_id,
                'holiday_status_id': self.holidays_status_1,
                'date_from': (now - relativedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                'date_to': now,
                'number_of_days_temp': 1,
            })

        # Employee creates a leave request in a limited category -> crash, not enough days left
        with self.assertRaises(ValidationError):
            self.HrHolidays.sudo(self.user_employee_id).create({
                'name': 'Hol22',
                'employee_id': self.emp_user_id,
                'holiday_status_id': self.holidays_status_2,
                'date_from': now.strftime('%Y-%m-%d %H:%M'),
                'date_to': now + relativedelta(days=1),
                'number_of_days_temp': 1,
            })

        # Clean transaction
        self.HrHolidays.search([('name', 'in', ['Hol21', 'Hol22'])]).unlink()

        # HrUser allocates some leaves to the employee
        allocation1 = self.HrHolidays.sudo(self.user_hr_user_id).create({
            'name': 'Days for limited category',
            'employee_id': self.emp_user_id,
            'holiday_status_id': self.holidays_status_2,
            'type': 'add',
            'number_of_days_temp': 2,
        })
        # HrUser validates the allocation request
        allocation1.sudo(self.user_hr_user_id).signal_workflow('validate')
        allocation1.sudo(self.user_hr_user_id).signal_workflow('second_validate')
        # Checks Employee has effectively some days left
        hol_status_2 = self.HrHolidaysStatus.sudo(self.user_employee_id).browse(self.holidays_status_2)
        _check_holidays_status(hol_status_2, 2.0, 0.0, 2.0, 2.0)

        # Employee creates a leave request in the limited category, now that he has some days left
        holiday21 = self.HrHolidays.sudo(self.user_employee_id).create({
            'name': 'Hol22',
            'employee_id': self.emp_user_id,
            'holiday_status_id': self.holidays_status_2,
            'date_from': (now + relativedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
            'date_to': now + relativedelta(days=3),
            'number_of_days_temp': 1,
        })
        # Check left days: - 1 virtual remaining day
        hol_status_2.refresh()
        _check_holidays_status(hol_status_2, 2.0, 0.0, 2.0, 1.0)

        # HrUser validates the first step
        holiday21.sudo(self.user_hr_user_id).signal_workflow('validate')
        holiday21.refresh()
        self.assertEqual(holiday21.state, 'validate1',
                         'hr_holidays: first validation should lead to validate1 state')

        # HrUser validates the second step
        holiday21.sudo(self.user_hr_user_id).signal_workflow('second_validate')
        holiday21.refresh()
        self.assertEqual(holiday21.state, 'validate',
                         'hr_holidays: second validation should lead to validate state')
        # Check left days: - 1 day taken
        hol_status_2.refresh()
        _check_holidays_status(hol_status_2, 2.0, 1.0, 1.0, 1.0)

        # HrManager finds an error: he refuses the leave request
        holiday21.sudo(self.user_hr_manager_id).signal_workflow('refuse')
        holiday21.refresh()
        self.assertEqual(holiday21.state, 'refuse',
                         'hr_holidays: refuse should lead to refuse state')
        # Check left days: 2 days left again
        hol_status_2.refresh()
        _check_holidays_status(hol_status_2, 2.0, 0.0, 2.0, 2.0)

        # Annoyed, HrUser tries to fix its error and tries to reset the leave request -> does not work, only HrManager
        holiday21.sudo(self.user_hr_user_id).signal_workflow('reset')
        self.assertEqual(holiday21.state, 'refuse',
                         'hr_holidays: hr_user should not be able to reset a refused leave request')

        # HrManager resets the request
        holiday21.sudo(self.user_hr_manager_id).signal_workflow('reset')
        holiday21.refresh()
        self.assertEqual(holiday21.state, 'draft',
                         'hr_holidays: resetting should lead to draft state')

        # HrManager changes the date and put too much days -> crash when confirming
        holiday21.sudo(self.user_hr_manager_id).write({
            'date_from': (now + relativedelta(days=4)).strftime('%Y-%m-%d %H:%M'),
            'date_to': now + relativedelta(days=7),
            'number_of_days_temp': 4,
        })
        with self.assertRaises(ValidationError):
            holiday21.sudo(self.user_hr_manager_id).signal_workflow('confirm')

        # In order to test the hr_holiday module in Odoo, I will  Allocate leaves for Employee and manage leaves and leaves requests.

        # I assign the dates in the holiday request.
        hr_holiday1 = self.HrHolidays.create({
            'name': 'Sick Leave',
            'holiday_status_id': self.ref('hr_holidays.holiday_status_cl'),
            'date_from': now + relativedelta(day=10, hour=10, minute=0, second=0),
            'date_to': now + relativedelta(day=10, hour=19, minute=0, second=0),
            'type': 'remove',
        })

        hr_holidays_employee1_cl = self.env.ref('hr_holidays.hr_holidays_employee1_cl')
        # I find a small mistake on my leave request to I click on "Refuse" button to correct a mistake.
        hr_holidays_employee1_cl.signal_workflow('refuse')

        # I again set to draft and then confirm.
        hr_holidays_employee1_cl.holidays_reset()
        hr_holidays_employee1_cl.signal_workflow('confirm')

        # I validate the holiday request by clicking on "To Approve" button.
        hr_holidays_employee1_cl.signal_workflow('validate')

        # I can also see Summary of Employee's holiday by using "Employee's Holidays" Report. This report will allows to choose to print holidays with state Confirmed, Validated or both.

        # Print the HR Holidays(Summary Department) Report through the wizard

        date_from = Date.from_string(Date.today()) + relativedelta(day=01)
        context = {'model': 'hr.department','active_ids': [self.ref('hr.employee_fp'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')]}
        data_dict = {'date_from': date_from, 'depts' : [(6, 0, [self.ref('hr.dep_sales')])],'holiday_type' : 'Approved'}
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_hr_holidays_summary_dept', wiz_data=data_dict, context=context, our_module='hr_holidays')

        # Print the HR Holidays(Summary Employee) Report through the wizard
        context = {'model': 'hr.employee', 'active_ids': [self.ref('hr.employee_fp'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')]}
        data_dict = {'date_from': date_from, 'emp' : [(6, 0, [self.ref('hr.employee_fp'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')])],'holiday_type' : 'Approved'}
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_hr_holidays_summary_employee', wiz_data=data_dict, context=context, our_module='hr_holidays')
