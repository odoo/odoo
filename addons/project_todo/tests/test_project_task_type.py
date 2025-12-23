import logging

from odoo.exceptions import AccessError
from odoo.addons.project.tests.test_project_task_type import TestProjectTaskTypeSecurity

_logger = logging.getLogger(__name__)


class TestProjectTodoTaskTypeSecurity(TestProjectTaskTypeSecurity):
    def _assert_access_employee(self):
        """Override: assert the access to `project.task.type` for `base.group_user`
        with the new expectations of the module `project_todo`"""

        _logger.info("Testing access for employee specific to project_todo")
        # Can read/create/write/unlink personal stage
        stage = self.env["project.task.type"].with_user(self.user_employee).create({"name": "foo"})
        stage.with_user(self.user_employee).read(["name"])
        stage.with_user(self.user_employee).write({"name": "foo"})
        stage.with_user(self.user_employee).unlink()

        # Can read a project stage
        self.stage_project.with_user(self.user_employee).read(["name"])
        # Cannot create/write/unlink project stage
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_employee).create(
                {"name": "foo", "project_ids": [self.project_goats.id]}
            )
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_employee).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_employee).unlink()

        # Cannot read/create/write/unlink other user stages
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_employee).read(["name"])
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_employee).create(
                {"name": "foo", "user_id": self.user_projectuser.id}
            )
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_employee).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_employee).unlink()

    def test_security(self):
        """Override: force this unit test to be re-executed for the module `project_todo`"""

        # Force to call `test_security` from the base class, to ensure the call of all methods `_assert_access_`
        # The goal of the class inheritance and the call to `super`
        # is to re-test the expected access for `base.group_user`, `project.group_project_user`,
        # `project.group_project_manager` despite the new ACLs and rules of this module
        super().test_security()
