from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged, users
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user

MAIL = """Return-Path: {return_path}
To: {to}
cc: {cc}
From: {email_from}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Date: {date}
Message-ID: {msg_id}
{extra}

Something is broken.
"""


@tagged("post_install", "-at_install")
class TestTeamUsage(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Team = cls.env["team.team"]
        Team.search([]).action_archive()
        cls.env["ir.config_parameter"].set_param(
            "test_team.alpha_membership_multi", False
        )
        cls.env["ir.config_parameter"].set_param(
            "test_team.beta_membership_multi", False
        )
        cls.user_alpha_manager = mail_new_test_user(
            cls.env,
            login="alpha_manager",
            groups="base.group_user,test_team.group_alpha_manager",
        )
        cls.user_beta_manager = mail_new_test_user(
            cls.env,
            login="beta_manager",
            groups="base.group_user,test_team.group_beta_manager",
        )
        cls.user_member = mail_new_test_user(
            cls.env, login="member", groups="base.group_user"
        )
        cls.team_alpha_1 = Team.create({"name": "Alpha 1", "use_alpha": True})
        cls.team_alpha_2 = Team.create({"name": "Alpha 2", "use_alpha": True})
        cls.team_beta = Team.create({"name": "Beta", "use_beta": True})
        cls.team_both = Team.create(
            {"name": "Both", "use_alpha": True, "use_beta": True}
        )

    def _join(self, team, user=None):
        return self.env["team.member"].create(
            {"team_id": team.id, "user_id": (user or self.user_member).id}
        )

    def test_joining_a_team_evicts_from_teams_sharing_a_mono_usage_only(self):
        in_alpha = self._join(self.team_alpha_1)
        in_beta = self._join(self.team_beta)

        self._join(self.team_alpha_2)

        self.assertFalse(in_alpha.active)
        self.assertTrue(
            in_beta.active,
            "Beta shares no usage with Alpha 2, so the membership is not competing",
        )

    def test_a_team_with_two_usages_evicts_from_both(self):
        in_alpha = self._join(self.team_alpha_1)
        in_beta = self._join(self.team_beta)

        self._join(self.team_both)

        self.assertFalse(in_alpha.active)
        self.assertFalse(in_beta.active)

    def test_a_multi_usage_keeps_memberships_while_a_mono_one_still_evicts(self):
        self.env["ir.config_parameter"].set_param(
            "test_team.alpha_membership_multi", True
        )
        in_alpha = self._join(self.team_alpha_1)
        in_beta = self._join(self.team_beta)

        self._join(self.team_both)

        self.assertTrue(in_alpha.active)
        self.assertFalse(in_beta.active)
        self.assertFalse(self.team_both.is_membership_multi)
        self.assertTrue(self.team_alpha_1.is_membership_multi)

    def test_the_member_warning_names_only_teams_sharing_a_mono_usage(self):
        self._join(self.team_alpha_1)
        self._join(self.team_beta)

        draft = self.env["team.member"].new(
            {"team_id": self.team_alpha_2.id, "user_id": self.user_member.id}
        )

        self.assertIn("Alpha 1", draft.member_warning)
        self.assertNotIn("Beta", draft.member_warning)

    def test_activating_multi_membership_takes_every_usage_administrator(self):
        with self.assertRaises(AccessError):
            self.team_both.with_user(
                self.user_alpha_manager
            ).action_activate_multi_membership()
        self.assertFalse(
            self.team_both.with_user(
                self.user_alpha_manager
            ).can_activate_multi_membership
        )

        self.team_alpha_1.with_user(
            self.user_alpha_manager
        ).action_activate_multi_membership()

        self.assertTrue(self.env["team.team"]._is_membership_multi("alpha"))
        self.assertFalse(self.env["team.team"]._is_membership_multi("beta"))

    def test_an_unsaved_team_activates_the_usages_its_flags_name(self):
        self.env["team.team"].with_user(
            self.user_beta_manager
        ).action_activate_multi_membership(flags={"use_beta": True})

        self.assertTrue(self.env["team.team"]._is_membership_multi("beta"))
        self.assertFalse(self.env["team.team"]._is_membership_multi("alpha"))

    def test_a_usage_receiving_mail_gets_one_alias_per_team(self):
        alias = self.team_alpha_1.alias_ids

        self.assertEqual(alias.usage, "alpha")
        self.assertEqual(alias.alias_model_id.model, "test.team.ticket")
        self.assertEqual(alias.alias_parent_model_id.model, "team.team")
        self.assertEqual(alias.alias_parent_thread_id, self.team_alpha_1.id)
        self.assertEqual(
            alias.alias_id._get_alias_defaults(),
            {"team_id": self.team_alpha_1.id, "kind": "incoming"},
        )
        self.assertFalse(self.team_beta.alias_ids)
        self.assertEqual(self.team_both.alias_ids.mapped("usage"), ["alpha"])

    def test_removing_the_usage_removes_its_alias(self):
        mail_alias = self.team_alpha_1.alias_ids.alias_id

        self.team_alpha_1.use_alpha = False

        self.assertFalse(self.team_alpha_1.alias_ids)
        self.assertFalse(mail_alias.exists())

    def test_a_second_alias_for_the_same_usage_is_refused(self):
        with self.assertRaises(Exception), mute_logger("odoo.db.cursor"):
            self.env["team.alias"].create(
                {"team_id": self.team_alpha_1.id, "usage": "alpha"}
            )
            self.env.flush_all()

    def test_an_alias_for_a_usage_without_mail_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["team.alias"].create(
                {"team_id": self.team_beta.id, "usage": "beta"}
            )

    @mute_logger("odoo.addons.mail.models.mixin_mail_thread")
    def test_mail_to_a_usage_alias_creates_its_document_in_the_team(self):
        self.team_alpha_1.alias_ids.alias_name = "alpha-one"

        ticket = self.format_and_process(
            MAIL,
            self.user_member.email_formatted,
            f"alpha-one@{self.alias_domain}",
            subject="Printer down",
            target_model="test.team.ticket",
        )

        self.assertEqual(ticket.team_id, self.team_alpha_1)
        self.assertEqual(ticket.kind, "incoming")

    def test_the_default_team_is_resolved_within_the_usage(self):
        self._join(self.team_beta)
        self._join(self.team_alpha_2)

        self.assertEqual(
            self.env["team.team"]._get_default_team(
                "alpha", user_id=self.user_member.id
            ),
            self.team_alpha_2,
        )

    def test_a_context_team_of_another_usage_is_ignored(self):
        self._join(self.team_alpha_2)

        team = (
            self.env["team.team"]
            .with_context(default_team_id=self.team_beta.id)
            ._get_default_team("alpha", user_id=self.user_member.id)
        )

        self.assertEqual(team, self.team_alpha_2)

    def test_a_document_takes_its_owners_team_of_its_usage(self):
        self._join(self.team_beta)
        self._join(self.team_alpha_1)

        ticket = self.env["test.team.ticket"].create({"user_id": self.user_member.id})

        self.assertEqual(ticket.team_id, self.team_alpha_1)

    @users("alpha_manager")
    def test_a_usage_administrator_edits_only_teams_of_their_usage(self):
        self.team_alpha_1.with_env(self.env).name = "Alpha One"
        with self.assertRaises(AccessError):
            self.team_beta.with_env(self.env).name = "Beta One"
            self.env.flush_all()

    @users("alpha_manager")
    def test_a_usage_administrator_cannot_delete_a_team_another_usage_shares(self):
        self.team_alpha_1.with_env(self.env).unlink()
        with self.assertRaises(AccessError):
            self.team_both.with_env(self.env).unlink()

    def test_a_teams_administrator_deletes_any_team(self):
        team_manager = mail_new_test_user(
            self.env, login="team_manager", groups="team.group_team_manager"
        )
        self.team_both.with_user(team_manager).unlink()
        self.assertFalse(self.team_both.exists())

    def test_the_users_teams_of_a_usage_are_searchable(self):
        self._join(self.team_beta)
        Users = self.env["res.users"].with_context(active_test=False)

        self.assertIn(
            self.user_member,
            Users.search([("beta_team_ids", "in", self.team_beta.ids)]),
        )
        self.assertIn(self.user_member, Users.search([("alpha_team_ids", "=", False)]))
        self.assertNotIn(
            self.user_member, Users.search([("beta_team_ids", "=", False)])
        )
        self.assertEqual(self.user_member.beta_team_ids, self.team_beta)
        self.assertFalse(self.user_member.alpha_team_ids)

    def test_changing_a_usage_flag_clears_the_rule_cache(self):
        with patch.object(type(self.env.registry), "clear_cache") as clear_cache:
            self.team_beta.use_alpha = True
        clear_cache.assert_called()

    def test_archiving_a_team_archives_its_memberships(self):
        membership = self._join(self.team_beta)

        self.team_beta.action_archive()

        self.assertFalse(membership.active)
