# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools import mute_logger, test_reports

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase


class TestHolidaysFlow(TestHrHolidaysBase):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_00_leave_request_flow(self):
        """ Testing leave request flow """
        Requests = self.env['hr.leave']
        Allocations = self.env['hr.leave.allocation']
        HolidaysStatus = self.env['hr.leave.type']

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
            HolidaysStatus.sudo(self.user_hruser_id).create({
                'name': 'UserCheats',
                'limit': True,
            })

        # HrManager creates some holiday statuses
        HolidayStatusManagerGroup = HolidaysStatus.sudo(self.user_hrmanager_id)
        HolidayStatusManagerGroup.create({
            'name': 'WithMeetingType',
            'limit': True,
            'categ_id': self.env['calendar.event.type'].sudo(self.user_hrmanager_id).create({'name': 'NotLimitedMeetingType'}).id
        })
        self.holidays_status_1 = HolidayStatusManagerGroup.create({
            'name': 'NotLimited',
            'limit': True,
        })
        self.holidays_status_2 = HolidayStatusManagerGroup.create({
            'name': 'Limited',
            'limit': False,
            'double_validation': True,
        })

        # --------------------------------------------------
        # Case1: unlimited type of leave request
        # --------------------------------------------------

        # Employee creates a leave request for another employee -> should crash
        HolidaysEmployeeGroup = Requests.sudo(self.user_employee_id)
        with self.assertRaises(ValidationError):
            HolidaysEmployeeGroup.create({
                'name': 'Hol10',
                'employee_id': self.employee_hruser_id,
                'holiday_status_id': self.holidays_status_1.id,
                'date_from': (datetime.today() - relativedelta(days=1)),
                'date_to': datetime.today(),
                'number_of_days_temp': 1,
            })
        Requests.search([('name', '=', 'Hol10')]).unlink()

        # Employee creates a leave request in a no-limit category
        hol1_employee_group = HolidaysEmployeeGroup.create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_1.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days_temp': 1,
        })
        hol1_user_group = hol1_employee_group.sudo(self.user_hruser_id)
        self.assertEqual(hol1_user_group.state, 'confirm', 'hr_holidays: newly created leave request should be in confirm state')

        # Employee validates its leave request -> should not work
        with self.assertRaises(UserError):
            hol1_employee_group.action_approve()
        self.assertEqual(hol1_user_group.state, 'confirm', 'hr_holidays: employee should not be able to validate its own leave request')

        # HrUser validates the employee leave request
        hol1_user_group.action_approve()
        self.assertEqual(hol1_user_group.state, 'validate', 'hr_holidays: validates leave request should be in validate state')

        # --------------------------------------------------
        # Case2: limited type of leave request
        # --------------------------------------------------

        # Employee creates a new leave request at the same time -> crash, avoid interlapping
        with self.assertRaises(ValidationError):
            HolidaysEmployeeGroup.create({
                'name': 'Hol21',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_status_1.id,
                'date_from': (datetime.today() - relativedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                'date_to': datetime.today(),
                'number_of_days_temp': 1,
            })

        # Employee creates a leave request in a limited category -> crash, not enough days left
        with self.assertRaises(ValidationError):
            HolidaysEmployeeGroup.create({
                'name': 'Hol22',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_status_2.id,
                'date_from': (datetime.today() + relativedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                'date_to': (datetime.today() + relativedelta(days=2)),
                'number_of_days_temp': 1,
            })

        # Clean transaction
        Requests.search([('name', 'in', ['Hol21', 'Hol22'])]).unlink()

        # HrUser allocates some leaves to the employee
        aloc1_user_group = Allocations.sudo(self.user_hruser_id).create({
            'name': 'Days for limited category',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_2.id,
            'number_of_days_temp': 2,
        })
        # HrUser validates the first step
        aloc1_user_group.action_approve()
        # HrManager validates the second step
        aloc1_user_group.sudo(self.user_hrmanager_id).action_validate()
        # Checks Employee has effectively some days left
        hol_status_2_employee_group = self.holidays_status_2.sudo(self.user_employee_id)
        _check_holidays_status(hol_status_2_employee_group, 2.0, 0.0, 2.0, 2.0)

        # Employee creates a leave request in the limited category, now that he has some days left
        hol2 = HolidaysEmployeeGroup.create({
            'name': 'Hol22',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_2.id,
            'date_from': (datetime.today() + relativedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=3)),
            'number_of_days_temp': 1,
        })
        hol2_user_group = hol2.sudo(self.user_hruser_id)
        # Check left days: - 1 virtual remaining day
        _check_holidays_status(hol_status_2_employee_group, 2.0, 0.0, 2.0, 1.0)

        # HrUser validates the first step
        hol2_user_group.action_approve()
        self.assertEqual(hol2.state, 'validate1',
                         'hr_holidays: first validation should lead to validate1 state')

        # HrManager validates the second step
        hol2_user_group.sudo(self.user_hrmanager_id).action_validate()
        self.assertEqual(hol2.state, 'validate',
                         'hr_holidays: second validation should lead to validate state')
        # Check left days: - 1 day taken
        _check_holidays_status(hol_status_2_employee_group, 2.0, 1.0, 1.0, 1.0)

        # HrManager finds an error: he refuses the leave request
        hol2.sudo(self.user_hrmanager_id).action_refuse()
        self.assertEqual(hol2.state, 'refuse',
                         'hr_holidays: refuse should lead to refuse state')
        # Check left days: 2 days left again
        _check_holidays_status(hol_status_2_employee_group, 2.0, 0.0, 2.0, 2.0)

        # Annoyed, HrUser tries to fix its error and tries to reset the leave request -> does not work, only HrManager
        with self.assertRaises(UserError):
            hol2_user_group.action_draft()
        self.assertEqual(hol2.state, 'refuse',
                         'hr_holidays: hr_user should not be able to reset a refused leave request')

        # HrManager resets the request
        hol2_manager_group = hol2.sudo(self.user_hrmanager_id)
        hol2_manager_group.action_draft()
        self.assertEqual(hol2.state, 'draft',
                         'hr_holidays: resetting should lead to draft state')

        # HrManager changes the date and put too much days -> crash when confirming
        hol2_manager_group.write({
            'date_from': (datetime.today() + relativedelta(days=4)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=7)),
            'number_of_days_temp': 4,
        })
        with self.assertRaises(ValidationError):
            hol2_manager_group.action_confirm()

        employee_id = self.ref('hr.employee_root')
        # cl can be of maximum 20 days for employee_root
        hol3_status = self.env.ref('hr_holidays.holiday_status_cl').with_context(employee_id=employee_id)
        # I assign the dates in the holiday request for 1 day
        hol3 = Requests.create({
            'name': 'Sick Leave',
            'holiday_status_id': hol3_status.id,
            'date_from': datetime.today().strftime('%Y-%m-10 10:00:00'),
            'date_to': datetime.today().strftime('%Y-%m-11 19:00:00'),
            'employee_id': employee_id,
            'number_of_days_temp': 1
        })
        # I find a small mistake on my leave request to I click on "Refuse" button to correct a mistake.
        hol3.action_refuse()
        self.assertEqual(hol3.state, 'refuse', 'hr_holidays: refuse should lead to refuse state')
        # I again set to draft and then confirm.
        hol3.action_draft()
        self.assertEqual(hol3.state, 'draft', 'hr_holidays: resetting should lead to draft state')
        hol3.action_confirm()
        self.assertEqual(hol3.state, 'confirm', 'hr_holidays: confirming should lead to confirm state')
        # I validate the holiday request by clicking on "To Approve" button.
        hol3.action_approve()
        self.assertEqual(hol3.state, 'validate', 'hr_holidays: validation should lead to validate state')
        # Check left days for casual leave: 19 days left
        _check_holidays_status(hol3_status, 20.0, 1.0, 19.0, 19.0)

    def test_10_leave_summary_reports(self):
        # Print the HR Holidays(Summary Department) Report through the wizard
        ctx = {
            'model': 'hr.department',
            'active_ids': [self.ref('hr.employee_root'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')]
        }
        data_dict = {
            'date_from': datetime.today().strftime('%Y-%m-01'),
            'depts': [(6, 0, [self.ref('hr.dep_sales')])],
            'holiday_type': 'Approved'
        }
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_hr_holidays_summary_dept', wiz_data=data_dict, context=ctx, our_module='hr_holidays')

        # Print the HR Holidays(Summary Employee) Report through the wizard
        ctx = {
            'model': 'hr.employee',
            'active_ids': [self.ref('hr.employee_root'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')]
        }
        data_dict = {
            'date_from': datetime.today().strftime('%Y-%m-01'),
            'emp': [(6, 0, [self.ref('hr.employee_root'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')])],
            'holiday_type': 'Approved'
        }
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_hr_holidays_summary_employee', wiz_data=data_dict, context=ctx, our_module='hr_holidays')
