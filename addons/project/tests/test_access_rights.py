# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import users


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

        self.project_pigs.allowed_user_ids = self.env.user
        with self.assertRaises(AccessError, msg="%s should not be able to write on the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).name = "Take over the world"

    @users('Internal user', 'Portal user')
    def test_project_no_unlink(self):
        self.project_pigs.task_ids.unlink()
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).unlink()

        self.project_pigs.allowed_user_ids = self.env.user
        self.project_pigs.task_ids.unlink()
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).unlink()

    @users('Internal user', 'Portal user')
    def test_project_no_read(self):
        self.project_pigs.invalidate_cache()
        with self.assertRaises(AccessError, msg="%s should not be able to read the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).name

    @users('Portal user')
    def test_project_allowed_portal_no_read(self):
        self.project_pigs.allowed_user_ids = self.env.user
        self.project_pigs.invalidate_cache()
        with self.assertRaises(AccessError, msg="%s should not be able to read the project" % self.env.user.name):
            self.project_pigs.with_user(self.env.user).name

    @users('Internal user')
    def test_project_allowed_internal_read(self):
        self.project_pigs.allowed_user_ids = self.env.user
        self.project_pigs.invalidate_cache()
        self.project_pigs.with_user(self.env.user).name

    @users('Internal user', 'Portal user')
    def test_task_no_read(self):
        self.task.invalidate_cache()
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Portal user')
    def test_task_allowed_portal_no_read(self):
        self.project_pigs.allowed_user_ids = self.env.user
        self.task.invalidate_cache()
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Internal user')
    def test_task_allowed_internal_read(self):
        self.project_pigs.allowed_user_ids = self.env.user
        self.task.invalidate_cache()
        self.task.with_user(self.env.user).name

    @users('Internal user', 'Portal user')
    def test_task_no_write(self):
        with self.assertRaises(AccessError, msg="%s should not be able to write on the task" % self.env.user.name):
            self.task.with_user(self.env.user).name = "Paint the world in black & white"

        self.project_pigs.allowed_user_ids = self.env.user
        with self.assertRaises(AccessError, msg="%s should not be able to write on the task" % self.env.user.name):
            self.task.with_user(self.env.user).name = "Paint the world in black & white"

    @users('Internal user', 'Portal user')
    def test_task_no_create(self):
        with self.assertRaises(AccessError, msg="%s should not be able to create a task" % self.env.user.name):
            self.create_task("Archive the world, it's not needed anymore")

        self.project_pigs.allowed_user_ids = self.env.user
        with self.assertRaises(AccessError, msg="%s should not be able to create a task" % self.env.user.name):
            self.create_task("Archive the world, it's not needed anymore")

    @users('Internal user', 'Portal user')
    def test_task_no_unlink(self):
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the task" % self.env.user.name):
            self.task.with_user(self.env.user).unlink()

        self.project_pigs.allowed_user_ids = self.env.user
        with self.assertRaises(AccessError, msg="%s should not be able to unlink the task" % self.env.user.name):
            self.task.with_user(self.env.user).unlink()


class TestCRUDVisibilityPortal(TestAccessRights):

    def setUp(self):
        super().setUp()
        self.project_pigs.privacy_visibility = 'portal'

    @users('Portal user')
    def test_task_portal_no_read(self):
        self.task.invalidate_cache()
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Portal user')
    def test_task_allowed_portal_read(self):
        self.project_pigs.allowed_user_ids = self.env.user
        self.task.invalidate_cache()
        self.task.with_user(self.env.user).name

    @users('Internal user')
    def test_task_internal_read(self):
        self.task.with_user(self.env.user).name


class TestCRUDVisibilityEmployees(TestAccessRights):

    def setUp(self):
        super().setUp()
        self.project_pigs.privacy_visibility = 'employees'

    @users('Portal user')
    def test_task_portal_no_read(self):
        self.task.invalidate_cache()
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

        self.project_pigs.allowed_user_ids = self.env.user
        self.task.invalidate_cache()
        with self.assertRaises(AccessError, msg="%s should not be able to read the task" % self.env.user.name):
            self.task.with_user(self.env.user).name

    @users('Internal user')
    def test_task_allowed_portal_read(self):
        self.task.invalidate_cache()
        self.task.with_user(self.env.user).name


class TestAllowedUsers(TestAccessRights):

    def setUp(self):
        super().setUp()
        self.project_pigs.privacy_visibility = 'followers'

    def test_project_permission_added(self):
        self.project_pigs.allowed_user_ids = self.user
        self.assertIn(self.user, self.task.allowed_user_ids)

    def test_project_default_permission(self):
        self.project_pigs.allowed_user_ids = self.user
        task = self.create_task("Review the end of the world")
        self.assertIn(self.user, task.allowed_user_ids)

    def test_project_default_customer_permission(self):
        self.project_pigs.privacy_visibility = 'portal'
        self.project_pigs.partner_id = self.portal.partner_id
        self.assertIn(self.portal, self.task.allowed_user_ids)
        self.assertIn(self.portal, self.project_pigs.allowed_user_ids)

    def test_project_permission_removed(self):
        self.project_pigs.allowed_user_ids = self.user
        self.project_pigs.allowed_user_ids -= self.user
        self.assertNotIn(self.user, self.task.allowed_user_ids)

    def test_project_specific_permission(self):
        self.project_pigs.allowed_user_ids = self.user
        john = mail_new_test_user(self.env, login='John')
        self.task.allowed_user_ids |= john
        self.project_pigs.allowed_user_ids -= self.user
        self.assertIn(john, self.task.allowed_user_ids, "John should still be allowed to read the task")

    def test_project_specific_remove_mutliple_tasks(self):
        self.project_pigs.allowed_user_ids = self.user
        john = mail_new_test_user(self.env, login='John')
        task = self.create_task('task')
        self.task.allowed_user_ids |= john
        self.project_pigs.allowed_user_ids -= self.user
        self.assertIn(john, self.task.allowed_user_ids)
        self.assertNotIn(john, task.allowed_user_ids)
        self.assertNotIn(self.user, task.allowed_user_ids)
        self.assertNotIn(self.user, self.task.allowed_user_ids)

    def test_no_portal_allowed(self):
        with self.assertRaises(ValidationError, msg="It should not allow to add portal users"):
            self.task.allowed_user_ids = self.portal

    def test_visibility_changed(self):
        self.project_pigs.privacy_visibility = 'portal'
        self.task.allowed_user_ids |= self.portal
        self.assertNotIn(self.user, self.task.allowed_user_ids, "Internal user should have been removed from allowed users")
        self.project_pigs.privacy_visibility = 'employees'
        self.assertNotIn(self.portal, self.task.allowed_user_ids, "Portal user should have been removed from allowed users")

    def test_write_task(self):
        self.user.groups_id |= self.env.ref('project.group_project_user')
        self.assertNotIn(self.user, self.project_pigs.allowed_user_ids)
        self.task.allowed_user_ids = self.user
        self.project_pigs.invalidate_cache()
        self.task.invalidate_cache()
        self.task.with_user(self.user).name = "I can edit a task!"

    def test_no_write_project(self):
        self.user.groups_id |= self.env.ref('project.group_project_user')
        self.assertNotIn(self.user, self.project_pigs.allowed_user_ids)
        with self.assertRaises(AccessError, msg="User should not be able to edit project"):
            self.project_pigs.with_user(self.user).name = "I can't edit a task!"
