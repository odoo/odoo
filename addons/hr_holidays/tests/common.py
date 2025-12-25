# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime

from odoo import Command, tests
from odoo.fields import Datetime
from odoo.tests import common
from odoo.tests.common import TransactionCase
from odoo.addons.hr.tests.test_utils import get_admin_employee
from odoo.addons.mail.tests.common import mail_new_test_user


class TestHrHolidaysCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestHrHolidaysCommon, cls).setUpClass()
        cls.env.user.tz = 'Europe/Brussels'
        cls.env.user.company_id.resource_calendar_id.tz = "Europe/Brussels"

        cls.company = cls.env['res.company'].create({'name': 'Test company'})
        cls.external_company = cls.env['res.company'].create({'name': 'External Test company'})

        cls.env.user.company_id = cls.company

        # The available time off types are the ones whose:
        # 1. Company is one of the selected companies.
        # 2. Company is false but whose country is one the countries of the selected companies.
        # 3. Company is false and country is false
        # Thus, a time off type is defined to be available for `Test company`
        # For example, the tour 'time_off_request_calendar_view' would succeed (false positive) without this leave type.
        # However, the tour won't create a time-off request (as expected)because no time-off type is available to be selected on the leave
        # This would cause the test case that uses the tour to fail.
        cls.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'requires_allocation': False,
            'request_unit': 'day',
            'company_id': cls.company.id,
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
        cls.user_employee = mail_new_test_user(cls.env, login='enguerran', password='enguerran', groups='base.group_user')
        cls.user_employee_id = cls.user_employee.id
        cls.external_user_employee = mail_new_test_user(cls.env, login='external', password='external', groups='base.group_user')
        cls.external_user_employee_id = cls.external_user_employee.id
        # Hr Data
        Department = cls.env['hr.department'].with_context(tracking_disable=True)

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


class TestHolidayContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': False,
            'responsible_ids': [Command.link(cls.env.ref('base.user_admin').id)],
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
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
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
            'holiday_status_id': cls.leave_type.id,
            'request_date_to': date_to or Datetime.today(),
            'request_date_from': date_from or Datetime.today(),
        })


@tests.tagged("access_rights", "post_install", "-at_install")
class TestHrLeaveCashOutCommon(TestHrHolidaysCommon):
    """Test the access rights for hr_leave_cash_out"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Leave Type",
                "leave_validation_type": "hr",
                "requires_allocation": True,
                "allow_cash_out_request": True,
                "allow_employee_request": True,
            },
        )
        cls.rd_dept.manager_id = False
        cls.hr_dept.manager_id = False
        cls.employee_emp.parent_id = False
        cls.cash_out_states = [
            state[0]
            for state in cls.env["hr.leave.cash.out"]._fields["state"].selection
        ]

    def request_allocation(self, values={}):
        values = {
            "name": "Allocation",
            "number_of_days": 20,
            "date_from": time.strftime("%Y-01-01"),
            "date_to": time.strftime("%Y-12-31"),
            "holiday_status_id": self.leave_type.id,
            **values,
        }
        allocation = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hrmanager_id)
            .create(values)
        )
        allocation.with_user(self.user_hrmanager_id).action_approve()
        return allocation

    def request_cash_out(self, user, values={}):
        values = {
            "state": "confirm",
            "leave_type_id": self.leave_type.id,
            "quantity": 1,
            **values,
        }
        return self.env["hr.leave.cash.out"].with_context(employee_id=values['employee_id']).with_user(user).create(values)
