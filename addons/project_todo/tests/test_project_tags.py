import logging

from odoo.exceptions import AccessError

from odoo.addons.project.tests.test_project_tags import TestProjectTagsSecurity

_logger = logging.getLogger(__name__)


class TestProjectTodoTagsSecurity(TestProjectTagsSecurity):
    def _assert_access_common_employee_project_user(self, user):
        """Assert the access to `project.tags` for `base.group_user` and `project.group_project_user`
        which become common with this module"""

        # Can read any tag
        (self.tag_project | self.tag_admin).with_user(user).read(["name"])

        # Can create/write/unlink own tags
        tag = self.env["project.tags"].with_user(user).create({"name": "Employee tag"})
        tag.with_user(user).write({"name": "Foo"})
        tag.with_user(user).unlink()

        # Cannot create/write/unlink tags associated to projects
        with self.assertRaises(AccessError):
            tag = (
                self.env["project.tags"]
                .with_user(user)
                .create(
                    {
                        "name": "Project tag",
                        "project_ids": [self.project_goats.id],
                    }
                )
            )
        with self.assertRaises(AccessError):
            self.tag_project.with_user(user).write({"name": "Foo"})
        with self.assertRaises(AccessError):
            self.tag_project.with_user(user).unlink()

        # Cannot create/write/unlink tags not their own
        with self.assertRaises(AccessError):
            self.tag_admin.with_user(user).write({"name": "Foo"})
        with self.assertRaises(AccessError):
            self.tag_admin.with_user(user).unlink()

    def _assert_access_employee(self):
        """Override: assert the access to `project.tags` for `base.group_user`
        with the new expectations of the module `project_todo`"""

        _logger.info("Testing access for employee specific to project_todo")
        self._assert_access_common_employee_project_user(self.user_employee)

    def _assert_access_project_user(self):
        """Override: assert the access to `project.tags` for `project.group_project_user`
        with the new expectations of the module `project_todo`"""

        _logger.info("Testing access for project user specific to project_todo")
        self._assert_access_common_employee_project_user(self.user_projectuser)

    def test_security(self):
        """Override: force this unit test to be re-executed for the module `project_todo`"""

        # Force to call `test_security` from the base class, to ensure the call of all methods `_assert_access_`
        # The goal of the class inheritance and the call to `super`
        # is to re-test the expected access for `project.group_project_user` and `project.group_project_manager`
        # despite the new ACLs and rules of this module
        super().test_security()
