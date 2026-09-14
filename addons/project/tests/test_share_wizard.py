import logging

from odoo import Command
from odoo.tests import tagged

from .test_project_base import TestProjectCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestShareWizardAppliesOnConfirm(TestProjectCommon):
    def test_partial_defaults_preserve_the_requested_field_contract(self):
        project = self.env["project.project"].create({"name": "Default target"})
        project._add_collaborators(self.user_portal.partner_id, access_mode="edit")
        model = self.env["project.share.wizard"].with_context(
            active_model=project._name,
            active_id=project.id,
        )
        defaults = model.default_get(["note"])
        _logger.debug("Project share note defaults: %s", defaults)
        self.assertLessEqual(defaults.keys(), {"note"})
        defaults = model.default_get(["collaborator_ids"])
        _logger.debug("Project share collaborator defaults: %s", defaults)
        self.assertEqual(defaults.keys(), {"collaborator_ids"})
        self.assertIn(
            self.user_portal.partner_id.id,
            [command[2]["partner_id"] for command in defaults["collaborator_ids"]],
        )

    def test_explicit_collaborator_defaults_are_preserved(self):
        project = self.env["project.project"].create({"name": "Explicit defaults"})
        project._add_collaborators(self.user_portal.partner_id, access_mode="edit")
        defaults = (
            self.env["project.share.wizard"]
            .with_context(
                active_model=project._name,
                active_id=project.id,
                default_collaborator_ids=[],
            )
            .default_get(["collaborator_ids"])
        )
        _logger.debug("Explicit project share collaborator defaults: %s", defaults)
        self.assertEqual(defaults.keys(), {"collaborator_ids"})
        wizard = self.env["project.share.wizard"].create(
            {
                "res_model": project._name,
                "res_id": project.id,
                **defaults,
            }
        )
        self.assertFalse(wizard.collaborator_ids)

    def _wizard(self, project, partner, access_mode="edit"):
        return self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": project.id,
                "collaborator_ids": [
                    Command.create(
                        {"partner_id": partner.id, "access_mode": access_mode}
                    )
                ],
            }
        )

    def test_saving_the_dialog_grants_nothing(self) -> None:
        project = self.env["project.project"].create(
            {"name": "Shared", "privacy_visibility": "portal"}
        )
        self._wizard(project, self.user_portal.partner_id)
        self.assertFalse(project.collaborator_ids)

    def test_sharing_grants_access(self) -> None:
        project = self.env["project.project"].create(
            {"name": "Shared", "privacy_visibility": "portal"}
        )
        self._wizard(project, self.user_portal.partner_id).action_send_mail()
        self.assertEqual(
            project.collaborator_ids.partner_id, self.user_portal.partner_id
        )

    def test_emptying_the_list_still_revokes(self) -> None:
        project = self.env["project.project"].create(
            {"name": "Shared", "privacy_visibility": "portal"}
        )
        self._wizard(project, self.user_portal.partner_id).action_send_mail()
        self.assertTrue(project.collaborator_ids)

        revoke = self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": project.id,
                "collaborator_ids": [],
            }
        )
        revoke.action_share_record()
        self.assertFalse(project.collaborator_ids)

    def test_invitations_leave_one_credential_free_note(self) -> None:
        project = self.env["project.project"].create(
            {"name": "Shared", "privacy_visibility": "portal"}
        )
        reader = self.env["res.partner"].create(
            {"name": "Read-only guest", "email": "guest@example.com"}
        )
        wizard = self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": project.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "edit",
                        }
                    ),
                    Command.create({"partner_id": reader.id, "access_mode": "view"}),
                ],
            }
        )
        wizard.action_send_mail()

        readable = (
            self.env["mail.message"]
            .with_user(self.user_projectuser)
            .search([("model", "=", project._name), ("res_id", "=", project.id)])
        )
        for message in readable:
            self.assertNotIn("token=", str(message.body))
            self.assertNotIn("hash=", str(message.body))
        notes = readable.filtered(
            lambda message: (
                reader.name in str(message.body)
                and self.user_portal.partner_id.name in str(message.body)
            )
        )
        self.assertEqual(len(notes), 1)
        invitations = self.env["mail.message"].search(
            [
                ("model", "=", project._name),
                ("res_id", "=", project.id),
                ("message_type", "=", "user_notification"),
            ]
        )
        self.assertEqual(invitations.partner_ids, self.user_portal.partner_id | reader)

    def test_applying_twice_is_a_no_op(self) -> None:
        project = self.env["project.project"].create(
            {"name": "Shared", "privacy_visibility": "portal"}
        )
        wizard = self._wizard(project, self.user_portal.partner_id)
        wizard.action_send_mail()
        wizard.action_send_mail()
        self.assertEqual(len(project.collaborator_ids), 1)


@tagged("post_install", "-at_install")
class TestCollaboratorRulesLetAManagerShare(TestProjectCommon):
    def test_a_manager_can_share_a_project_they_neither_follow_nor_own(self) -> None:
        # project.collaborator carries the comp / visibility / manager triad that
        # project.risk and project.gate carry. The manager member is what makes
        # the pair work: an ir.rule with no perm_* fields governs create as well
        # as read, group_project_manager implies group_project_user, and rules of
        # different groups OR together -- so without an unrestricted manager rule
        # the read-scoping visibility rule also blocks a manager from CREATING a
        # collaborator on a project they do not follow. That is every project the
        # setUpClass of an HttpCase builds, which is how it reached the sharing
        # tours rather than a unit test.
        project = (
            self.env["project.project"]
            .with_user(self.env.ref("base.user_root"))
            .create({"name": "Owned by nobody", "privacy_visibility": "portal"})
        )
        project.message_unsubscribe(partner_ids=project.message_partner_ids.ids)
        manager = self.user_projectmanager
        self.assertNotIn(manager.partner_id, project.message_partner_ids)
        self.assertNotEqual(project.user_id, manager)

        project.with_user(manager).write(
            {
                "collaborator_ids": [
                    Command.create({"partner_id": self.user_portal.partner_id.id})
                ]
            }
        )
        self.assertEqual(
            project.collaborator_ids.partner_id, self.user_portal.partner_id
        )
