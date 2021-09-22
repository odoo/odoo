# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import users
from odoo.tools import mute_logger

class TestAccessRights(TestProjectCommon):
    def setUp(self):
        super().setUp()
        self.task = self.create_task('Make the world a better place')
        self.user = mail_new_test_user(self.env, 'Internal user', groups='base.group_user')
        self.portal = mail_new_test_user(self.env, 'Portal user', groups='base.group_portal')

    def create_task(self, name, *, with_user=None, **kwargs):
        values = dict(name=name, project_id=self.project_pigs.id, **kwargs)
        return self.env['project.task'].with_user(with_user or self.env.user).create(values)

class TestCRUDVisibilityFollowers(TestAccessRights):

    def setUp(self):
        super().setUp()
        self.project_pigs.privacy_visibility = 'followers'

    @users('Internal user', 'Portal user')
    def test_project_no_write(self):
        with self.assertRaises(AccessError, msg="%s should not be able to write on the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).name = "Take over the world"

        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        with self.assertRaises(AccessError, msg="%s should not be able to write on the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).name = "Take over the world"

    @users('Internal user', 'Portal user')
    def test_project_no_unlink(self):
        self.project_pigs.task_ids.unlink()
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).unlink()

        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        self.project_pigs.task_ids.unlink()
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).unlink()

    @users('Internal user', 'Portal user')
    def test_project_no_read(self):
        with self.assertRaises(AccessError, msg="%s should not be able to read the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).name

    @users('Portal user')
    def test_project_allowed_portal_no_read(self):
        self.project_pigs.privacy_visibility = 'portal'
        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        self.project_pigs.privacy_visibility = 'followers'
        with self.assertRaises(AccessError, msg="%s should not be able to read the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).name

    @users('Internal user')
    def test_project_allowed_internal_read(self):
        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        self.project_pigs.flush()
        self.project_pigs.invalidate_cache()
        self.project_pigs.with_user(self.env.user).name

    @users('Internal user', 'Portal user')
    def test_task_no_read(self):
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Portal user')
    def test_task_allowed_portal_no_read(self):
        self.project_pigs.privacy_visibility = 'portal'
        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        self.project_pigs.privacy_visibility = 'followers'
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Internal user')
    def test_task_allowed_internal_read(self):
        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        self.task.flush()
        self.task.invalidate_cache()
        self.task.with_user(self.env.user).name

    @users('Internal user', 'Portal user')
    def test_task_no_write(self):
        with self.assertRaises(AccessError, msg="%s should not be able to write on the task" % self.env.user.name):
            self.task.with_user(self.env.user).name = "Paint the world in black & white"

        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        with self.assertRaises(AccessError, msg="%s should not be able to write on the task" % self.env.user.name):
            self.task.with_user(self.env.user).name = "Paint the world in black & white"

    @users('Internal user', 'Portal user')
    def test_task_no_create(self):
        with self.assertRaises(AccessError, msg="%s should not be able to create a task" % self.env.user.name):
            self.create_task("Archive the world, it's not needed anymore")

        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        with self.assertRaises(AccessError, msg="%s should not be able to create a task" % self.env.user.name):
            self.create_task("Archive the world, it's not needed anymore")

    @users('Internal user', 'Portal user')
    def test_task_no_unlink(self):
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the task" % self.env.user.name):
            self.task.with_user(self.env.user).unlink()

        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the task" % self.env.user.name):
            self.task.with_user(self.env.user).unlink()

class TestCRUDVisibilityPortal(TestAccessRights):

    def setUp(self):
        super().setUp()
        self.project_pigs.privacy_visibility = 'portal'

    @users('Portal user')
    def test_task_portal_no_read(self):
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Portal user')
    def test_task_allowed_portal_read(self):
        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        self.task.flush()
        self.task.invalidate_cache()
        self.task.with_user(self.env.user).name

    @users('Internal user')
    def test_task_internal_read(self):
        self.task.flush()
        self.task.invalidate_cache()
        self.task.with_user(self.env.user).name

class TestCRUDVisibilityEmployees(TestAccessRights):

    def setUp(self):
        super().setUp()
        self.project_pigs.privacy_visibility = 'employees'

    @users('Portal user')
    def test_task_portal_no_read(self):
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

        self.project_pigs.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Internal user')
    def test_task_allowed_portal_read(self):
        self.task.flush()
        self.task.invalidate_cache()
        self.task.with_user(self.env.user).name

class TestAllowedUsers(TestAccessRights):

    def setUp(self):
        super().setUp()
        self.project_pigs.privacy_visibility = 'followers'

    def test_project_permission_added(self):
        self.project_pigs.message_subscribe(partner_ids=[self.user.partner_id.id])
        self.assertIn(self.user.partner_id, self.task.message_partner_ids)

    def test_project_default_permission(self):
        self.project_pigs.message_subscribe(partner_ids=[self.user.partner_id.id])
        task = self.create_task("Review the end of the world")
        self.assertIn(self.user.partner_id, self.task.message_partner_ids)

    def test_project_default_customer_permission(self):
        self.project_pigs.privacy_visibility = 'portal'
        self.project_pigs.message_subscribe(partner_ids=[self.portal.partner_id.id])
        self.assertIn(self.portal.partner_id, self.task.message_partner_ids)
        self.assertIn(self.portal.partner_id, self.project_pigs.message_partner_ids)

    def test_project_permission_removed(self):
        self.project_pigs.message_subscribe(partner_ids=[self.user.partner_id.id])
        self.project_pigs.message_unsubscribe(partner_ids=[self.user.partner_id.id])
        self.assertNotIn(self.user.partner_id, self.task.message_partner_ids)

    def test_project_specific_permission(self):
        self.project_pigs.message_subscribe(partner_ids=[self.user.partner_id.id])
        john = mail_new_test_user(self.env, 'John')
        self.project_pigs.message_subscribe(partner_ids=[john.partner_id.id])
        self.project_pigs.message_unsubscribe(partner_ids=[self.user.partner_id.id])
        self.assertIn(john.partner_id, self.task.message_partner_ids, "John should still be allowed to read the task")

    def test_project_specific_remove_mutliple_tasks(self):
        self.project_pigs.message_subscribe(partner_ids=[self.user.partner_id.id])
        john = mail_new_test_user(self.env, 'John')
        task = self.create_task('task')
        self.task.message_subscribe(partner_ids=[john.partner_id.id])
        self.project_pigs.message_unsubscribe(partner_ids=[self.user.partner_id.id])
        self.assertIn(john.partner_id, self.task.message_partner_ids)
        self.assertNotIn(john.partner_id, task.message_partner_ids)
        self.assertNotIn(self.user.partner_id, task.message_partner_ids)
        self.assertNotIn(self.user.partner_id, self.task.message_partner_ids)

    def test_visibility_changed(self):
        self.project_pigs.privacy_visibility = 'portal'
        self.task.message_subscribe(partner_ids=[self.portal.partner_id.id])
        self.assertNotIn(self.user.partner_id, self.task.message_partner_ids, "Internal user should have been removed from allowed users")
        self.project_pigs.write({'privacy_visibility': 'employees'})
        self.assertNotIn(self.portal.partner_id, self.task.message_partner_ids, "Portal user should have been removed from allowed users")

    def test_write_task(self):
        self.user.groups_id |= self.env.ref('project.group_project_user')
        self.assertNotIn(self.user.partner_id, self.project_pigs.message_partner_ids)
        self.task.message_subscribe(partner_ids=[self.user.partner_id.id])
        self.project_pigs.invalidate_cache()
        self.task.invalidate_cache()
        self.task.with_user(self.user).name = "I can edit a task!"

    def test_no_write_project(self):
        self.user.groups_id |= self.env.ref('project.group_project_user')
        self.assertNotIn(self.user.partner_id, self.project_pigs.message_partner_ids)
        with self.assertRaises(AccessError, msg="User should not be able to edit project"):
            self.project_pigs.with_user(self.user).name = "I can't edit a task!"

class TestProjectPortalCommon(TestProjectCommon):

    def setUp(self):
        super(TestProjectPortalCommon, self).setUp()
        self.user_noone = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True}).create({
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notification_type': 'email',
            'groups_id': [(6, 0, [])]})

        self.task_3 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test3', 'user_ids': self.user_portal, 'project_id': self.project_pigs.id})
        self.task_4 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test4', 'user_ids': self.user_public, 'project_id': self.project_pigs.id})
        self.task_5 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test5', 'user_ids': False, 'project_id': self.project_pigs.id})
        self.task_6 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test5', 'user_ids': False, 'project_id': self.project_pigs.id})

