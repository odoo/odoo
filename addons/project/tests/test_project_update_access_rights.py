# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import users

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.project.tests.test_project_base import TestProjectCommon

@tagged('-at_install', 'post_install')
class TestProjectUpdateAccessRights(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super(TestProjectUpdateAccessRights, cls).setUpClass()
        cls.project_update_1 = cls.env['project.update'].create({
            'name': "Test Project Update",
            'project_id': cls.project_pigs.id,
            'status': 'on_track',
        })
        cls.project_milestone = cls.env['project.milestone'].create({
            'name': 'Test Projec Milestone',
            'project_id': cls.project_pigs.id,
        })
        cls.base_user = mail_new_test_user(cls.env, 'Base user', groups='base.group_user')
        cls.project_user = mail_new_test_user(cls.env, 'Project user', groups='project.group_project_user')
        cls.project_manager = mail_new_test_user(cls.env, 'Project admin', groups='project.group_project_manager')
        cls.portal_user = mail_new_test_user(cls.env, 'Portal user', groups='base.group_portal')

    @users('Project user', 'Project admin', 'Base user')
    def test_project_update_user_can_read(self):
        self.project_update_1.with_user(self.env.user).name

    @users('Base user')
    def test_project_update_user_no_write(self):
        with self.assertRaises(AccessError, msg="%s should not be able to write in the project update" % self.env.user.name):
            self.project_update_1.with_user(self.env.user).name = "Test write"

    @users('Project admin')
    def test_project_update_admin_can_write(self):
        self.project_update_1.with_user(self.env.user).name = "Test write"

    @users('Base user')
    def test_project_update_user_no_unlink(self):
        with self.assertRaises(AccessError, msg="%s should not be able to unlink in the project update" % self.env.user.name):
            self.project_update_1.with_user(self.env.user).unlink()

    @users('Project admin')
    def test_project_update_admin_unlink(self):
        self.project_update_1.with_user(self.env.user).unlink()

    @users('Portal user')
    def test_project_update_portal_user_no_read(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to read in the project update"):
            self.project_update_1.with_user(self.env.user).name

    @users('Portal user')
    def test_project_update_portal_user_no_write(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to write in the project update"):
            self.project_update_1.with_user(self.env.user).name = 'Test write'

    @users('Portal user')
    def test_project_update_portal_user_no_create(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to create in the project update model"):
            self.env['project.update'].with_user(self.env.user).create({
                'name': 'Test Create with portal user',
                'project_id': self.project_pigs.id,
                'state': 'on_track',
            })

    @users('Portal user')
    def test_project_update_portal_user_no_unlink(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to unlink in the project update"):
            self.project_update_1.with_user(self.env.user).unlink()

    @users('Portal user')
    def test_project_milestone_portal_user_no_read(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to read in the project update"):
            self.project_milestone.with_user(self.env.user).name

    @users('Portal user')
    def test_project_milestone_portal_user_no_write(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to write in the project update"):
            self.project_milestone.with_user(self.env.user).name = 'Test write'

    @users('Portal user')
    def test_project_milestone_portal_user_no_create(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to create in the project update model"):
            self.env['project.update'].with_user(self.env.user).create({
                'name': 'Test Create with portal user',
                'project_id': self.project_pigs.id,
            })

    @users('Portal user')
    def test_project_milestone_portal_user_no_unlink(self):
        with self.assertRaises(AccessError, msg=f"{self.env.user.name} should not be able to unlink in the project update"):
            self.project_milestone.with_user(self.env.user).unlink()
