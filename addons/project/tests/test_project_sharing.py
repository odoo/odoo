# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import Form

from .test_project_base import TestProjectCommon


class TestProjectSharingCommon(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        project_sharing_stages_vals_list = [
            (0, 0, {'name': 'To Do', 'sequence': 1}),
            (0, 0, {'name': 'Done', 'sequence': 10, 'fold': True, 'rating_template_id': cls.env.ref('project.rating_project_request_email_template').id}),
        ]

        cls.partner_portal = cls.env['res.partner'].create({
            'name': 'Chell Gladys',
            'email': 'chell@gladys.portal',
            'company_id': False,
            'user_ids': [Command.link(cls.user_portal.id)]})

        cls.project_cows = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Cows',
            'privacy_visibility': 'portal',
            'alias_name': 'project+cows',
            'type_ids': project_sharing_stages_vals_list,
        })
        cls.project_portal = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Portal',
            'privacy_visibility': 'portal',
            'alias_name': 'project+portal',
            'partner_id': cls.user_portal.partner_id.id,
            'type_ids': project_sharing_stages_vals_list,
        })

        cls.task_cow = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Cow UserTask',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_cows.id,
        })
        cls.task_portal = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Portal UserTask',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_portal.id,
        })

        cls.project_sharing_form_view_xml_id = 'project.project_sharing_project_task_view_form'

    def get_project_sharing_form_view(self, record, with_user=None):
        return Form(
            record.with_user(with_user or self.env.user),
            view=self.project_sharing_form_view_xml_id
        )

