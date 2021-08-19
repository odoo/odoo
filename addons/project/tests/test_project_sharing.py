# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import Form

from .test_project_base import TestProjectCommon


class TestProjectSharingCommon(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        project_sharing_stages_vals_list = [
            (0, 0, {'name': 'To Do', 'sequence': 1}),
            (0, 0, {'name': 'Done', 'sequence': 10}),
        ]
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
            'user_id': cls.user_projectuser.id,
            'project_id': cls.project_cows.id,
        })
        cls.task_portal = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Portal UserTask',
            'user_id': cls.user_projectuser.id,
            'project_id': cls.project_portal.id,
        })

    def get_project_sharing_form_view(self, record, with_user=None):
        return Form(
            record.with_user(with_user or self.env.user),
            view="project.project_sharing_project_task_view_form"
        )

    def get_project_sharing_access_for_user(self, with_user, project):
        project_with_user = project.with_user(with_user or self.env.user)
        return {
            'read': project_with_user._check_project_sharing_access(),
            'comment': project_with_user._check_project_sharing_access('comment'),
            'edit': project_with_user._check_project_sharing_access('edit')
        }



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
        })
        self.assertFalse(project_share_wizard.line_ids, 'No access rights should be given to a portal user in this project.')
        self.assertFalse(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user should not have accessed in project sharing views.')
        project_share_wizard.write({'line_ids': [
            Command.create({
                'user_id': self.user_portal.id,
                'access_mode': 'read',
            }),
        ]})
        project_share_wizard.action_confirm_access()
        self.assertEqual(len(self.project_portal.project_sharing_access_ids), 1, 'The access right added in project share wizard should be added in the project when the user confirm the access in the wizard.')
        self.assertDictEqual({
            'user_id': self.project_portal.project_sharing_access_ids.user_id,
            'access_mode': self.project_portal.project_sharing_access_ids.access_mode,
            'project_id': self.project_portal.project_sharing_access_ids.project_id,
        }, {
            'user_id': self.user_portal,
            'access_mode': 'read',
            'project_id': self.project_portal,
        }, 'The access rights added should be the read access for the portal project for Chell Gladys.')
        self.assertTrue(self.project_portal._check_project_sharing_access(), 'The portal user should have read access to the portal project with project sharing feature.')
        self.assertTrue(self.user_portal.partner_id in self.project_portal.message_partner_ids)

    def test_project_sharing_access(self):
        """ Check the _check_project_sharing_access returns the expected value for all access mode defined in project sharing.
        """
        self.assertDictEqual(
            self.get_project_sharing_access_for_user(self.user_public, self.project_portal),
            {
                'read': False,
                'comment': False,
                'edit': False,
            },
            'The public user should not have any access to project sharing feature of the portal project.'
        )
        self.assertDictEqual(
            self.get_project_sharing_access_for_user(self.user_projectuser, self.project_portal),
            {
                'read': True,
                'comment': True,
                'edit': True,
            },
            'The internal user should have all accesses to project sharing feature of the portal project.'
        )
        self.assertDictEqual(
            self.get_project_sharing_access_for_user(self.user_portal, self.project_portal),
            {
                'read': False,
                'comment': False,
                'edit': False,
            },
            'The portal user should not have any access to project sharing feature of the portal project.'
        )
        self.project_portal.write({
            'project_sharing_access_ids': [Command.create({
                'user_id': self.user_portal.id,
                'access_mode': 'read',
            })],
        })
        project_sharing_access = self.project_portal.project_sharing_access_ids
        self.assertDictEqual(
            self.get_project_sharing_access_for_user(self.user_portal, self.project_portal),
            {
                'read': True,
                'comment': False,
                'edit': False,
            },
            'The portal user should have only the read access to project sharing feature of the portal project.'
        )
        project_sharing_access.write({'access_mode': 'comment'})
        self.assertDictEqual(
            self.get_project_sharing_access_for_user(self.user_portal, self.project_portal),
            {
                'read': True,
                'comment': True,
                'edit': False,
            },
            'The portal user should can read and comment the tasks of the portal project in project sharing views.'
        )
        project_sharing_access.write({'access_mode': 'edit'})
        self.assertDictEqual(
            self.get_project_sharing_access_for_user(self.user_portal, self.project_portal),
            {
                'read': True,
                'comment': True,
                'edit': True,
            },
            'The portal user should can read, comment and edit the tasks of the portal project in project sharing views.'
        )

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
        self.project_portal.write({
            'project_sharing_access_ids': [
                Command.create({
                    'user_id': self.user_portal.id,
                    'access_mode': 'read',
                }),
            ],
        })
        with self.assertRaises(AccessError, msg="Should not accept the portal user create a task in the project when he has not the edit access right."):
            with self.get_project_sharing_form_view(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_portal.id}), self.user_portal) as form:
                form.name = 'Test'
                task = form.save()

        # 2) Give the 'comment' access mode to a portal user in a project and try to create task with this user.
        project_sharing_access = self.project_portal.project_sharing_access_ids
        project_sharing_access.write({'access_mode': 'comment'})
        with self.assertRaises(AccessError, msg="Should not accept the portal user create a task in the project when he has not the edit access right."):
            with self.get_project_sharing_form_view(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_portal.id}), self.user_portal) as form:
                form.name = 'Test'
                task = form.save()

        # 3) Give the 'edit' access mode to a portal user in a project and try to create task with this user.
        project_sharing_access.write({'access_mode': 'edit'})
        with self.get_project_sharing_form_view(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_portal.id}), self.user_portal) as form:
            form.name = 'Test'
            task = form.save()
            self.assertEqual(task.name, 'Test')
            self.assertEqual(task.project_id, self.project_portal)
            self.assertEqual(task.user_id, self.user_portal)
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
        """
        # 1) Give the 'read' access mode to a portal user in a project and try to create task with this user.
        project_share_wizard = self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_cows.id,
            'line_ids': [
                Command.create({
                    'user_id': self.user_portal.id,
                    'access_mode': 'read',
                }),
            ],
        })
        project_share_wizard.action_confirm_access()
        with self.assertRaises(AccessError, msg="Should not accept the portal user create a task in the project when he has not the edit access right."):
            with self.get_project_sharing_form_view(self.task_cow.with_context({'tracking_disable': True, 'default_project_id': self.project_cows.id}), self.user_portal) as form:
                form.name = 'Test'
                task = form.save()

        # 2) Give the 'comment' access mode to a portal user in a project and try to create task with this user.
        project_sharing_access = self.project_cows.project_sharing_access_ids
        project_sharing_access.write({'access_mode': 'comment'})
        with self.assertRaises(AccessError, msg="Should not accept the portal user create a task in the project when he has not the edit access right."):
            with self.get_project_sharing_form_view(self.task_cow.with_context({'tracking_disable': True, 'default_project_id': self.project_cows.id}), self.user_portal) as form:
                form.name = 'Test'
                task = form.save()

        # 3) Give the 'edit' access mode to a portal user in a project and try to create task with this user.
        project_sharing_access.write({'access_mode': 'edit'})
        with self.get_project_sharing_form_view(self.task_cow.with_context({'tracking_disable': True, 'default_project_id': self.project_cows.id, 'uid': self.user_portal.id}), self.user_portal) as form:
            form.name = 'Test'
            task = form.save()
            self.assertEqual(task.name, 'Test')
            self.assertEqual(task.project_id, self.project_cows)
            # 3.1) Try to change the project of the new task with this user.
            with self.assertRaises(AssertionError, msg="Should not accept the portal user changes the project of the task."):
                form.project_id = self.project_portal
                task = form.save()
            # 3.2) Create a sub-task
            with form.child_ids.new() as subtask_form:
                subtask_form.name = 'Test Subtask'
                with self.assertRaises(AssertionError, msg="Should not accept the portal user changes the project of the task."):
                    subtask_form.display_project_id = self.project_portal
            form.save()
            self.assertEqual(task.child_ids.name, 'Test Subtask')
            self.assertEqual(task.child_ids.project_id, self.project_cows)
            self.assertEqual(task.child_ids.user_id, self.user_portal)
