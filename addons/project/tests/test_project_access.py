from odoo import Command
from odoo.exceptions import AccessError
from odoo.modules.module import get_module_path, load_script
from odoo.tests import tagged
from odoo.tools import mute_logger

from .test_project_base import TestProjectCommon


@tagged("post_install", "-at_install")
class TestProjectAccess(TestProjectCommon):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.project_goats.user_id = cls.user_projectmanager
        cls.goat_task = (
            cls.env["project.task"]
            .with_context(mail_create_nolog=True)
            .create({"name": "Goat task", "project_id": cls.project_goats.id})
        )
        cls.shared = cls.env["project.project"].create(
            {
                "name": "Shared",
                "privacy_visibility": "invited_users",
                "workflow_step_ids": [
                    Command.create({"name": "Todo", "sequence": 1}),
                    Command.create({"name": "Done", "sequence": 2}),
                ],
            }
        )
        cls.todo, cls.done = cls.shared.workflow_step_ids.sorted("sequence")
        cls.shared_task = (
            cls.env["project.task"]
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Shared task",
                    "project_id": cls.shared.id,
                    "step_id": cls.todo.id,
                    "priority": "0",
                }
            )
        )

    def _readable(self, user, records):
        return records.with_user(user).search([("id", "in", records.ids)])

    def _share(self, access_mode):
        self.shared.collaborator_ids = [
            Command.create(
                {
                    "partner_id": self.user_portal.partner_id.id,
                    "access_mode": access_mode,
                }
            )
        ]
        return self.shared.collaborator_ids

    def test_following_a_private_project_grants_nothing(self):
        self.project_goats.message_subscribe(self.user_projectuser.partner_id.ids)

        self.assertFalse(self._readable(self.user_projectuser, self.project_goats))
        self.assertFalse(self._readable(self.user_projectuser, self.goat_task))

    def test_team_members_and_the_manager_reach_a_private_project(self):
        self.assertTrue(self._readable(self.user_projectmanager, self.project_goats))

        self.project_goats.member_user_ids = self.user_projectuser

        self.assertTrue(self._readable(self.user_projectuser, self.project_goats))
        self.assertTrue(self._readable(self.user_projectuser, self.goat_task))
        self.assertTrue(
            self.project_goats.with_user(self.user_projectuser).user_has_access
        )

    def test_a_followed_task_stays_readable_without_project_access(self):
        self.goat_task.message_subscribe(self.user_projectuser.partner_id.ids)

        self.assertTrue(self._readable(self.user_projectuser, self.goat_task))
        self.assertFalse(self._readable(self.user_projectuser, self.project_goats))

    def test_project_scoped_records_follow_project_access(self):
        milestone = self.env["project.milestone"].create(
            {"name": "Goal", "project_id": self.project_goats.id}
        )
        self.project_goats.message_subscribe(self.user_projectuser.partner_id.ids)
        self.assertFalse(self._readable(self.user_projectuser, milestone))

        self.project_goats.member_user_ids = self.user_projectuser

        self.assertTrue(self._readable(self.user_projectuser, milestone))

    def test_a_portal_follower_is_not_a_collaborator(self):
        self.shared.message_subscribe(self.user_portal.partner_id.ids)

        self.assertFalse(self._readable(self.user_portal, self.shared))
        self.assertFalse(self._readable(self.user_portal, self.shared_task))

    def test_a_view_collaborator_reads_everything_and_edits_nothing(self):
        self._share("view")

        self.assertTrue(self._readable(self.user_portal, self.shared))
        self.assertTrue(self._readable(self.user_portal, self.shared_task))
        with self.assertRaises(AccessError), mute_logger("odoo.addons.base.models"):
            self.shared_task.with_user(self.user_portal).write({"name": "Renamed"})

    @mute_logger("odoo.addons.base.models")
    def test_an_edit_collaborator_edits_and_creates_but_does_not_move(self):
        self._share("edit")
        task = self.shared_task.with_user(self.user_portal)

        task.write({"name": "Renamed"})
        self.assertEqual(self.shared_task.name, "Renamed")
        task.write({"step_id": self.todo.id, "priority": "0"})
        with self.assertRaises(AccessError):
            task.write({"step_id": self.done.id})
        with self.assertRaises(AccessError):
            task.write({"priority": "1"})

        created = (
            self.env["project.task"]
            .with_user(self.user_portal)
            .with_context(
                default_project_id=self.shared.id, default_step_id=self.done.id
            )
            .create({"name": "Placed in a column"})
        )
        self.assertEqual(created.step_id, self.done)

    def test_an_advanced_edit_collaborator_moves_tasks(self):
        self._share("advanced_edit")

        self.shared_task.with_user(self.user_portal).write(
            {"step_id": self.done.id, "priority": "1"}
        )

        self.assertEqual(self.shared_task.step_id, self.done)
        self.assertEqual(self.shared_task.priority, "1")

    def test_unfollowing_does_not_revoke_a_collaborator(self):
        self._share("edit")
        self.shared.message_subscribe(self.user_portal.partner_id.ids)

        self.shared.message_unsubscribe(self.user_portal.partner_id.ids)

        self.assertTrue(self.shared.collaborator_ids)
        self.assertTrue(self._readable(self.user_portal, self.shared_task))

    def test_removing_a_collaborator_revokes_task_access_too(self):
        collaborator = self._share("edit")
        self.shared_task.with_user(
            self.user_portal
        ).project_sharing_toggle_is_follower()
        self.assertIn(self.user_portal.partner_id, self.shared_task.message_partner_ids)

        collaborator.unlink()

        self.assertNotIn(
            self.user_portal.partner_id, self.shared_task.message_partner_ids
        )
        self.assertFalse(self._readable(self.user_portal, self.shared_task))
        self.assertFalse(self._readable(self.user_portal, self.shared))

    def test_opening_visibility_invites_the_customer_and_closing_keeps_collaborators(
        self,
    ):
        self.project_goats.privacy_visibility = "portal"
        customer = self.project_goats.collaborator_ids
        self.assertEqual(customer.partner_id, self.partner_1)
        self.assertEqual(customer.access_mode, "view")

        self.project_goats.privacy_visibility = "employees"
        self.assertEqual(self.project_goats.collaborator_ids, customer)
        self.assertFalse(self.project_goats.with_user(self.user_portal).user_has_access)

    def test_changing_customer_and_visibility_together_invites_the_new_customer(self):
        self.project_goats.write(
            {"partner_id": self.partner_2.id, "privacy_visibility": "portal"}
        )

        self.assertEqual(self.project_goats.collaborator_ids.partner_id, self.partner_2)


