# -*- coding: utf-8 -*-

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestProjectSharingUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nolog': True}).create({
            'name': 'Georges',
            'login': 'georges1',
            'password': 'georges1',
            'email': 'georges@project.portal',
            'signature': 'SignGeorges',
            'notification_type': 'email',
            'groups_id': [Command.set([cls.env.ref('base.group_portal').id])],
        })

        cls.partner_portal = cls.env['res.partner'].with_context({'mail_create_nolog': True}).create({
            'name': 'Georges',
            'email': 'georges@project.portal',
            'company_id': False,
            'user_ids': [user.id],
        })
        cls.project_portal = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Project Sharing',
            'privacy_visibility': 'portal',
            'alias_name': 'project+sharing',
            'partner_id': cls.partner_portal.id,
            'type_ids': [
                Command.create({'name': 'To Do', 'sequence': 1}),
                Command.create({'name': 'Done', 'sequence': 10})
            ],
        })
        cls.env['res.config.settings'].create({'group_project_milestone': True}).execute()

    def test_blocked_task_with_project_sharing_string_portal(self):
        """
        Ensure the portal user shows the message 'This task is currently blocked...'.
        Flow:
            - Activated Task Dependencies in a portal project
            - Create a 'New' task stage
            - Create a project(Test Project)
            - Ensure the portal user receives the message 'This task is currently blocked..'.
            - Create task(Test Task)
            - Create a task with a Blocked task (Test Task)
        """

        self.project_portal.write({
            'allow_task_dependencies': True,
            'collaborator_ids': [
                Command.create({'partner_id': self.partner_portal.id}),
            ],
        })

        project = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test Project',
        })

        self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_portal.id,
            'collaborator_ids': [
                Command.create({'partner_id': self.partner_portal.id, 'access_mode': 'edit'}),
            ],
        })

        task = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test Task',
            'project_id': project.id,
        })

        self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Portal Task',
            'project_id': self.project_portal.id,
            'depend_on_ids': task.ids,
            'stage_id': self.project_portal.type_ids[0].id,
        })

        self.start_tour("/odoo", 'project_sharing_with_blocked_task_tour', login="georges1")

    def test_01_project_sharing(self):
        """ Test Project Sharing UI with an internal user """
        self.start_tour("/odoo", 'project_sharing_tour', login="admin")

    def test_02_project_sharing(self):
        """ Test project sharing ui with a portal user.

            The additional data created here are the data created in the first test with the tour js.

            Since a problem to logout Mitchell Admin to log in as Georges user, this test is created
            to launch a tour with portal user.
        """
        self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_portal.id,
            'collaborator_ids': [
                Command.create({'partner_id': self.partner_portal.id, 'access_mode': 'edit'}),
            ],
        })

        self.project_portal.write({
            'task_ids': [Command.create({
                'name': "Test Project Sharing",
                'stage_id': self.project_portal.type_ids.filtered(lambda stage: stage.sequence == 10)[:1].id,
            })],
        })
        self.start_tour("/my/projects", 'portal_project_sharing_tour', login='georges1')

    def test_03_project_sharing(self):
        self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_portal.id,
            'collaborator_ids': [
                Command.create({'partner_id': self.partner_portal.id, 'access_mode': 'edit'}),
            ],
        })

        self.project_portal.write({
            'task_ids': [Command.create({
                'name': "Test Project Sharing",
                'stage_id': self.project_portal.type_ids.filtered(lambda stage: stage.sequence == 10)[:1].id,
            })],
            'allow_milestones': False,
        })
        self.start_tour("/my/projects", 'portal_project_sharing_tour_with_disallowed_milestones', login='georges1')
