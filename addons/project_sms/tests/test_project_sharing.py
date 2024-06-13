# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon
from odoo.addons.sms.tests.common import SMSCommon
from odoo.tests import tagged


class TestProjectSharingWithSms(TestProjectSharingCommon, SMSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_settings = cls.env["res.config.settings"].create({'group_project_stages': True})
        project_settings.execute()

        cls.sms_template = cls.env['sms.template'].sudo().create({
            'body': '{{ object.name }}',
            'model_id': cls.env['ir.model'].sudo().search([('model', '=', 'project.task')]).id,
        })
        cls.task_stage_with_sms = cls.project_portal.type_ids[-1]
        cls.task_stage_with_sms.write({'sms_template_id': cls.sms_template.id})

        cls.sms_template_2 = cls.env['sms.template'].sudo().create({
            'body': '{{ object.name }}',
            'model_id': cls.env['ir.model'].sudo().search([('model', '=', 'project.project')]).id,
        })
        cls.project_stage_with_sms = cls.project_portal.stage_id.browse(2)
        cls.project_stage_with_sms.write({'sms_template_id': cls.sms_template_2.id})

        cls.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': cls.user_portal.partner_id.id}),
            ],
        })
        cls.project_portal.partner_id.mobile = cls.random_numbers[0]

    def test_portal_user_can_change_stage_with_sms_template(self):
        """ Test user portal can change the stage of a task to a stage with a sms template

            The sms template should be sent and the stage should be changed on the task.
        """
        with self.mockSMSGateway():
            self.task_portal.with_user(self.user_portal).write({
                'stage_id': self.task_stage_with_sms.id,
            })
        self.assertEqual(self.task_portal.stage_id, self.task_stage_with_sms)
        self.assertSMSIapSent([])  # no sms sent since the author is the recipient

        self.task_portal.write({
            'partner_id': self.user_projectuser.partner_id.id,
            'stage_id': self.project_portal.type_ids[0].id,
        })
        with self.mockSMSGateway():
            self.task_portal.with_user(self.user_portal).write({
                'stage_id': self.task_stage_with_sms.id,
            })
        self.assertEqual(self.task_portal.stage_id, self.task_stage_with_sms)
        self.assertSMSIapSent([self.user_projectuser.partner_id.mobile])

        with self.mockSMSGateway():
            self.project_portal.write({
                'stage_id': self.project_stage_with_sms.id,
            })
        self.assertEqual(self.project_portal.stage_id, self.project_stage_with_sms)
        self.assertSMSIapSent([self.project_portal.partner_id.mobile])


@tagged('post_install', '-at_install')
class TestPostInstallProjectSharingWithSms(TestProjectSharingWithSms):

    def test_project_user_can_change_stage_with_sms_template(self):
        """ Test that users with the rights to change the stage of a task can perform this action
            when the stage has an sms template.

            The sms template should be sent and the stage should be changed on the task.
        """
        project_user_group = self.env.ref('project.group_project_user')
        sale_manager_group = self.env.ref('sales_team.group_sale_manager', False)
        if not sale_manager_group:
            self.skipTest('`sale_sms` not installed')
        self.user_projectuser.write({
            'groups_id': [
                Command.link(project_user_group.id),
                Command.link(sale_manager_group.id),
            ]
        })
        self.assertTrue(self.task_cow.with_user(self.user_projectuser).check_access_rights('write'))
        with self.mockSMSGateway():
            self.task_cow.with_user(self.user_projectuser).write({
                'stage_id': self.task_stage_with_sms.id,
            })
        self.assertEqual(self.task_cow.stage_id, self.task_stage_with_sms)
        self.assertSMSIapSent([])  # no sms sent since the author is the recipient

        self.task_cow.write({
            'partner_id': self.user_portal.partner_id.id,
            'stage_id': self.project_cows.type_ids[0].id,
        })
        with self.mockSMSGateway():
            self.task_cow.with_user(self.user_projectuser).write({
                'stage_id': self.task_stage_with_sms.id,
            })
        self.assertEqual(self.task_cow.stage_id, self.task_stage_with_sms)
        self.assertSMSIapSent([self.user_portal.partner_id.mobile])