@tagged("post_install", "-at_install")
class TestProjectAccessMigration(TestProjectCommon):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.script = load_script(
            f"{get_module_path('project')}/migrations/1.25/post-migrate.py",
            "project_1_25_post_migrate",
        )

    def test_followers_become_collaborators_and_team_members(self):
        shared = self.env["project.project"].create(
            {"name": "Shared before", "privacy_visibility": "portal"}
        )
        shared.message_subscribe(
            (self.user_portal.partner_id | self.user_projectuser.partner_id).ids
        )
        self.project_goats.message_subscribe(self.user_projectuser.partner_id.ids)
        self.env.flush_all()

        self.script.migrate(self.env.cr, "19.0.1.24")
        self.env.invalidate_all()

        self.assertEqual(
            shared.collaborator_ids.partner_id, self.user_portal.partner_id
        )
        self.assertEqual(shared.collaborator_ids.access_mode, "view")
        self.assertIn(self.user_projectuser, shared.member_user_ids)
        self.assertIn(self.user_projectuser, self.project_goats.member_user_ids)
        self.assertFalse(self.project_goats.collaborator_ids)
        self.assertTrue(
            self.env.ref("project.project_task_rule_portal_project_sharing").active
        )

    def test_follower_based_rules_are_reloaded_and_stay_noupdate(self):
        rule = self.env.ref("project.project_public_members_rule")
        rule.domain_force = "[('message_partner_ids', 'in', [user.partner_id.id])]"
        self.env.flush_all()

        self.script.migrate(self.env.cr, "19.0.1.24")
        self.env.invalidate_all()

        self.assertIn("user_has_access", rule.domain_force)
        self.assertTrue(
            self.env["ir.model.data"]
            .search(
                [
                    ("module", "=", "project"),
                    ("name", "=", "project_public_members_rule"),
                ]
            )
            .noupdate
        )

    def test_fresh_install_is_noop(self):
        shared = self.env["project.project"].create(
            {"name": "Fresh", "privacy_visibility": "portal"}
        )
        shared.message_subscribe(self.user_portal.partner_id.ids)
        self.env.flush_all()

        self.script.migrate(self.env.cr, None)
        self.env.invalidate_all()

        self.assertFalse(shared.collaborator_ids)
