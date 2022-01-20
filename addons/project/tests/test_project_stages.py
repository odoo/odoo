# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_project_base import TestProjectCommon
from odoo.addons.mail.tests.common import MockEmail

class TestProjectStages(TestProjectCommon, MockEmail):
    @classmethod
    def setUpClass(cls):
        super(TestProjectStages, cls).setUpClass()

        # Enable the company setting
        cls.env['res.config.settings'].create({
            'group_project_stages': True
        }).execute()

        cls.stage_a = cls.env['project.project.stage'].create({'name': 'a', 'sequence': 1})
        cls.stage_b = cls.env['project.project.stage'].create({'name': 'b', 'sequence': 10})
        cls.project_bird = cls.env['project.project'].with_context(mail_create_nolog=True).create({
            'name': 'Test Project',
            'partner_id': cls.partner_1.id,
        })

    def test_project_stages_creation(self):
        self.assertTrue(self.stage_a, "Check Stage a should be created")
        self.assertTrue(self.stage_b, "Check Stage b should be created")
        self.assertEqual(self.project_bird.stage_id, self.stage_a, "Check project bird is in stage a")

    def test_send_email_project_stages_change(self):
        project_complete_mail_template = self.env.ref('project.project_done_email_template')
        self.stage_b.write({'mail_template_id': project_complete_mail_template.id})

        with self.mock_mail_gateway():
            self.project_bird.with_user(self.user_projectmanager).write({'stage_id': self.stage_b.id})
        self.project_bird._message_track_post_template('stage_id')

        self.assertEqual(len(self.project_bird.message_ids), 1, "Email should be automatically sent when switching the project stage")
