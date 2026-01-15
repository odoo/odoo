# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.fields import Command, Domain
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

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
        cls.project_portal.message_subscribe(partner_ids=[cls.partner_portal.id])

        cls.project_no_collabo = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'No Collabo',
            'privacy_visibility': 'followers',
            'alias_name': 'project+nocollabo',
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
        cls.task_no_collabo = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'No Collabo Task',
            'project_id': cls.project_no_collabo.id,
        })

        cls.task_tag = cls.env['project.tags'].create({'name': 'Foo'})

        cls.project_sharing_form_view_xml_id = 'project.project_sharing_project_task_view_form'

    def get_project_sharing_form_view(self, record, with_user=None):
        return Form(
            record.with_user(with_user or self.env.user),
            view=self.project_sharing_form_view_xml_id
        )

    def get_project_share_link(self):
        self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_no_collabo.id,
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id, 'access_mode': 'edit'}),
            ],
        }).action_send_mail()
        return self.env['mail.message'].search([
            ('partner_ids', 'in', self.user_portal.partner_id.id),
        ])


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
        self.project_portal.message_unsubscribe(partner_ids=self.user_portal.partner_id.ids)
        project_share_form = Form(self.env['project.share.wizard'].with_context(active_model='project.project', active_id=self.project_portal.id))
        self.assertFalse(project_share_form.collaborator_ids, 'No collaborator should be in the wizard.')
        with self.assertRaises(AccessError, msg='The public user should not have any access to project sharing feature of the portal project.'):
            self.project_portal.with_user(self.user_portal)._check_project_sharing_access()
        with project_share_form.collaborator_ids.new() as collaborator_form:
            collaborator_form.partner_id = self.user_portal.partner_id
            collaborator_form.access_mode = 'edit'
        project_share_wizard = project_share_form.save()
        project_share_wizard.action_send_mail()
        self.assertEqual(len(self.project_portal.collaborator_ids), 1, 'The access right added in project share wizard should be added in the project when the user confirm the access in the wizard.')
        self.assertDictEqual({
            'partner_id': self.project_portal.collaborator_ids.partner_id,
            'project_id': self.project_portal.collaborator_ids.project_id,
            'limited_access': self.project_portal.collaborator_ids.limited_access,
        }, {
            'partner_id': self.user_portal.partner_id,
            'project_id': self.project_portal,
            'limited_access': False,
        }, 'The access rights added should be the read access for the portal project for Chell Gladys.')
        self.assertTrue(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user should have read access to the portal project with project sharing feature.')
        project_share_wizard = self.env['project.share.wizard'].with_context(active_model="project.project", active_id=self.project_portal.id).new({})
        self.assertEqual(len(project_share_wizard.collaborator_ids), 1, 'The access right added in project share wizard should be added in the project when the user confirm the access in the wizard.')
        self.assertDictEqual({
            'partner_id': project_share_wizard.collaborator_ids.partner_id,
            'access_mode': project_share_wizard.collaborator_ids.access_mode,
        }, {
            'partner_id': self.user_portal.partner_id,
            'access_mode': 'edit',
        })

    def test_project_share_wizard_add_collaborator_with_limited_access(self):
        ProjectShare = self.env['project.share.wizard'].with_context(active_model="project.project", active_id=self.project_portal.id)
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.partner_1.id}),
            ],
        })
        self.project_portal.message_unsubscribe(partner_ids=[self.user_portal.partner_id.id])
        project_share_form = Form(ProjectShare)
        self.assertEqual(len(project_share_form.collaborator_ids), 1)
        with project_share_form.collaborator_ids.new() as collaborator_form:
            collaborator_form.partner_id = self.user_portal.partner_id
            collaborator_form.access_mode = 'edit_limited'
        project_share_wizard = project_share_form.save()
        project_share_wizard.action_send_mail()
        self.assertEqual(len(self.project_portal.collaborator_ids), 2, 'The access right added in project share wizard should be added in the project when the user confirm the access in the wizard.')
        self.assertEqual(self.project_portal.collaborator_ids.partner_id, self.user_portal.partner_id + self.partner_1)
        for collaborator in self.project_portal.collaborator_ids:
            collaborator_vals = {
                'partner_id': collaborator.partner_id,
                'project_id': collaborator.project_id,
                'limited_access': collaborator.limited_access,
            }
            if collaborator.partner_id == self.user_portal.partner_id:
                self.assertDictEqual(collaborator_vals, {
                    'partner_id': self.user_portal.partner_id,
                    'project_id': self.project_portal,
                    'limited_access': True,
                })
            else:
                self.assertDictEqual(collaborator_vals, {
                    'partner_id': self.partner_1,
                    'project_id': self.project_portal,
                    'limited_access': False,
                })
        self.assertTrue(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user should have read access to the portal project with project sharing feature.')

        project_share_wizard = ProjectShare.new({})
        self.assertEqual(len(project_share_wizard.collaborator_ids), 2, 'The access right added in project share wizard should be added in the project when the user confirm the access in the wizard.')
        for collaborator in project_share_wizard.collaborator_ids:
            collaborator_vals = {
                'partner_id': collaborator.partner_id,
                'access_mode': collaborator.access_mode,
            }
            if collaborator.partner_id == self.user_portal.partner_id:
                self.assertDictEqual(collaborator_vals, {
                    'partner_id': self.user_portal.partner_id,
                    'access_mode': 'edit_limited',
                })
            else:
                self.assertDictEqual(collaborator_vals, {
                    'partner_id': self.partner_1,
                    'access_mode': 'edit',
                })

    def test_project_share_wizard_remove_collaborators(self):
        PortalShare = self.env['project.share.wizard'].with_context(active_model="project.project", active_id=self.project_portal.id)
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
                Command.create({'partner_id': self.partner_1.id, 'limited_access': True}),
            ],
        })
        self.project_portal.message_subscribe(partner_ids=[self.partner_2.id])
        with Form(PortalShare) as project_share_form:
            self.assertEqual(len(project_share_form.collaborator_ids), 3, "2 external collaborators should be found for that project.")
            collaborator_vals_per_id = project_share_form.collaborator_ids._field_value._data
            collaborator_access_mode_per_partner_id = {
                c['partner_id']: c['access_mode']
                for c in collaborator_vals_per_id.values()
            }
            self.assertIn(self.user_portal.partner_id.id, collaborator_access_mode_per_partner_id)
            self.assertIn(self.partner_1.id, collaborator_access_mode_per_partner_id)
            self.assertIn(self.partner_2.id, collaborator_access_mode_per_partner_id)
            access_mode_expected_per_partner_id = {
                self.user_portal.partner_id.id: 'edit',
                self.partner_1.id: 'edit_limited',
                self.partner_2.id: 'read',
            }
            self.assertDictEqual(collaborator_access_mode_per_partner_id, access_mode_expected_per_partner_id)
            collaborator_ids_to_remove = {c_id for c_id, vals in collaborator_vals_per_id.items() if vals['access_mode'] != 'read'}
            index = 0
            for collaborator_id in project_share_form.collaborator_ids.ids:
                if collaborator_id in collaborator_ids_to_remove:
                    project_share_form.collaborator_ids.remove(index)
                else:
                    index += 1

        self.assertFalse(self.project_portal.collaborator_ids)
        self.assertIn(self.partner_2, self.project_portal.message_partner_ids, "The readonly partner should still be a follower.")
        self.assertNotIn(self.user_portal.partner_id, self.project_portal.message_partner_ids, "The readonly partner should still be a follower.")
        self.assertNotIn(self.partner_1, self.project_portal.message_partner_ids, "The readonly partner should still be a follower.")

    def test_project_share_wizard_alter_access_mode_collaborators(self):
        ProjectShare = self.env['project.share.wizard'].with_context(active_model="project.project", active_id=self.project_portal.id)
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
                Command.create({'partner_id': self.partner_1.id, 'limited_access': True}),
            ],
            'message_partner_ids': [  # readonly access
                Command.link(self.partner_2.id),
            ],
        })
        with Form(ProjectShare) as project_share_form:
            access_updated_per_partner_id = {
                self.user_portal.partner_id.id: 'edit_limited',
                self.partner_2.id: 'edit',
            }
            for index in range(len(project_share_form.collaborator_ids.ids)):
                with project_share_form.collaborator_ids.edit(index) as collaborator_form:
                    if collaborator_form.partner_id.id in access_updated_per_partner_id:
                        collaborator_form.access_mode = access_updated_per_partner_id[collaborator_form.partner_id.id]

        self.assertEqual(len(self.project_portal.collaborator_ids), 3, "3 collaborators should be found for that project.")
        self.assertEqual(
            self.project_portal.collaborator_ids.partner_id,
            self.user_portal.partner_id + self.partner_1 + self.partner_2,
            "The collaborators should be the portal user, Valid Lelitre and Valid Poilvache.",
        )
        self.assertEqual(
            self.project_portal.collaborator_ids.filtered(lambda c: c.limited_access).partner_id,
            self.user_portal.partner_id + self.partner_1,
            "The portal user and Valid Lelitre should have limited access.",
        )

    def test_project_sharing_access(self):
        """ Check if the different user types can access to project sharing feature as expected. """
        with self.assertRaises(AccessError, msg='The public user should not have any access to project sharing feature of the portal project.'):
            self.project_portal.with_user(self.user_public)._check_project_sharing_access()
        self.assertTrue(self.project_portal.with_user(self.user_projectuser)._check_project_sharing_access(), 'The internal user should have all accesses to project sharing feature of the portal project.')
        self.assertFalse(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user should not have any access to project sharing feature of the portal project.')
        self.project_portal.write({'collaborator_ids': [Command.create({'partner_id': self.user_portal.partner_id.id})]})
        self.assertTrue(self.project_portal.with_user(self.user_portal)._check_project_sharing_access(), 'The portal user can access to project sharing feature of the portal project.')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_create_task_in_project_sharing(self):
        """ Test when portal user creates a task in project sharing views.

            Test Cases:
            ==========
            1) Give the 'read' access mode to a portal user in a project and try to create task with this user.
            2) Give the 'comment' access mode to a portal user in a project and try to create task with this user.
            3) Give the 'edit' access mode to a portal user in a project and try to create task with this user.
            3.1) Try to change the project of the new task with this user.
        """
        Task = self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_portal.id, 'default_user_ids': [(4, self.user_portal.id)]})
        # 1) Give the 'read' access mode to a portal user in a project and try to create task with this user.
        with self.assertRaises(AccessError, msg="Should not accept the portal user create a task in the project when he has not the edit access right."):
            with self.get_project_sharing_form_view(Task, self.user_portal) as form:
                form.name = 'Test'
                task = form.save()

        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        with self.get_project_sharing_form_view(Task, self.user_portal) as form:
            form.name = 'Test'
            with form.child_ids.new() as subtask_form:
                subtask_form.name = 'Test Subtask'
            task = form.save()
            self.assertEqual(task.name, 'Test')
            self.assertEqual(task.project_id, self.project_portal)
            self.assertFalse(task.portal_user_names)
            self.assertTrue(task.stage_id)

            # Check creating a sub-task while creating the parent task works as expected.
            self.assertEqual(task.child_ids.name, 'Test Subtask')
            self.assertEqual(task.child_ids.project_id, self.project_portal)
            self.assertFalse(task.child_ids.portal_user_names, 'by default no user should be assigned to a subtask created by the portal user.')
            self.assertFalse(task.child_ids.user_ids, 'No user should be assigned to the new subtask.')

            # 3.1) Try to change the project of the new task with this user.
            with self.assertRaises(AssertionError, msg="Should not accept the portal user changes the project of the task."):
                form.project_id = self.project_cows
                task = form.save()

        Task = Task.with_user(self.user_portal)

        # Allow to set as parent a task he has access to
        task = Task.create({'name': 'foo', 'parent_id': self.task_portal.id})
        self.assertEqual(task.parent_id, self.task_portal)
        # Disallow to set as parent a task he doesn't have access to
        with self.assertRaises(AccessError, msg="Should not accept the portal user to set a parent task he doesn't have access to."):
            Task.create({'name': 'foo', 'parent_id': self.task_no_collabo.id})
        with self.assertRaises(AccessError, msg="Should not accept the portal user to set a parent task he doesn't have access to."):
            task = Task.with_context(default_parent_id=self.task_no_collabo.id).create({'name': 'foo'})

        # Create/Update a forbidden task through child_ids
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create({'name': 'foo', 'child_ids': [Command.update(self.task_no_collabo.id, {'name': 'Foo'})]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create({'name': 'foo', 'child_ids': [Command.delete(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create({'name': 'foo', 'child_ids': [Command.unlink(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create({'name': 'foo', 'child_ids': [Command.link(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create({'name': 'foo', 'child_ids': [Command.set([self.task_no_collabo.id])]})

        # Same thing but using context defaults
        # However, cache is updated, but nothing is written.
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.with_context(default_child_ids=[Command.update(self.task_no_collabo.id, {'name': 'Foo'})]).create({'name': 'foo'})
        with Task.env.cr.savepoint() as sp:
            task = Task.with_context(default_child_ids=[Command.delete(self.task_no_collabo.id)]).create({'name': 'foo'})
            task.env.invalidate_all()
            self.assertTrue(self.task_no_collabo.exists(), "Task should still be there, no delete is sent")
            sp.rollback()
        with self.env.cr.savepoint() as sp:
            self.task_no_collabo.parent_id = self.task_no_collabo.create({'name': 'parent collabo'})
            task = Task.with_context(default_child_ids=[Command.unlink(self.task_no_collabo.id)]).create({'name': 'foo'})
            task.env.invalidate_all()
            self.assertTrue(self.task_no_collabo.parent_id, "Task should still be there, no delete is sent")
            sp.rollback()
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task = Task.with_context(default_child_ids=[Command.link(self.task_no_collabo.id)]).create({'name': 'foo'})
            task.env.invalidate_all()
            self.assertFalse(task.child_ids)
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task = Task.with_context(default_child_ids=[Command.set([self.task_no_collabo.id])]).create({'name': 'foo'})
            task.env.invalidate_all()
            self.assertFalse(task.child_ids)

        # Create/update a tag through tag_ids
        with self.assertRaisesRegex(AccessError, "not allowed to create 'Project Tags'"):
            Task.create({'name': 'foo', 'tag_ids': [Command.create({'name': 'Bar'})]})
        with self.assertRaisesRegex(AccessError, "not allowed to modify 'Project Tags'"):
            Task.create({'name': 'foo', 'tag_ids': [Command.update(self.task_tag.id, {'name': 'Bar'})]})
        with self.assertRaisesRegex(AccessError, "not allowed to delete 'Project Tags'"):
            Task.create({'name': 'foo', 'tag_ids': [Command.delete(self.task_tag.id)]})

        # Same thing but using context defaults
        with self.assertRaisesRegex(AccessError, "not allowed to create 'Project Tags'"):
            Task.with_context(default_tag_ids=[Command.create({'name': 'Bar'})]).create({'name': 'foo'})
        with Task.env.cr.savepoint() as sp:
            task = Task.with_context(default_tag_ids=[Command.update(self.task_tag.id, {'name': 'Bar'})]).create({'name': 'foo'})
            task.env.invalidate_all()
            self.assertNotEqual(self.task_tag.name, 'Bar')
            sp.rollback()
        with Task.env.cr.savepoint() as sp:
            Task.with_context(default_tag_ids=[Command.delete(self.task_tag.id)]).create({'name': 'foo'})
            task.env.invalidate_all()
            self.assertTrue(self.task_tag.exists())
            sp.rollback()

        task = Task.create({'name': 'foo', 'color': 1, 'tag_ids': [Command.link(self.task_tag.id)]})
        self.assertEqual(task.color, 1)
        self.assertEqual(task.tag_ids, self.task_tag)

        task = Task.create({'name': 'foo', 'color': 4, 'tag_ids': [Command.set([self.task_tag.id])]})
        self.assertEqual(task.color, 4)
        self.assertEqual(task.tag_ids, self.task_tag)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
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
            'res_model': 'project.project',
            'res_id': self.project_cows.id,
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id, 'access_mode': 'edit'}),
            ],
        })
        project_share_wizard.action_send_mail()
        # the portal user is set as follower for the task_cow. Without it he does not have read access to the task, and thus can not access its view form
        self.task_cow.message_subscribe(partner_ids=self.user_portal.partner_id.ids)
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
                    subtask_form.project_id = self.project_portal
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

        # Allow to set as parent a task he has access to
        task.write({'parent_id': self.task_portal.id})
        self.assertEqual(task.parent_id, self.task_portal)
        # Disallow to set as parent a task he doesn't have access to
        with self.assertRaises(AccessError, msg="Should not accept the portal user to set a parent task he doesn't have access to."):
            task.write({'parent_id': self.task_no_collabo.id})

        # Create/Update a forbidden task through child_ids
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({'child_ids': [Command.update(self.task_no_collabo.id, {'name': 'Foo'})]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({'child_ids': [Command.delete(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({'child_ids': [Command.unlink(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({'child_ids': [Command.link(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({'child_ids': [Command.set([self.task_no_collabo.id])]})

        # Create/update a tag through tag_ids
        with self.assertRaisesRegex(AccessError, "not allowed to create 'Project Tags'"):
            task.write({'tag_ids': [Command.create({'name': 'Bar'})]})
        with self.assertRaisesRegex(AccessError, "not allowed to modify 'Project Tags'"):
            task.write({'tag_ids': [Command.update(self.task_tag.id, {'name': 'Bar'})]})
        with self.assertRaisesRegex(AccessError, "not allowed to delete 'Project Tags'"):
            task.write({'tag_ids': [Command.delete(self.task_tag.id)]})

        task.write({'tag_ids': [Command.link(self.task_tag.id)]})
        self.assertEqual(task.tag_ids, self.task_tag)

        task.write({'tag_ids': [Command.unlink(self.task_tag.id)]})
        self.assertFalse(task.tag_ids)

        task.write({'tag_ids': [Command.link(self.task_tag.id)]})
        task.write({'tag_ids': [Command.clear()]})
        self.assertFalse(task.tag_ids, [])

        task.write({'tag_ids': [Command.set([self.task_tag.id])]})
        self.assertEqual(task.tag_ids, self.task_tag)


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
            'res_model': 'project.project',
            'res_id': self.project_cows.id,
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id, 'access_mode': 'edit'}),
            ],
        })
        project_share_wizard.action_send_mail()
        # subscribe the portal user to give him read access to the task.
        self.task_cow.message_subscribe(partner_ids=self.user_portal.partner_id.ids)
        self.assertFalse(self.task_cow.with_user(self.user_portal).user_ids, 'the portal user should see no assigness in the task.')
        task_portal_read = self.task_cow.with_user(self.user_portal).read(['portal_user_names'])
        self.assertEqual(self.task_cow.portal_user_names, task_portal_read[0]['portal_user_names'], 'the portal user should see assignees name in the task via the `portal_user_names` field.')

    def test_portal_user_can_change_stage_with_rating(self):
        """ Test portal user can change the stage of task to a stage with rating template email

            The user should be able to change the stage and the email should be sent as expected
            if a email template is set in `rating_template_id` field in the new stage.
        """
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        stage = self.project_portal.type_ids[-1]
        stage.write({
            'rating_active': True,
            'rating_status': 'stage',
        })
        self.task_portal.with_user(self.user_portal).write({'stage_id': stage.id})

    def test_orm_method_with_true_false_domain(self):
        """ Test orm method overriden in project for project sharing works

            Test Case
            =========
            1) Share a project in edit mode for portal user
            2) Search the portal task contained in the project shared by using a TRUE domain
            3) Check the task is found with the `search` method
            4) Search the task with `FALSE` and check no task is found with `search` method
            5) Call `read_group` method with `TRUE` in the domain and check if the task is found
            6) Call `read_group` method with `FALSE` in the domain and check if no task is found
        """
        domain = Domain('id', '=', self.task_portal.id)
        self.project_portal.write({
            'collaborator_ids': [Command.create({
                'partner_id': self.user_portal.partner_id.id,
            })],
        })
        task = self.env['project.task'].with_user(self.user_portal).search(domain)
        self.assertTrue(task, 'The task should be found.')
        task = self.env['project.task'].with_user(self.user_portal).search(Domain.FALSE)
        self.assertFalse(task, 'No task should be found since the domain contained a falsy tuple.')

        task_read_group = self.env['project.task'].formatted_read_group(
            domain,
            aggregates=['id:min', '__count'],
        )
        self.assertEqual(task_read_group[0]['__count'], 1, 'The task should be found with the formatted_read_group method containing a truly tuple.')
        self.assertEqual(task_read_group[0]['id:min'], self.task_portal.id, 'The task should be found with the formatted_read_group method containing a truly tuple.')

        task_read_group = self.env['project.task'].formatted_read_group(
            Domain.FALSE,
            aggregates=['__count'],
        )
        self.assertFalse(task_read_group[0]['__count'], 'No result should found with the formatted_read_group since the domain is falsy.')

    def test_milestone_read_access_right(self):
        """ This test ensures that a portal user has read access on the milestone of the project that was shared with him """

        project_milestone = self.env['project.milestone'].create({
            'name': 'Test Project Milestone',
            'project_id': self.project_portal.id,
        })
        with self.assertRaises(AccessError, msg="Should not accept the portal user to access to a milestone if he's not a collaborator of its project."):
            project_milestone.with_user(self.user_portal).read(['name'])

        self.project_portal.write({
            'collaborator_ids': [Command.create({
                'partner_id': self.user_portal.partner_id.id,
            })],
        })
        # Reading the milestone should no longer trigger an access error.
        project_milestone.with_user(self.user_portal).read(['name'])
        with self.assertRaises(AccessError, msg="Should not accept the portal user to update a milestone."):
            project_milestone.with_user(self.user_portal).write(['name'])
        with self.assertRaises(AccessError, msg="Should not accept the portal user to delete a milestone."):
            project_milestone.with_user(self.user_portal).unlink()
        with self.assertRaises(AccessError, msg="Should not accept the portal user to create a milestone."):
            self.env['project.milestone'].with_user(self.user_portal).create({
                'name': 'Test Project new Milestone',
                'project_id': self.project_portal.id,
            })

    def test_add_followers_from_share_edit_wizard(self):
        """
            This test ensures that when a project is shared in edit mode, the partners are correctly set as follower in the project and their respective tasks.
        """
        company_partner = self.env.company.partner_id
        partners = partner_a, partner_b, partner_d = self.env['res.partner'].create([
            {'name': "Solanum", 'parent_id': company_partner.id},
            {'name': "Zana", 'parent_id': company_partner.id},
            {'name': "Thresh"},
        ])
        partners |= company_partner
        project_to_share = self.env['project.project'].create({'name': "project to share"})
        task_with_partner_1, task_with_partner_2, task_with_parent_partner, task_without_partner = self.env['project.task'].create([{
            'name': "Task with partner 1",
            'partner_id': partner_a.id,
            'project_id': project_to_share.id,
        }, {
            'name': "Task with partner 2",
            'partner_id': partner_b.id,
            'project_id': project_to_share.id,
        }, {
            'name': "Task with company",
            'partner_id': company_partner.id,
            'project_id': project_to_share.id,
        }, {
            'name': "Task with no partner",
            'project_id': project_to_share.id,
        }])
        project_to_share._add_followers(partners)

        self.assertEqual(partners, project_to_share.message_partner_ids, "All the partner should be set as a new follower of the project")
        self.assertEqual(partner_a, task_with_partner_1.message_partner_ids, "Only the first partner should be set as a new follower for the task 1")
        self.assertEqual(partner_b, task_with_partner_2.message_partner_ids, "Only the second partner should be set as a new follower for the task 2")
        self.assertEqual(partners - partner_d, task_with_parent_partner.message_partner_ids,
                         "The first, second, and the company partner should be set as new followers for the task 3 because the partner of this task is the parent of the other 2")
        self.assertFalse(task_without_partner.message_partner_ids, "Since this task has no partner, no follower should be added")

    def test_project_manager_remains_follower_after_sharing(self):
        """
        Test that the project manager remains a follower when collaborators are added
        """
        project = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'project',
            'privacy_visibility': 'followers',
            'user_id': self.user_projectmanager.id,
        })
        self.assertIn(self.user_projectmanager.partner_id, project.message_partner_ids, "Project manager should be a follower of the project")
        project_share_wizard = self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': project.id,
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id, 'access_mode': 'read'}),
            ],
        })
        project_share_wizard.action_send_mail()
        self.assertIn(self.user_projectmanager.partner_id, project.message_partner_ids, "Project manager should still be a follower after sharing the project")
        self.assertEqual(len(project.message_follower_ids), 2, "number of followers should be 2")
