import logging

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.project.tests.test_project_base import TestProjectCommon

_logger = logging.getLogger(__name__)


# `at_install` on purpose, the security of `project` is tested without the ACLs and rules of `project_todo`
@tagged("at_install", "-post_install")
class TestProjectTagsSecurity(TestProjectCommon):
    @classmethod
    @mute_logger("odoo.models.unlink")
    def setUpClass(cls):
        super().setUpClass()
        cls.tag_project, cls.tag_admin = cls.env["project.tags"].create(
            [
                {"name": "project tag", "project_ids": [cls.project_goats.id]},
                {"name": "admin tag"},
            ]
        )

    def _assert_access_portal(self):
        """Assert the access to `project.tags` for `base.group_portal`"""

        _logger.info("Testing access for portal")
        # Can read any tag
        (self.tag_project | self.tag_admin).with_user(self.user_portal).read(["name"])

        # Cannot create/write/unlink tags
        with self.assertRaises(AccessError):
            self.env["project.tags"].with_user(self.user_portal).create({"name": "Foo"})
        # Force create a tag with as create_uid `self.user_portal`
        tag = self.env["project.tags"].with_user(self.user_portal).sudo().create({"name": "Portal tag"}).sudo(False)
        with self.assertRaises(AccessError):
            tag.with_user(self.user_portal).write({"name": "Foo"})
        with self.assertRaises(AccessError):
            tag.with_user(self.user_portal).unlink()

    def _assert_access_employee(self):
        """Assert the access to `project.tags` for `base.group_user`"""

        _logger.info("Testing access for employee")
        # Can read any tag
        (self.tag_project | self.tag_admin).with_user(self.user_employee).read(["name"])

        # Cannot create/write/unlink tags
        with self.assertRaises(AccessError):
            self.env["project.tags"].with_user(self.user_employee).create({"name": "Foo"})
        # Force create a tag with as create_uid `self.user_employee`
        tag = self.env["project.tags"].with_user(self.user_employee).sudo().create({"name": "Employee tag"}).sudo(False)
        with self.assertRaises(AccessError):
            tag.with_user(self.user_employee).write({"name": "Foo"})
        with self.assertRaises(AccessError):
            tag.with_user(self.user_employee).unlink()

    def _assert_access_project_user(self):
        """Assert the access to `project.tags` for `project.group_project_user`"""

        _logger.info("Testing access for project user")
        # Can read any tag
        (self.tag_project | self.tag_admin).with_user(self.user_projectuser).read(["name"])

        # Cannot create/write/unlink tags
        with self.assertRaises(AccessError):
            self.env["project.tags"].with_user(self.user_projectuser).create({"name": "Foo"})
        # Force create a tag with as create_uid `self.user_employee`
        tag = (
            self.env["project.tags"]
            .with_user(self.user_projectuser)
            .sudo()
            .create({"name": "Project user tag"})
            .sudo(False)
        )
        with self.assertRaises(AccessError):
            tag.with_user(self.user_projectuser).write({"name": "Foo"})
        with self.assertRaises(AccessError):
            tag.with_user(self.user_projectuser).unlink()

    def _assert_access_project_manager(self):
        """Assert the access to `project.tags` for `project.group_project_manager`"""

        _logger.info("Testing access for project manager")
        # Can read any tag
        (self.tag_project | self.tag_admin).with_user(self.user_projectmanager).read(["name"])

        # Can create/write/unlink tags, whether associated to projects or not
        self.env["project.tags"].with_user(self.user_projectmanager).create(
            [
                {"name": "Manager tag"},
                {"name": "Project tag", "project_ids": [self.project_goats.id]},
            ]
        )
        (self.tag_project | self.tag_admin).with_user(self.user_projectmanager).write({"color": 1})
        (self.tag_project | self.tag_admin).with_user(self.user_projectmanager).unlink()

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule", "odoo.models.unlink")
    def test_security(self):
        """Tests the access to `project.tags` for the different user groups"""

        self._assert_access_portal()
        self._assert_access_employee()
        self._assert_access_project_user()
        self._assert_access_project_manager()
