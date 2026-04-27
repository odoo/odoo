# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.hr.tests.test_mail_activity_plan import ActivityScheduleHRCase
from odoo.addons.sign.tests.sign_request_common import SignRequestCommon
from odoo.tests import tagged, users


@tagged('mail_activity', 'mail_activity_plan')
class TestActivitySchedule(ActivityScheduleHRCase, SignRequestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.activity_type_request_signature = cls.env.ref('sign.mail_activity_data_signature_request')
        cls.plan_sign = cls.env['mail.activity.plan'].create({
            'name': 'Sign plan',
            'res_model': 'hr.employee',
            'template_ids': [Command.create({
                'activity_type_id': cls.activity_type_request_signature.id,
                'sign_template_id': cls.template_1_role.id,
                'summary': 'Sign',
                'responsible_type': 'employee',
            }), Command.create({
                'activity_type_id': cls.activity_type_todo.id,
                'summary': 'Fill in personal information on the website',
                'responsible_type': 'employee',
            })]
        })
        cls.employee_3 = cls.employee_coach

    @users('admin')
    def test_sign(self):
        employees = (self.employee_1 + self.employee_2).with_env(self.env)
        form = self._instantiate_activity_schedule_wizard(employees)
        form.plan_id = self.plan_sign
        with self._mock_activities():
            form.save().action_schedule_plan()

        for employee in employees:
            self.assertActivityCreatedOnRecord(employee, {
                'activity_type_id': self.activity_type_todo,
                'summary': 'Fill in personal information on the website',
            })

            last_message = employee.message_ids[0]
            self.assertIn(f'{self.env.user.name} requested a new signature on the following documents', last_message.body)
