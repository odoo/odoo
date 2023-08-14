# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import fields
from odoo.addons.hr.tests.test_mail_activity_plan import TestActivityScheduleHRCase


class TestActivitySchedule(TestActivityScheduleHRCase):
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
                'name': 'Contract',
                'employee_id': employee.id,
                'state': 'draft',
                'wage': 1,
                'date_start': fields.Date.from_string(date_start),
                'date_end': fields.Date.from_string('2025-12-31'),
            })
        cls.partner_1, cls.partner_2 = cls.env['res.partner'].create([
            {'name': f'partner{idx + 1}'} for idx in range(2)])

    @freeze_time('2023-08-31')
    def test_default_due_date(self):
        for employees, date_plan_deadline in (
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
                self.assertEqual(form.date_plan_deadline, fields.Date.from_string(date_plan_deadline))
        self.plan_onboarding.template_ids[1].responsible_type = 'on_demand'
        self.plan_onboarding.res_model_ids = False
        for partners in (self.partner_1, self.partner_1 + self.partner_2):
            with self._instantiate_activity_schedule_wizard(partners) as form:
                form.plan_id = self.plan_onboarding
                self.assertFalse(form.date_plan_deadline)
