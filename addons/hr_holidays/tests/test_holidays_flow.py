# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools import mute_logger, test_reports

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHolidaysFlow(TestHrHolidaysCommon):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_00_leave_request_flow_unlimited(self):
        """ Testing leave request flow: unlimited type of leave request """
        Requests = self.env['hr.leave']
        HolidaysStatus = self.env['hr.leave.type']

        # HrManager creates some holiday statuses
        HolidayStatusManagerGroup = HolidaysStatus.with_user(self.user_hrmanager_id)
        HolidayStatusManagerGroup.create({
            'name': 'WithMeetingType',
            'requires_allocation': 'no',
        })
        self.holidays_status_hr = HolidayStatusManagerGroup.create({
            'name': 'NotLimitedHR',
            'requires_allocation': 'no',
            'leave_validation_type': 'hr',
        })
        self.holidays_status_manager = HolidayStatusManagerGroup.create({
            'name': 'NotLimitedManager',
            'requires_allocation': 'no',
            'leave_validation_type': 'manager',
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
        with freeze_time('2022-01-15'):
            Requests = self.env['hr.leave']
            Allocations = self.env['hr.leave.allocation']
            HolidaysStatus = self.env['hr.leave.type']

            holiday_status_paid_time_off = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'requires_allocation': 'yes',
                'employee_requests': 'no',
                'allocation_validation_type': 'officer',
                'leave_validation_type': 'both',
                'responsible_id': self.env.ref('base.user_admin').id,
            })

            self.env['hr.leave.allocation'].create([
                {
                    'name': 'Paid Time off for David',
                    'holiday_status_id': holiday_status_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.employee_emp_id,
                    'state': 'validate',
                    'date_from': time.strftime('%Y-%m-01'),
                }, {
                    'name': 'Paid Time off for David',
                    'holiday_status_id': holiday_status_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.ref('hr.employee_admin'),
                    'state': 'validate',
                    'date_from': time.strftime('%Y-%m-01'),
                }
            ])

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
                'requires_allocation': 'no',
            })

            self.holidays_status_limited = HolidayStatusManagerGroup.create({
                'name': 'Limited',
                'requires_allocation': 'yes',
                'employee_requests': 'no',
                'allocation_validation_type': 'officer',
                'leave_validation_type': 'both',
            })
            HolidaysEmployeeGroup = Requests.with_user(self.user_employee_id)

            # HrUser allocates some leaves to the employee
            aloc1_user_group = Allocations.with_user(self.user_hruser_id).create({
                'name': 'Days for limited category',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_status_limited.id,
                'number_of_days': 2,
                'state': 'confirm',
                'date_from': time.strftime('%Y-%m-01'),
            })
            # HrUser validates the first step

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
            hol_status_2_employee_group.invalidate_model()
            _check_holidays_status(hol_status_2_employee_group, 2.0, 0.0, 2.0, 1.0)

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

            hol_status_2_employee_group.invalidate_model(['max_leaves'])
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
            hol3_status = holiday_status_paid_time_off.with_context(employee_id=employee_id)
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
            hol3.action_validate()
            self.assertEqual(hol3.state, 'validate', 'hr_holidays: validation should lead to validate state')
            # Check left days for casual leave: 19 days left
            _check_holidays_status(hol3_status, 20.0, 1.0, 19.0, 19.0)

    def test_10_leave_summary_reports(self):
        # Print the HR Holidays(Summary Employee) Report through the wizard
        ctx = {
            'model': 'hr.employee',
            'active_ids': [self.ref('hr.employee_admin')]
        }
        data_dict = {
            'date_from': datetime.today().strftime('%Y-%m-01'),
            'emp': [(6, 0, [self.ref('hr.employee_admin')])],
            'holiday_type': 'Approved'
        }
        self.env.company.external_report_layout_id = self.env.ref('web.external_layout_standard').id
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_hr_holidays_summary_employee', wiz_data=data_dict, context=ctx, our_module='hr_holidays')

    def test_sql_constraint_dates(self):
        # The goal is mainly to verify that a human friendly
        # error message is triggered if the date_from is after
        # date_to. Coming from a bug due to the new ORM 13.0

        holiday_status_paid_time_off = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'officer',
            'leave_validation_type': 'both',
            'responsible_id': self.env.ref('base.user_admin').id,
        })

        self.env['hr.leave.allocation'].create({
            'name': 'Paid Time off for David',
            'holiday_status_id': holiday_status_paid_time_off.id,
            'number_of_days': 20,
            'employee_id': self.ref('hr.employee_admin'),
            'state': 'validate',
            'date_from': time.strftime('%Y-%m-01'),
            'date_to': time.strftime('%Y-12-31'),
        })

        leave_vals = {
            'name': 'Sick Time Off',
            'holiday_status_id': holiday_status_paid_time_off.id,
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
            'holiday_status_id': holiday_status_paid_time_off.id,
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
