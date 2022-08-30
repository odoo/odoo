# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon


class TestProjectSharingWithSms(TestProjectSharingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sms_template = cls.env['sms.template'].sudo().create({
            'body': '{{ object.name }}',
            'model_id': cls.env['ir.model'].sudo().search([('model', '=', 'project.task')]).id,
        })
        cls.project_portal.type_ids[-1].write({'sms_template_id': cls.sms_template.id})
        cls.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': cls.user_portal.partner_id.id}),
            ],
        })

    def test_portal_user_can_change_stage_with_sms_template(self):
        """ Test user portal can change the stage of a task to a stage with a sms template

            The sms template should be sent and the stage should be changed on the task.
        """
        stage = self.project_portal.type_ids[-1]
        self.task_portal.with_user(self.user_portal).write({'stage_id': stage.id})
        self.assertEqual(self.task_portal.stage_id, stage)
