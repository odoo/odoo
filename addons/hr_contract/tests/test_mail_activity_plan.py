# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import fields
from odoo.addons.hr.tests.test_mail_activity_plan import ActivityScheduleHRCase
from odoo.tests import tagged, users


@tagged('mail_activity', 'mail_activity_plan')
class TestActivitySchedule(ActivityScheduleHRCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_3 = cls.employee_coach
        cls.employee_4 = cls.employee_manager
        cls.employee_4.coach_id = cls.employee_coach
        for employee, date_start in ((cls.employee_1, '2023-08-01'),
                                     (cls.employee_2, '2023-09-01'),
                                     (cls.employee_3, '2023-12-01'),
                                     (cls.employee_4, '2024-01-01')):
            employee.contract_ids = cls.env['hr.contract'].create({
                'employee_id': employee.id,
                'date_end': fields.Date.from_string('2025-12-31'),
                'date_start': fields.Date.from_string(date_start),
                'name': 'Contract',
                'state': 'draft',
                'wage': 1,
            })

    @freeze_time('2023-08-31')
    @users('admin')
    def test_default_due_date(self):
        for employees, plan_date in (
                (self.employee_1, '2023-09-30'),
                (self.employee_2, '2023-09-30'),
                (self.employee_3, '2023-12-01'),
                (self.employee_4, '2024-01-01'),
                (self.employee_1 + self.employee_2 + self.employee_3, '2023-09-30'),
                (self.employee_2 + self.employee_3, '2023-09-30'),
                (self.employee_1 + self.employee_3, '2023-09-30'),
                (self.employee_3 + self.employee_4, '2023-12-01'),
                (self.employee_4 + self.employee_3, '2023-12-01'),
        ):
            with self._instantiate_activity_schedule_wizard(employees) as form:
                form.plan_id = self.plan_onboarding
                self.assertEqual(form.plan_date, fields.Date.from_string(plan_date))

        # not applicable on other models
        customers = self.env['res.partner'].create([
            {'name': 'Customer1',},
            {'name': 'Customer2',},
        ])
        with self._instantiate_activity_schedule_wizard(customers) as form:
            form.plan_id = self.plan_party
            self.assertFalse(form.plan_date)
