# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.fields import Datetime as FieldsDatetime
from datetime import datetime
from unittest.mock import patch


class TestHrEmployee(TestHrCommon):

    def test_employee_resource(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee = employee_form.save()
        self.assertEqual(employee.tz, _tz)

    def test_employee_from_user(self):
        _tz = 'Pacific/Apia'
        _tz2 = 'America/Tijuana'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        self.res_users_hr_officer.tz = _tz2
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, self.res_users_hr_officer.tz)

    def test_employee_from_user_tz_no_reset(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.tz = False
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.tz = _tz
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, _tz)

    def test_employee_working_now(self):
        #arrange
        _tz = 'Europe/Brussels'
        self.calendar = self.env['resource.calendar'].create({
            'name': '8h on Mon',
            'tz': 'Europe/Brussels',
            'attendance_ids': [
                (0, 0, {
                    'name': '8h_on_Mon_0',
                    'hour_from': 8,
                    'hour_to': 16,
                    'dayofweek': '0'
                })
            ]
        })
        
        self.empl = self.env['hr.employee.base'].create({
            'name': "John tester",
            'resource_calendar_id': self.calendar_jean.id,
        })
        
        with patch('odoo.fields.datetime', wraps=FieldsDatetime) as mock_datetime:
            mock_datetime.now.return_value = datetime(2021, 3, 15, 9, 30, 28) #Monday 09:30
            # act
            Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
            result = Employee._get_employee_working_now()
            #assert
            self.assertEqual(result, True)