@tagged('project_sharing')
class TestProjectSharing(TestProjectSharingCommon):

    def test_project_share_wizard(self):
        """ Test Project Share Wizard

            Test Cases:
            ==========
            1) Create the wizard record
            2) Check if no access rights are given to a portal user
            3) Add access rights to a portal user
        """
        project_share_wizard = self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_portal.id,
            'access_mode': 'edit',
        })
        self.assertFalse(project_share_wizard.partner_ids, 'No collaborator should be in the wizard.')
        self.assertFalse(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user should not have accessed in project sharing views.')
        project_share_wizard.write({'partner_ids': [Command.link(self.user_portal.partner_id.id)]})
        project_share_wizard.action_send_mail()
        self.assertEqual(len(self.project_portal.collaborator_ids), 1, 'The access right added in project share wizard should be added in the project when the user confirm the access in the wizard.')
        self.assertDictEqual({
            'partner_id': self.project_portal.collaborator_ids.partner_id,
            'project_id': self.project_portal.collaborator_ids.project_id,
        }, {
            'partner_id': self.user_portal.partner_id,
            'project_id': self.project_portal,
        }, 'The access rights added should be the read access for the portal project for Chell Gladys.')
        self.assertTrue(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user should have read access to the portal project with project sharing feature.')

    def test_project_sharing_access(self):
        """ Check if the different user types can access to project sharing feature as expected. """
        with self.assertRaises(AccessError, msg='The public user should not have any access to project sharing feature of the portal project.'):
            self.project_portal.with_user(self.user_public)._check_project_sharing_access()
        self.assertTrue(self.project_portal.with_user(self.user_projectuser)._check_project_sharing_access(), 'The internal user should have all accesses to project sharing feature of the portal project.')
        self.assertFalse(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user should not have any access to project sharing feature of the portal project.')
        self.project_portal.write({'collaborator_ids': [Command.create({'partner_id': self.user_portal.partner_id.id})]})
        self.assertTrue(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user can access to project sharing feature of the portal project.')

    def test_create_task_in_project_sharing(self):
        """ Test when portal user creates a task in project sharing views.

            Test Cases:
            ==========
            1) Give the 'read' access mode to a portal user in a project and try to create task with this user.
            2) Give the 'comment' access mode to a portal user in a project and try to create task with this user.
            3) Give the 'edit' access mode to a portal user in a project and try to create task with this user.
            3.1) Try to change the project of the new task with this user.
        """
        # 1) Give the 'read' access mode to a portal user in a project and try to create task with this user.
        with self.assertRaises(AccessError, msg="Should not accept the portal user create a task in the project when he has not the edit access right."):
            with self.get_project_sharing_form_view(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_portal.id}), self.user_portal) as form:
                form.name = 'Test'
                task = form.save()

        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        with self.get_project_sharing_form_view(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_portal.id}), self.user_portal) as form:
            form.name = 'Test'
            task = form.save()
            self.assertEqual(task.name, 'Test')
            self.assertEqual(task.project_id, self.project_portal)
            self.assertFalse(task.portal_user_names)
            # 3.1) Try to change the project of the new task with this user.
            with self.assertRaises(AssertionError, msg="Should not accept the portal user changes the project of the task."):
                form.project_id = self.project_cows
                task = form.save()

    def test_edit_task_in_project_sharing(self):
        """ Test when portal user creates a task in project sharing views.

            Test Cases:
            ==========
            1) Give the 'read' access mode to a portal user in a project and try to edit task with this user.
            2) Give the 'comment' access mode to a portal user in a project and try to edit task with this user.
            3) Give the 'edit' access mode to a portal user in a project and try to create task with this user.
            3.1) Try to change the project of the new task with this user.
            3.2) Create a sub-task
            3.3) Create a second sub-task
        """
        # 1) Give the 'read' access mode to a portal user in a project and try to create task with this user.
        with self.assertRaises(AccessError, msg="Should not accept the portal user create a task in the project when he has not the edit access right."):
            with self.get_project_sharing_form_view(self.task_cow.with_context({'tracking_disable': True, 'default_project_id': self.project_cows.id}), self.user_portal) as form:
                form.name = 'Test'
                task = form.save()

        project_share_wizard = self.env['project.share.wizard'].create({
            'access_mode': 'edit',
            'res_model': 'project.project',
            'res_id': self.project_cows.id,
            'partner_ids': [
                Command.link(self.user_portal.partner_id.id),
            ],
        })
        project_share_wizard.action_send_mail()

        with self.get_project_sharing_form_view(self.task_cow.with_context({'tracking_disable': True, 'default_project_id': self.project_cows.id, 'uid': self.user_portal.id}), self.user_portal) as form:
            form.name = 'Test'
            task = form.save()
            self.assertEqual(task.name, 'Test')
            self.assertEqual(task.project_id, self.project_cows)

        # 3.1) Try to change the project of the new task with this user.
        with self.assertRaises(AssertionError, msg="Should not accept the portal user changes the project of the task."):
            with self.get_project_sharing_form_view(task, self.user_portal) as form:
                form.project_id = self.project_portal

        # 3.2) Create a sub-task
        with self.get_project_sharing_form_view(task, self.user_portal) as form:
            with form.child_ids.new() as subtask_form:
                subtask_form.name = 'Test Subtask'
                with self.assertRaises(AssertionError, msg="Should not accept the portal user changes the project of the task."):
                    subtask_form.display_project_id = self.project_portal
        self.assertEqual(task.child_ids.name, 'Test Subtask')
        self.assertEqual(task.child_ids.project_id, self.project_cows)
        self.assertFalse(task.child_ids.portal_user_names, 'by default no user should be assigned to a subtask created by the portal user.')
        self.assertFalse(task.child_ids.user_ids, 'No user should be assigned to the new subtask.')

        task2 = self.env['project.task'] \
            .with_context({
                'tracking_disable': True,
                'default_project_id': self.project_cows.id,
                'default_user_ids': [Command.set(self.user_portal.ids)],
            }) \
            .with_user(self.user_portal) \
            .create({'name': 'Test'})
        self.assertFalse(task2.portal_user_names, 'the portal user should not be assigned when the portal user creates a task into the project shared.')

        # 3.3) Create a second sub-task
        with self.get_project_sharing_form_view(task, self.user_portal) as form:
            with form.child_ids.new() as subtask_form:
                subtask_form.name = 'Test Subtask'
        self.assertEqual(len(task.child_ids), 2, 'Check 2 subtasks has correctly been created by the user portal.')

    def test_portal_user_cannot_see_all_assignees(self):
        """ Test when the portal sees a task he cannot see all the assignees.

            Because of a ir.rule in res.partner filters the assignees, the portal
            can only see the assignees in the same company than him.

            Test Cases:
            ==========
            1) add many assignees in a task
            2) check the portal user can read no assignee in this task. Should have an AccessError exception
        """
        self.task_cow.write({'user_ids': [Command.link(self.user_projectmanager.id)]})
        with self.assertRaises(AccessError, msg="Should not accept the portal user to access to a task he does not follow it and its project."):
            self.task_cow.with_user(self.user_portal).read(['portal_user_names'])
        self.assertEqual(len(self.task_cow.user_ids), 2, '2 users should be assigned in this task.')

        project_share_wizard = self.env['project.share.wizard'].create({
            'access_mode': 'edit',
            'res_model': 'project.project',
            'res_id': self.project_cows.id,
            'partner_ids': [
                Command.link(self.user_portal.partner_id.id),
            ],
        })
        project_share_wizard.action_send_mail()

        self.assertFalse(self.task_cow.with_user(self.user_portal).user_ids, 'the portal user should see no assigness in the task.')
        task_portal_read = self.task_cow.with_user(self.user_portal).read(['portal_user_names'])
        self.assertEqual(self.task_cow.portal_user_names, task_portal_read[0]['portal_user_names'], 'the portal user should see assignees name in the task via the `portal_user_names` field.')

    def test_portal_user_can_change_stage_with_rating(self):
        """ Test portal user can change the stage of task to a stage with rating template email

            The user should be able to change the stage and the email should be sent as expected
            if a email template is set in `rating_template_id` field in the new stage.
        """
        self.project_portal.write({
            'rating_active': True,
            'rating_status': 'stage',
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        self.task_portal.with_user(self.user_portal).write({'stage_id': self.project_portal.type_ids[-1].id})
