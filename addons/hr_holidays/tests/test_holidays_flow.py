# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo import Command
from odoo.tools import date_utils, mute_logger, test_reports

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
            'requires_allocation': False,
        })
        self.holidays_status_hr = HolidayStatusManagerGroup.create({
            'name': 'NotLimitedHR',
            'requires_allocation': False,
            'leave_validation_type': 'hr',
        })
        self.holidays_status_manager = HolidayStatusManagerGroup.create({
            'name': 'NotLimitedManager',
            'requires_allocation': False,
            'leave_validation_type': 'manager',
        })

        HolidaysEmployeeGroup = Requests.with_user(self.user_employee_id)

        # Employee creates a leave request in a no-limit category hr manager only
        leave_date = date_utils.start_of((date.today() - relativedelta(days=1)), 'week')
        hol1_employee_group = HolidaysEmployeeGroup.create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_hr.id,
            'request_date_from': leave_date,
            'request_date_to': leave_date,
        })
        hol1_user_group = hol1_employee_group.with_user(self.user_hruser_id)
        hol1_manager_group = hol1_employee_group.with_user(self.user_hrmanager_id)
        self.assertEqual(hol1_user_group.state, 'confirm', 'hr_holidays: newly created leave request should be in confirm state')

        # HrUser validates the employee leave request -> should work
        hol1_user_group.action_approve()
        self.assertEqual(hol1_manager_group.state, 'validate', 'hr_holidays: validated leave request should be in validate state')

        # Employee creates a leave request in a no-limit category department manager only
        leave_date = date_utils.start_of(date.today() + relativedelta(days=11), 'week')
        hol12_employee_group = HolidaysEmployeeGroup.create({
            'name': 'Hol12',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_manager.id,
            'request_date_from': leave_date,
            'request_date_to': leave_date,
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

            self.env.ref('hr.employee_admin').tz = "Europe/Brussels"

            holiday_status_paid_time_off = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'requires_allocation': True,
                'employee_requests': False,
                'allocation_validation_type': 'hr',
                'leave_validation_type': 'both',
                'responsible_ids': [Command.link(self.env.ref('base.user_admin').id)],
            })

            self.env['hr.leave.allocation'].create([
                {
                    'name': 'Paid Time off for David',
                    'holiday_status_id': holiday_status_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.employee_emp_id,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                }, {
                    'name': 'Paid Time off for Admin',
                    'holiday_status_id': holiday_status_paid_time_off.id,
                    'number_of_days': 20,
                    'employee_id': self.ref('hr.employee_admin'),
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-%m-01'),
                }
            ]).action_approve()

            def _check_holidays_status(holiday_status, employee, ml, lt, rl, vrl):
                result = holiday_status.get_allocation_data(employee)[employee][0][1]
                self.assertEqual(result['max_leaves'], ml,
                                'hr_holidays: wrong type days computation')
                self.assertEqual(result['leaves_taken'], lt,
                                'hr_holidays: wrong type days computation')
                self.assertEqual(result['remaining_leaves'], rl,
                                'hr_holidays: wrong type days computation')
                self.assertEqual(result['virtual_remaining_leaves'], vrl,
                                'hr_holidays: wrong type days computation')

            # HrManager creates some holiday statuses
            HolidayStatusManagerGroup = HolidaysStatus.with_user(self.user_hrmanager_id)
            HolidayStatusManagerGroup.create({
                'name': 'WithMeetingType',
                'requires_allocation': False,
            })

            self.holidays_status_limited = HolidayStatusManagerGroup.create({
                'name': 'Limited',
                'requires_allocation': True,
                'employee_requests': False,
                'allocation_validation_type': 'hr',
                'leave_validation_type': 'both',
                'responsible_ids': [Command.link(self.env.ref('base.user_admin').id)]
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
            self.env.flush_all()

            # HrManager validates the second step
            aloc1_user_group.with_user(self.user_hrmanager_id).action_approve()
            # Checks Employee has effectively some days left
            hol_status_2_employee_group = self.holidays_status_limited.with_user(self.user_employee_id)
            _check_holidays_status(hol_status_2_employee_group, self.employee_emp, 2.0, 0.0, 2.0, 2.0)

            # Employee creates a leave request in the limited category, now that he has some days left
            hol2 = HolidaysEmployeeGroup.create({
                'name': 'Hol22',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_status_limited.id,
                'request_date_from': (date.today() + relativedelta(days=2)),
                'request_date_to': (date.today() + relativedelta(days=2)),
            })
            self.env.flush_all()
            hol2_user_group = hol2.with_user(self.user_hruser_id)
            # Check left days: - 1 virtual remaining day
            hol_status_2_employee_group.invalidate_model()
            _check_holidays_status(hol_status_2_employee_group, self.employee_emp, 2.0, 0.0, 2.0, 1.0)

            # HrManager validates the second step
            hol2_user_group.with_user(self.user_hrmanager_id).action_approve()
            self.assertEqual(hol2.state, 'validate',
                            'hr_holidays: second validation should lead to validate state')
            # Check left days: - 1 day taken
            hol_status_2_employee_group.invalidate_model(['max_leaves', 'leaves_taken'])
            _check_holidays_status(hol_status_2_employee_group, self.employee_emp, 2.0, 1.0, 1.0, 1.0)

            # HrManager finds an error: he refuses the leave request
            hol2.with_user(self.user_hrmanager_id).action_refuse()
            self.assertEqual(hol2.state, 'refuse',
                            'hr_holidays: refuse should lead to refuse state')
            # Check left days: 2 days left again

            hol_status_2_employee_group.invalidate_model(['max_leaves'])
            _check_holidays_status(hol_status_2_employee_group, self.employee_emp, 2.0, 0.0, 2.0, 2.0)

            self.assertEqual(hol2.state, 'refuse',
                            'hr_holidays: hr_user should not be able to reset a refused leave request')

            employee_id = self.ref('hr.employee_admin')
            # cl can be of maximum 20 days for employee_admin
            hol3_status = holiday_status_paid_time_off.with_context(employee_id=employee_id)
            # I assign the dates in the holiday request for 1 day
            hol3 = Requests.create({
                'name': 'Sick Time Off',
                'holiday_status_id': hol3_status.id,
                'request_date_from': date.today() + relativedelta(day=10),
                'request_date_to': date.today() + relativedelta(day=10),
                'employee_id': employee_id,
                'number_of_days': 1,
            })
            # I find a small mistake on my leave request to I click on "Refuse" button to correct a mistake.
            hol3.action_refuse()
            self.assertEqual(hol3.state, 'refuse', 'hr_holidays: refuse should lead to refuse state')
            # Validate it again
            hol3.action_approve()
            self.assertEqual(hol3.state, 'validate', 'hr_holidays: validation should lead to validate state')
            # Check left days for casual leave: 19 days left
            _check_holidays_status(hol3_status, self.env['hr.employee'].browse(employee_id), 20.0, 1.0, 19.0, 19.0)

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
            'requires_allocation': True,
            'employee_requests': False,
            'allocation_validation_type': 'hr',
            'leave_validation_type': 'both',
            'responsible_ids': [Command.link(self.env.ref('base.user_admin').id)],
        })

        self.env['hr.leave.allocation'].create({
            'name': 'Paid Time off for David',
            'holiday_status_id': holiday_status_paid_time_off.id,
            'number_of_days': 20,
            'employee_id': self.ref('hr.employee_admin'),
            'state': 'confirm',
            'date_from': time.strftime('%Y-%m-01'),
            'date_to': time.strftime('%Y-12-31'),
        }).action_approve()

        leave_vals = {
            'name': 'Sick Time Off',
            'holiday_status_id': holiday_status_paid_time_off.id,
            'request_date_from': date.today() + relativedelta(day=11),
            'request_date_to': date.today() + relativedelta(day=10),
            'employee_id': self.ref('hr.employee_admin'),
        }
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            self.env['hr.leave'].create(leave_vals)

        leave_vals = {
            'name': 'Sick Time Off',
            'holiday_status_id': holiday_status_paid_time_off.id,
            'request_date_from': date.today() + relativedelta(day=10),
            'request_date_to': date.today() + relativedelta(day=11),
            'employee_id': self.ref('hr.employee_admin'),
        }
        leave = self.env['hr.leave'].create(leave_vals)

        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            leave.write({
                'request_date_from': date.today() + relativedelta(day=11),
                'request_date_to': date.today() + relativedelta(day=10),
            })
