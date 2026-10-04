# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date

from odoo import Command, fields
from odoo.tests import common, Form
from odoo.tests.common import TransactionCase
from odoo.fields import Datetime
from odoo.addons.hr.tests.test_utils import get_admin_employee
from odoo.addons.mail.tests.common import mail_new_test_user


class TestHrHolidaysCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestHrHolidaysCommon, cls).setUpClass()
        cls.env.user.tz = 'Europe/Brussels'
        cls.env.user.company_id.tz = "Europe/Brussels"

        cls.company = cls.env['res.company'].create({'name': 'Test company'})
        cls.external_company = cls.env['res.company'].create({'name': 'External Test company'})

        cls.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'attendance_ids': [
                (0, 0,
                    {
                        'dayofweek': weekday,
                        'hour_from': hour,
                        'hour_to': hour + 4,
                    })
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
            'company_id': cls.company.id,
            'name': 'Standard 40h/week',
        })

        cls.external_company.resource_calendar_id = cls.env['resource.calendar'].create({
            'attendance_ids': [
                (0, 0,
                    {
                        'dayofweek': weekday,
                        'hour_from': hour,
                        'hour_to': hour + 4,
                    })
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
            'company_id': cls.external_company.id,
            'name': 'Standard 40h/week',
        })

        cls.env.user.company_id = cls.company

        # The available time off types are the ones whose:
        # 1. Company is one of the selected companies.
        # 2. Company is false but whose country is one the countries of the selected companies.
        # 3. Company is false and country is false
        # Thus, a time off type is defined to be available for `Test company`
        # For example, the tour 'time_off_request_calendar_view' would succeed (false positive) without this leave type.
        # However, the tour won't create a time-off request (as expected)because no time-off type is available to be selected on the leave
        # This would cause the test case that uses the tour to fail.
        cls.env['hr.work.entry.type'].create({
            'name': 'Test Work Entry Type',
            'code': 'Test Work Entry Type',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.admin_employee = get_admin_employee(cls.env)

        # Test users to use through the various tests
        cls.user_hruser = mail_new_test_user(cls.env, login='armande', groups='base.group_user,hr_holidays.group_hr_holidays_user')
        cls.user_hruser_id = cls.user_hruser.id

        cls.user_hrmanager = mail_new_test_user(cls.env, login='bastien', groups='base.group_user,hr_holidays.group_hr_holidays_manager')
        cls.user_hrmanager_id = cls.user_hrmanager.id
        cls.user_hrmanager.tz = 'Europe/Brussels'

        cls.user_responsible = mail_new_test_user(cls.env, login='Titus', groups='base.group_user,hr_holidays.group_hr_holidays_responsible')
        cls.user_responsible_id = cls.user_responsible.id
        cls.user_employee = mail_new_test_user(cls.env, login='enguerran', password='enguerran', groups='hr_holidays.group_hr_holidays_employee')
        cls.user_employee_id = cls.user_employee.id
        cls.external_user_employee = mail_new_test_user(cls.env, login='external', password='external', groups='base.group_user')
        cls.external_user_employee_id = cls.external_user_employee.id
        # Hr Data
        Department = cls.env['hr.department']

        cls.hr_dept = Department.create({
            'name': 'Human Resources',
        })
        cls.rd_dept = Department.create({
            'name': 'Research and devlopment',
        })

        cls.employee_responsible = cls.env['hr.employee'].create({
            'name': 'David Employee',
            'user_id': cls.user_responsible_id,
            'department_id': cls.rd_dept.id,
        })

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'David Employee',
            'user_id': cls.user_employee_id,
            'leave_manager_id': cls.user_responsible_id,
            'department_id': cls.rd_dept.id,
            'company_id': cls.company.id,
        })
        cls.employee_emp_id = cls.employee_emp.id

        cls.employee_external = cls.env['hr.employee'].create({
            'name': 'external Employee',
            'user_id': cls.external_user_employee_id,
            'company_id': cls.external_company.id,
        })
        cls.external_employee_id = cls.employee_external.id

        cls.employee_hruser = cls.env['hr.employee'].create({
            'name': 'Armande HrUser',
            'user_id': cls.user_hruser_id,
            'department_id': cls.rd_dept.id,
        })
        cls.employee_hruser_id = cls.employee_hruser.id

        cls.employee_hrmanager = cls.env['hr.employee'].create({
            'name': 'Bastien HrManager',
            'user_id': cls.user_hrmanager_id,
            'department_id': cls.hr_dept.id,
            'parent_id': cls.employee_hruser_id,
        })
        cls.employee_hrmanager_id = cls.employee_hrmanager.id

        cls.rd_dept.write({'manager_id': cls.employee_hruser_id})
        cls.hours_per_day = cls.employee_emp.resource_id.calendar_id.hours_per_day or 8

    def _assert_allocation_balance(self, allocation, expected_duration=None, expected_remaining_leaves=None,
            target_date=None, msg=None, digits=3):
        """ Assert `_get_allocation_data` returns the specified `expected_duration` and `expected_remaining_leaves`
            for the work entry type of the given `allocation` at the given `target_date`
            :param expected_duration: expressed in `allocation.work_entry_type_id.unit_of_measure`
            :param target_date: default is today
        """
        return self._assert_work_entry_type_allocations_balance(
            allocation.work_entry_type_id, allocation.employee_id, expected_duration, expected_remaining_leaves, target_date, msg, digits)

    def _assert_work_entry_type_allocations_balance(self, work_entry_type, employee, expected_duration=None, expected_remaining_leaves=None,
            target_date=None, msg=None, digits=3):
        """ Assert `_get_allocation_data` returns the specified `expected_duration` and `expected_remaining_leaves`
            for the given `work_entry_type`
            :param expected_duration: expressed in `allocation.work_entry_type_id.unit_of_measure`
            :param target_date: default is today
        """
        work_entry_type_data = work_entry_type.get_allocation_data(employee, target_date)
        remaining_leaves = work_entry_type_data[employee][0][1]['remaining_leaves']

        modified_msg = f'Error on {target_date or fields.Date.today()}' + (f' - {msg}' if msg else '')
        if expected_duration:
            leaves_taken = work_entry_type_data[employee][0][1]['leaves_taken']
            allocation_value = remaining_leaves + leaves_taken
            self.assertAlmostEqual(allocation_value, expected_duration, places=digits, msg=modified_msg)
        if expected_remaining_leaves:
            self.assertAlmostEqual(remaining_leaves, expected_remaining_leaves, places=digits, msg=modified_msg)

    def _create_leave(self, employee, work_entry_type, date_from, date_to, hour_from=False, hour_to=False, validate=False, user=None, additionnal_ctx={}):
        leave = self.env['hr.leave'].with_context(tracking_disable=True, **additionnal_ctx).with_user(user or self.env.user).create({
            'name': 'Leave',
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'request_hour_from': hour_from,
            'request_hour_to': hour_to,
        })
        if validate:
            leave.action_approve()
        return leave

    def _create_form_test_accrual_allocation(self, work_entry_type, date_from, employee, accrual_plan, date_to=None, creator_user=None, number_of_days=None, skip_auto_approve=False):
        allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True)
        if creator_user:
            allocation = allocation.with_user(creator_user)
        if skip_auto_approve:
            allocation = allocation.with_context(allocation_skip_auto_approve=True)
        with Form(allocation, 'hr_holidays.hr_leave_allocation_view_form_manager') as form:
            form.name = 'Test accrual allocation'
            form.accrual_plan_id = accrual_plan
            form.employee_id = employee
            form.work_entry_type_id = work_entry_type
            form.date_from = date_from
            if date_to:
                form.date_to = date_to
            if number_of_days:
                form.number_of_days = number_of_days
        return form.record

    def _create_form_test_regular_allocation(self, work_entry_type, date_from, employee, duration, date_to=None, creator_user=None):
        allocation = self.env['hr.leave.allocation']
        if creator_user:
            allocation = allocation.with_user(creator_user)
        with Form(allocation, 'hr_holidays.hr_leave_allocation_view_form_manager') as form:
            form.name = 'Test regular allocation'
            form.employee_id = employee
            form.work_entry_type_id = work_entry_type
            form.date_from = date_from
            if not work_entry_type.unit_of_measure or work_entry_type.unit_of_measure == 'day':
                form.number_of_days_display = duration
            else:
                form.number_of_hours_display = duration
            if date_to:
                form.date_to = date_to
        return form.record


class TestHolidayContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'attendance_ids': [
                (0, 0,
                    {
                        'dayofweek': weekday,
                        'hour_from': hour,
                        'hour_to': hour + 4,
                    })
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
            'name': 'Standard 40h/week',
        })

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Legal Leaves',
            'code': 'Legal Leaves',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.env.ref('base.user_admin').notification_type = 'inbox'

        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })

        # I create a new employee "Jules"
        cls.jules_emp = cls.env['hr.employee'].create({
            'name': 'Jules',
            'sex': 'male',
            'birthday': '1984-05-01',
            'country_id': cls.env.ref('base.be').id,
            'department_id': cls.dep_rd.id,
        })

        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 16}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 16})
            ]
        })
        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})

        # This contract ends at the 15th of the month
        cls.jules_emp.version_id.write({  # Fixed term contract
            'contract_date_end': datetime.strptime('2015-11-15', '%Y-%m-%d'),
            'contract_date_start': datetime.strptime('2015-01-01', '%Y-%m-%d'),
            'date_version': datetime.strptime('2015-01-01', '%Y-%m-%d'),
            'name': 'First CDD Contract for Jules',
            'resource_calendar_id': cls.calendar_40h.id,
            'wage': 5000.0,
        })
        cls.contract_cdd = cls.jules_emp.version_id

        # This contract starts the next day
        cls.contract_cdi = cls.jules_emp.create_version({
            'date_version': datetime.strptime('2015-11-16', '%Y-%m-%d'),
            'contract_date_start': datetime.strptime('2015-11-16', '%Y-%m-%d'),
            'contract_date_end': False,
            'name': 'Contract for Jules',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
        })

    @classmethod
    def create_leave(cls, date_from=None, date_to=None, name="", employee_id=False):
        return cls.env['hr.leave'].create({
            'name': name or 'Holiday!!!',
            'employee_id': employee_id or cls.richard_emp.id,
            'work_entry_type_id': cls.work_entry_type.id,
            'request_date_to': date_to or Datetime.today(),
            'request_date_from': date_from or Datetime.today(),
        })


