# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo import tests
from odoo.tests import new_test_user
from odoo.tests.common import Form, TransactionCase
from odoo.exceptions import ValidationError


@tests.tagged('access_rights', 'post_install', '-at_install')
class TestHrLeaveStressDays(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.default_calendar = cls.env['resource.calendar'].create({
            'name': 'moon calendar',
        })

        cls.company = cls.env['res.company'].create({
            'name': 'super company',
            'resource_calendar_id': cls.default_calendar.id,
        })

        cls.employee_user = new_test_user(cls.env, login='user', groups='base.group_user', company_ids=[(6, 0, cls.company.ids)], company_id=cls.company.id)
        cls.manager_user = new_test_user(cls.env, login='manager', groups='base.group_user,hr_holidays.group_hr_holidays_manager', company_ids=[(6, 0, cls.company.ids)], company_id=cls.company.id)

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'Toto Employee',
            'company_id': cls.company.id,
            'user_id': cls.employee_user.id,
            'resource_calendar_id': cls.default_calendar.id,
        })
        cls.manager_emp = cls.env['hr.employee'].create({
            'name': 'Toto Mananger',
            'company_id': cls.company.id,
            'user_id': cls.manager_user.id,
        })

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Unlimited',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
            'company_id': cls.company.id,
        })

        cls.stress_day = cls.env['hr.leave.stress.day'].create({
            'name': 'Super Event',
            'company_id': cls.company.id,
            'start_date': datetime(2021, 11, 2),
            'end_date': datetime(2021, 11, 2),
            'color': 1,
            'resource_calendar_id': cls.default_calendar.id,
        })
        cls.stress_week = cls.env['hr.leave.stress.day'].create({
            'name': 'Super Event End Of Week',
            'company_id': cls.company.id,
            'start_date': datetime(2021, 11, 8),
            'end_date': datetime(2021, 11, 12),
            'color': 2,
            'resource_calendar_id': cls.default_calendar.id,
        })

    @freeze_time('2021-10-15')
    def test_request_stress_days(self):
        # An employee can request time off outside stress days
        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2021, 11, 3),
            'date_to': datetime(2021, 11, 3),
            'number_of_days': 1,
        })

        # Taking a time off during a Stress Day is not allowed for a simple employee...
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.employee_user.id).create({
                'name': 'coucou',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'date_from': datetime(2021, 11, 3),
                'date_to': datetime(2021, 11, 17),
                'number_of_days': 1,
            })

        # ... but is allowed for a Time Off Officer
        self.env['hr.leave'].with_user(self.manager_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2021, 11, 2),
            'date_to': datetime(2021, 11, 2),
            'number_of_days': 1,
        })

    @freeze_time('2021-10-15')
    def test_get_stress_days(self):
        stress_days = self.env['hr.leave.stress.day'].with_user(self.employee_user.id).get_stress_days('2021-11-01', '2021-11-30')

        # Stress Days spanning multiple days should be split in single days
        expected_data = {'2021-11-02': 1, '2021-11-08': 2, '2021-11-09': 2, '2021-11-10': 2, '2021-11-11': 2, '2021-11-12': 2}

        self.assertEqual(len(stress_days), len(expected_data))
        for day, color in expected_data.items():
            self.assertTrue(day in stress_days)
            self.assertEqual(color, stress_days[day])

        with self.assertRaises(ValidationError), Form(self.env['hr.leave'].with_user(self.employee_user.id).with_context(default_employee_id=self.employee_emp.id)) as leave_form:
            leave_form.holiday_status_id = self.leave_type
            leave_form.date_from = datetime(2021, 11, 1)
            leave_form.date_to = datetime(2021, 11, 1)
            self.assertFalse(leave_form.has_stress_day)

            leave_form.date_to = datetime(2021, 11, 5)
            self.assertTrue(leave_form.has_stress_day)