class TestPortalProject(TestProjectPortalCommon):

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_employee_project_access_rights(self):
        pigs = self.project_pigs

        pigs.write({'privacy_visibility': 'employees'})
        # Do: Alfred reads project -> ok (employee ok employee)
        pigs.with_user(self.user_projectuser).read(['user_id'])
        # Test: all project tasks visible
        tasks = self.env['project.task'].with_user(self.user_projectuser).search([('project_id', '=', pigs.id)])
        test_task_ids = set([self.task_1.id, self.task_2.id, self.task_3.id, self.task_4.id, self.task_5.id, self.task_6.id])
        self.assertEqual(set(tasks.ids), test_task_ids,
                         'access rights: project user cannot see all tasks of an employees project')
        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.with_user(self.user_noone).read, ['user_id'])
        # Do: Donovan reads project -> ko (public ko employee)
        self.assertRaises(AccessError, pigs.with_user(self.user_public).read, ['user_id'])
        # Do: project user is employee and can create a task
        tmp_task = self.env['project.task'].with_user(self.user_projectuser).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task',
            'project_id': pigs.id})
        tmp_task.with_user(self.user_projectuser).unlink()

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_favorite_project_access_rights(self):
        pigs = self.project_pigs.with_user(self.user_projectuser)

        # we can't write on project name
        self.assertRaises(AccessError, pigs.write, {'name': 'False Pigs'})
        # we can write on is_favorite
        pigs.write({'is_favorite': True})

    @mute_logger('odoo.addons.base.ir.ir_model')
    def test_followers_project_access_rights(self):
        pigs = self.project_pigs
        pigs.write({'privacy_visibility': 'followers'})
        pigs.flush(['privacy_visibility'])
        # Do: Alfred reads project -> ko (employee ko followers)
        self.assertRaises(AccessError, pigs.with_user(self.user_projectuser).read, ['user_id'])
        # Test: no project task visible
        tasks = self.env['project.task'].with_user(self.user_projectuser).search([('project_id', '=', pigs.id)])
        self.assertEqual(tasks, self.task_1,
                         'access rights: employee user should not see tasks of a not-followed followers project, only assigned')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.with_user(self.user_noone).read, ['user_id'])

        # Do: Donovan reads project -> ko (public ko employee)
        self.assertRaises(AccessError, pigs.with_user(self.user_public).read, ['user_id'])

        pigs.message_subscribe(partner_ids=[self.user_projectuser.partner_id.id])

        # Do: Alfred reads project -> ok (follower ok followers)
        donkey = pigs.with_user(self.user_projectuser)
        donkey.invalidate_cache()
        donkey.read(['user_id'])

        # Do: Donovan reads project -> ko (public ko follower even if follower)
        self.assertRaises(AccessError, pigs.with_user(self.user_public).read, ['user_id'])
        # Do: project user is follower of the project and can create a task
        self.env['project.task'].with_user(self.user_projectuser).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task', 'project_id': pigs.id
        })
        # not follower user should not be able to create a task
        pigs.with_user(self.user_projectuser).message_unsubscribe(partner_ids=[self.user_projectuser.partner_id.id])
        self.assertRaises(AccessError, self.env['project.task'].with_user(self.user_projectuser).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})

        # Do: project user can create a task without project
        self.assertRaises(AccessError, self.env['project.task'].with_user(self.user_projectuser).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})
