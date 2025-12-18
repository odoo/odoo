# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.project.tests.test_project_base import TestProjectCommon

_logger = logging.getLogger(__name__)


class TestProjectTaskType(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.stage_created = cls.env['project.task.type'].create({
            'name': 'Stage Already Created',
            'project_ids': cls.project_goats.ids,
        })

    def test_create_stage(self):
        '''
        Verify that 'user_id' is removed when a stage is created with `project_ids` set or set by default to the curent user if not
        '''
        self.assertFalse(self.env['project.task.type'].create({
                'name': 'New Stage',
                'user_id': self.uid,
                'project_ids': [self.project_goats.id],
            }).user_id,
            "user_id should be reset if a project is set on the current stage",
        )
        self.assertEqual(self.env['project.task.type'].create({
                'name': 'Other new Stage',
            }).user_id.id,
            self.env.uid,
            "user_id should be set to the current user if no project is set at stage creation",
        )

    def test_modify_existing_stage(self):
        '''
        - case 1: [`user_id`: not set, `project_ids`: set]  | Remove `project_ids` => user_id should not be set (no transformation of project stage to personal stage)
        - case 2: [`user_id`: not set, `project_ids`: not set] | Add `user_id` and `project_ids` => user_id reset
        - case 3: [`user_id`: not set, `project_ids`: set] | Add `user_id` => UserError
        - case 4: [`user_id`: set, `project_ids`: not set]  | Add `project_ids` => user_id reset
        '''
        # case 1
        self.assertTrue(not self.stage_created.user_id and self.stage_created.project_ids)
        self.stage_created.write({'project_ids': False})
        self.assertFalse(
            self.stage_created.user_id,
            "When project_ids is reset, user_id should not be set (no transformation of project related stage to personal stage)",
        )

        # case 2
        self.assertTrue(not self.stage_created.user_id and not self.stage_created.project_ids)
        self.stage_created.write({
            'user_id': self.uid,
            'project_ids': [self.project_goats.id],
        })
        self.assertFalse(
            self.stage_created.user_id,
            "user_id should be reset if a project is set on the current stage",
        )

        # case 3
        with self.assertRaises(UserError):
            self.stage_created.write({
                'user_id': self.uid,
            })

        # case 4
        self.stage_created.write({
            'user_id': self.env.uid,
            'project_ids': False,
        })
        self.assertTrue(self.stage_created.user_id)
        self.stage_created.write({
            'project_ids': [self.project_goats.id],
        })
        self.assertFalse(
            self.stage_created.user_id,
            "user_id should be reset if a project is set on the current stage",
        )


# `at_install` on purpose, the security of `project` is tested without the ACLs and rules of `project_todo`
@tagged("at_install", "-post_install")
class TestProjectTaskTypeSecurity(TestProjectCommon):
    @classmethod
    @mute_logger("odoo.models.unlink")
    def setUpClass(cls):
        super().setUpClass()
        (cls.stage_project, cls.stage_manager, cls.stage_user, cls.stage_employee, cls.stage_portal) = cls.env[
            "project.task.type"
        ].create(
            [
                {"name": "project stage", "project_ids": [cls.project_goats.id]},
                {"name": "manager stage", "user_id": cls.user_projectmanager.id},
                {"name": "user stage", "user_id": cls.user_projectuser.id},
                {"name": "employee stage", "user_id": cls.user_employee.id},
                {"name": "portal stage", "user_id": cls.user_portal.id},
            ]
        )

    def _assert_access_portal(self):
        """Assert the access to `project.task.type` for `base.group_portal`"""

        _logger.info("Testing access for portal")
        # Can read a project stage
        self.stage_project.with_user(self.user_portal).read(["name"])

        # Can read own stage
        self.stage_portal.with_user(self.user_portal).read(["name"])

        # Cannot read another people's stage
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_portal).read(["name"])

        # Cannot create/write/unlink project stage
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_portal).create(
                {
                    "name": "foo",
                    "project_ids": [self.project_goats.id],
                }
            )
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_portal).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_portal).unlink()

        # Cannot create/write/unlink personal stages, even own
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_portal).create({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_portal.with_user(self.user_portal).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_portal.with_user(self.user_portal).unlink()

    def _assert_access_employee(self):
        """Assert the access to `project.task.type` for `base.group_user`"""

        _logger.info("Testing access for employee")
        # Can read a project stage
        self.stage_project.with_user(self.user_employee).read(["name"])

        # Can read own stage
        self.stage_employee.with_user(self.user_employee).read(["name"])

        # Cannot read another people's stage
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_employee).read(["name"])

        # Cannot create/write/unlink project stage
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_employee).create(
                {
                    "name": "foo",
                    "project_ids": [self.project_goats.id],
                }
            )
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_employee).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_employee).unlink()

        # Cannot create/write/unlink personal stages, even own
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_employee).create({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_employee.with_user(self.user_employee).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_employee.with_user(self.user_employee).unlink()

    def _assert_access_project_user(self):
        """Assert the access to `project.task.type` for `project.group_project_user`"""

        _logger.info("Testing access for project user")
        # Can read a project stage
        self.stage_project.with_user(self.user_projectuser).read(["name"])
        # but not create/write/unlink a project stage
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_projectuser).create(
                {
                    "name": "foo",
                    "project_ids": [self.project_goats.id],
                }
            )
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_projectuser).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_project.with_user(self.user_projectuser).unlink()

        # Cannot do anything on a stage from another user
        with self.assertRaises(AccessError):
            self.stage_manager.with_user(self.user_projectuser).read(["name"])
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_projectuser).create(
                {
                    "name": "foo",
                    "user_id": self.user_projectmanager.id,
                }
            )
        with self.assertRaises(AccessError):
            self.stage_manager.with_user(self.user_projectuser).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_manager.with_user(self.user_projectuser).unlink()

        # Can do everything on his own stage
        self.stage_user.with_user(self.user_projectuser).read(["name"])
        stage_user_new = (
            self.env["project.task.type"]
            .with_user(self.user_projectuser)
            .create({"name": "foo", "user_id": self.user_projectuser.id})
        )
        self.stage_user.with_user(self.user_projectuser).write({"name": "foo"})
        stage_user_new.with_user(self.user_projectuser).unlink()

    def _assert_access_project_manager(self):
        """Assert the access to `project.tags` for `project.group_project_manager`"""

        _logger.info("Testing access for project manager")
        # Can do everything on project stages
        self.stage_project.with_user(self.user_projectmanager).read(["name"])
        self.env["project.task.type"].with_user(self.user_projectmanager).create(
            {
                "name": "foo",
                "project_ids": [self.project_goats.id],
            }
        )
        self.stage_project.with_user(self.user_projectmanager).write({"name": "foo"})
        self.stage_project.with_user(self.user_projectmanager).unlink()

        # Cannot do anything on a stage from another user
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_projectmanager).read(["name"])
        with self.assertRaises(AccessError):
            self.env["project.task.type"].with_user(self.user_projectmanager).create(
                {
                    "name": "foo",
                    "user_id": self.user_projectuser.id,
                }
            )
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_projectmanager).write({"name": "foo"})
        with self.assertRaises(AccessError):
            self.stage_user.with_user(self.user_projectmanager).unlink()

        # Can do everything on his own stage
        self.stage_manager.with_user(self.user_projectmanager).read(["name"])
        self.env["project.task.type"].with_user(self.user_projectmanager).create(
            {"name": "foo", "user_id": self.user_projectmanager.id}
        )
        self.stage_manager.with_user(self.user_projectmanager).write({"name": "foo"})
        self.stage_manager.with_user(self.user_projectmanager).unlink()

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule", "odoo.models.unlink")
    def test_security(self):
        self._assert_access_portal()
        self._assert_access_employee()
        self._assert_access_project_user()
        self._assert_access_project_manager()
