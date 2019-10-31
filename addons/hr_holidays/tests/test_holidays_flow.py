# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import datetime
from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools import mute_logger, test_reports

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase


class TestHolidaysFlow(TestHrHolidaysBase):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_00_leave_request_flow_unlimited(self):
        """ Testing leave request flow: unlimited type of leave request """
        Requests = self.env['hr.leave']
        HolidaysStatus = self.env['hr.leave.type']

        # HrManager creates some holiday statuses
        HolidayStatusManagerGroup = HolidaysStatus.with_user(self.user_hrmanager_id)
        HolidayStatusManagerGroup.create({
            'name': 'WithMeetingType',
            'allocation_type': 'no',
        })
        self.holidays_status_hr = HolidayStatusManagerGroup.create({
            'name': 'NotLimitedHR',
            'allocation_type': 'no',
            'validation_type': 'hr',
            'validity_start': False,
        })
        self.holidays_status_manager = HolidayStatusManagerGroup.create({
            'name': 'NotLimitedManager',
            'allocation_type': 'no',
            'validation_type': 'manager',
            'validity_start': False,
        })

        HolidaysEmployeeGroup = Requests.with_user(self.user_employee_id)

        # Employee creates a leave request in a no-limit category hr manager only
        hol1_employee_group = HolidaysEmployeeGroup.create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_hr.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days': 1,
        })
        hol1_user_group = hol1_employee_group.with_user(self.user_hruser_id)
        hol1_manager_group = hol1_employee_group.with_user(self.user_hrmanager_id)
        self.assertEqual(hol1_user_group.state, 'confirm', 'hr_holidays: newly created leave request should be in confirm state')

        # HrUser validates the employee leave request -> should work
        hol1_user_group.action_approve()
        self.assertEqual(hol1_manager_group.state, 'validate', 'hr_holidays: validated leave request should be in validate state')

        # Employee creates a leave request in a no-limit category department manager only
        hol12_employee_group = HolidaysEmployeeGroup.create({
            'name': 'Hol12',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_manager.id,
            'date_from': (datetime.today() + relativedelta(days=12)),
            'date_to': (datetime.today() + relativedelta(days=13)),
            'number_of_days': 1,
        })
        hol12_user_group = hol12_employee_group.with_user(self.user_hruser_id)
        hol12_manager_group = hol12_employee_group.with_user(self.user_hrmanager_id)
        self.assertEqual(hol12_user_group.state, 'confirm', 'hr_holidays: newly created leave request should be in confirm state')

        # HrManager validate the employee leave request
        hol12_manager_group.action_approve()
        self.assertEqual(hol1_user_group.state, 'validate', 'hr_holidays: validates leave request should be in validate state')


    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_01_leave_request_flow_limited(self):
        """ Testing leave request flow: limited type of leave request """
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

        # HrManager creates some holiday statuses
        HolidayStatusManagerGroup = HolidaysStatus.with_user(self.user_hrmanager_id)
        HolidayStatusManagerGroup.create({
            'name': 'WithMeetingType',
            'allocation_type': 'no',
            'validity_start': False,
        })

        self.holidays_status_limited = HolidayStatusManagerGroup.create({
            'name': 'Limited',
            'allocation_type': 'fixed',
            'validation_type': 'both',
            'validity_start': False,
        })
        HolidaysEmployeeGroup = Requests.with_user(self.user_employee_id)

        # HrUser allocates some leaves to the employee
        aloc1_user_group = Allocations.with_user(self.user_hruser_id).create({
            'name': 'Days for limited category',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_limited.id,
            'number_of_days': 2,
        })
        # HrUser validates the first step
        aloc1_user_group.action_approve()

        # HrManager validates the second step
        aloc1_user_group.with_user(self.user_hrmanager_id).action_validate()
        # Checks Employee has effectively some days left
        hol_status_2_employee_group = self.holidays_status_limited.with_user(self.user_employee_id)
        _check_holidays_status(hol_status_2_employee_group, 2.0, 0.0, 2.0, 2.0)

        # Employee creates a leave request in the limited category, now that he has some days left
        hol2 = HolidaysEmployeeGroup.create({
            'name': 'Hol22',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_limited.id,
            'date_from': (datetime.today() + relativedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=3)),
            'number_of_days': 1,
        })
        hol2_user_group = hol2.with_user(self.user_hruser_id)
        # Check left days: - 1 virtual remaining day
        hol_status_2_employee_group.invalidate_cache()
        _check_holidays_status(hol_status_2_employee_group, 2.0, 0.0, 2.0, 1.0)

        # HrManager validates the first step
        hol2_user_group.with_user(self.user_hrmanager_id).action_approve()
        self.assertEqual(hol2.state, 'validate1',
                         'hr_holidays: first validation should lead to validate1 state')

        # HrManager validates the second step
        hol2_user_group.with_user(self.user_hrmanager_id).action_validate()
        self.assertEqual(hol2.state, 'validate',
                         'hr_holidays: second validation should lead to validate state')
        # Check left days: - 1 day taken
        _check_holidays_status(hol_status_2_employee_group, 2.0, 1.0, 1.0, 1.0)

        # HrManager finds an error: he refuses the leave request
        hol2.with_user(self.user_hrmanager_id).action_refuse()
        self.assertEqual(hol2.state, 'refuse',
                         'hr_holidays: refuse should lead to refuse state')
        # Check left days: 2 days left again

        hol_status_2_employee_group.invalidate_cache(['max_leaves'])
        _check_holidays_status(hol_status_2_employee_group, 2.0, 0.0, 2.0, 2.0)

        self.assertEqual(hol2.state, 'refuse',
                         'hr_holidays: hr_user should not be able to reset a refused leave request')

        # HrManager resets the request
        hol2_manager_group = hol2.with_user(self.user_hrmanager_id)
        hol2_manager_group.action_draft()
        self.assertEqual(hol2.state, 'draft',
                         'hr_holidays: resetting should lead to draft state')

        employee_id = self.ref('hr.employee_admin')
        # cl can be of maximum 20 days for employee_admin
        hol3_status = self.env.ref('hr_holidays.holiday_status_cl').with_context(employee_id=employee_id)
        # I assign the dates in the holiday request for 1 day
        hol3 = Requests.create({
            'name': 'Sick Time Off',
            'holiday_status_id': hol3_status.id,
            'date_from': datetime.today().strftime('%Y-%m-10 10:00:00'),
            'date_to': datetime.today().strftime('%Y-%m-11 19:00:00'),
            'employee_id': employee_id,
            'number_of_days': 1,
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
        hol3.action_validate()
        self.assertEqual(hol3.state, 'validate', 'hr_holidays: validation should lead to validate state')
        # Check left days for casual leave: 19 days left
        _check_holidays_status(hol3_status, 20.0, 1.0, 19.0, 19.0)

    def test_10_leave_summary_reports(self):
        # Print the HR Holidays(Summary Employee) Report through the wizard
        ctx = {
            'model': 'hr.employee',
            'active_ids': [self.ref('hr.employee_admin'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')]
        }
        data_dict = {
            'date_from': datetime.today().strftime('%Y-%m-01'),
            'emp': [(6, 0, [self.ref('hr.employee_admin'), self.ref('hr.employee_qdp'), self.ref('hr.employee_al')])],
            'holiday_type': 'Approved'
        }
        self.env.company.external_report_layout_id = self.env.ref('web.external_layout_standard').id
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_hr_holidays_summary_employee', wiz_data=data_dict, context=ctx, our_module='hr_holidays')

    def test_sql_constraint_dates(self):
        # The goal is mainly to verify that a human friendly
        # error message is triggered if the date_from is after
        # date_to. Coming from a bug due to the new ORM 13.0

        leave_vals = {
            'name': 'Sick Time Off',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id,
            'date_from': datetime.today().strftime('%Y-%m-11 19:00:00'),
            'date_to': datetime.today().strftime('%Y-%m-10 10:00:00'),
            'employee_id': self.ref('hr.employee_admin'),
            'number_of_days': 1,
        }
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    self.env['hr.leave'].create(leave_vals)

        leave_vals = {
            'name': 'Sick Time Off',
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_cl').id,
            'date_from': datetime.today().strftime('%Y-%m-10 10:00:00'),
            'date_to': datetime.today().strftime('%Y-%m-11 19:00:00'),
            'employee_id': self.ref('hr.employee_admin'),
            'number_of_days': 1,
        }
        leave = self.env['hr.leave'].create(leave_vals)
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):  # No ValidationError
                with self.cr.savepoint():
                    leave.write({
                        'date_from': datetime.today().strftime('%Y-%m-11 19:00:00'),
                        'date_to': datetime.today().strftime('%Y-%m-10 10:00:00'),
                    })