class TestFutureLeavesCommon(TransactionCase):
    """ Common setup of the tests about the future leaves linked to an accrual plan.

    Today is 2026-09-29 (freeze_time):
    - accrual plan: 2 days (or 16 hours) on the 1st of each month, accrued at the start of the period
    - allocation starting on 2026-01-01: 9 accruals (January to September), so 18 days accrued today
      and then 20 days on 2026-10-01, 22 on 2026-11-01 and 24 on 2026-12-01
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee = cls.env['hr.employee'].create({'name': 'Accrual Employee'})
        cls.work_entry_type = cls._create_work_entry_type('Accrued Time Off', 'ACCR', allows_negative=False)
        cls.accrual_plan = cls._create_accrual_plan(cls.work_entry_type)
        # accrual with negative balance
        cls.negative_work_entry_type = cls._create_work_entry_type(
            'Accrued Time Off (negative allowed)', 'ACNEG', allows_negative=True, max_allowed_negative=1)
        cls.negative_accrual_plan = cls._create_accrual_plan(cls.negative_work_entry_type)
        # accrual in hours, 16 hours per month (2 days of 8 hours)
        cls.hour_work_entry_type = cls._create_work_entry_type(
            'Accrued Hours', 'ACHR', allows_negative=False, unit_of_measure='hour')
        cls.hour_accrual_plan = cls._create_accrual_plan(
            cls.hour_work_entry_type, added_value=16, added_value_type='hour')
        # accrual that allows the requests to be made with custom hours instead of full days
        cls.custom_hours_work_entry_type = cls._create_work_entry_type(
            'Accrued Custom Hours', 'ACCH', allows_negative=False, unit_of_measure='hour', request_unit='hour')
        cls.custom_hours_accrual_plan = cls._create_accrual_plan(
            cls.custom_hours_work_entry_type, added_value=16, added_value_type='hour')

    @classmethod
    def _create_accrual_plan(cls, work_entry_type, added_value=2, added_value_type='day'):
        return cls.env['hr.leave.accrual.plan'].create({
            'name': 'Monthly accrual',
            'work_entry_type_id': work_entry_type.id,
            'accrued_gain_time': 'start',
            'transition_mode': 'immediately',
            'added_value_type': added_value_type,
            'level_ids': [(0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': added_value,
                'added_value_type': added_value_type,
                'frequency': 'monthly',
                'first_day': '1',
            })],
        })

    @classmethod
    def _create_work_entry_type(
            cls, name, code, allows_negative, max_allowed_negative=0, unit_of_measure='day', request_unit='day'):
        # no validation, so that allocations and leaves are directly validated
        return cls.env['hr.work.entry.type'].create({
            'name': name,
            'code': code,
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
            'allocation_validation_type': 'no_validation',
            'request_unit': request_unit,
            'unit_of_measure': unit_of_measure,
            'allows_negative': allows_negative,
            'max_allowed_negative': max_allowed_negative,
        })

    def _create_allocation(self, work_entry_type=None, accrual_plan=None):
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Accrual allocation',
            'employee_id': self.employee.id,
            'work_entry_type_id': (work_entry_type or self.work_entry_type).id,
            'accrual_plan_id': (accrual_plan or self.accrual_plan).id,
            'date_from': date(2026, 1, 1),
            'number_of_days': 0,
        })
        if allocation.state != 'validate':
            allocation.action_approve()
        # update number_of_days with the accruals until today
        allocation._update_accrual()
        return allocation

    def _create_leave(self, request_date_from, request_date_to, work_entry_type=None, from_dashboard=False, **values):
        return self.env['hr.leave'].with_context(from_dashboard=from_dashboard).create({
            'employee_id': self.employee.id,
            'work_entry_type_id': (work_entry_type or self.work_entry_type).id,
            'request_date_from': request_date_from,
            'request_date_to': request_date_to,
            **values,
        })

    def _get_info(self, from_dashboard, target_date=None, work_entry_type=None):
        """ Return the data of a time type as the dashboard requests it (`from_dashboard`),
        or as any other caller (validation, cron, ...) gets it. """
        work_entry_type = work_entry_type or self.work_entry_type
        target_date = target_date or date.today()
        if from_dashboard:
            data = work_entry_type.with_context(
                employee_id=self.employee.id, from_dashboard=True).get_allocation_data_request(target_date, False)
        else:
            data = work_entry_type.get_allocation_data(self.employee, target_date)[self.employee]
        return next(info for _name, info, _requires_allocation, type_id in data if type_id == work_entry_type.id)

    def _create_planned_leaves(self, work_entry_type):
        """ Create 20 days (4 weeks) of future leaves. """
        for date_from, date_to in (
            (date(2026, 11, 16), date(2026, 11, 20)),
            (date(2026, 11, 23), date(2026, 11, 27)),
            (date(2026, 12, 7), date(2026, 12, 11)),
            (date(2026, 12, 14), date(2026, 12, 18)),
        ):
            self._create_leave(date_from, date_to, work_entry_type=work_entry_type)
