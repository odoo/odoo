from unittest.mock import patch

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import common

from odoo.addons.mail.tests.common import mail_new_test_user


class TestBadgeGranting(common.TransactionCase):
    """Tests for badge granting rules and monthly limits."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Patch send_mail to avoid actual email sending
        patch_email = patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            lambda *args, **kwargs: None,
        )
        cls.startClassPatcher(patch_email)

        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_granter = mail_new_test_user(
            cls.env,
            login="badge_granter",
            name="Badge Granter",
            email="granter@example.com",
            karma=100,
            groups="base.group_user",
        )
        cls.user_recipient = mail_new_test_user(
            cls.env,
            login="badge_recipient",
            name="Badge Recipient",
            email="badge_recipient@example.com",
            karma=100,
            groups="base.group_user",
        )
        cls.user_vip = mail_new_test_user(
            cls.env,
            login="badge_vip",
            name="VIP User",
            email="vip@example.com",
            karma=100,
            groups="base.group_user",
        )

    # --- rule_auth = 'everyone' ---

    def test_everyone_can_grant(self):
        """Badge with rule_auth='everyone' can be granted by any user."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Everyone Badge",
                "rule_auth": "everyone",
            }
        )
        status = badge.with_user(self.user_granter)._get_badge_grant_status()
        self.assertEqual(status, badge.CAN_GRANT)

    # --- rule_auth = 'nobody' ---

    def test_nobody_can_grant(self):
        """Badge with rule_auth='nobody' cannot be granted by regular users."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Nobody Badge",
                "rule_auth": "nobody",
            }
        )
        status = badge.with_user(self.user_granter)._get_badge_grant_status()
        self.assertEqual(status, badge.NOBODY_CAN_GRANT)

    def test_nobody_admin_override(self):
        """Admin can always grant regardless of rule_auth."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Nobody Badge",
                "rule_auth": "nobody",
            }
        )
        status = badge.with_user(self.user_admin)._get_badge_grant_status()
        self.assertEqual(status, badge.CAN_GRANT)

    # --- rule_auth = 'users' ---

    def test_users_authorized_can_grant(self):
        """User in the authorized list can grant."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "VIP Badge",
                "rule_auth": "users",
                "rule_auth_user_ids": [(6, 0, [self.user_vip.id])],
            }
        )
        status = badge.with_user(self.user_vip)._get_badge_grant_status()
        self.assertEqual(status, badge.CAN_GRANT)

    def test_users_unauthorized_cannot_grant(self):
        """User NOT in the authorized list gets USER_NOT_VIP."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "VIP Badge",
                "rule_auth": "users",
                "rule_auth_user_ids": [(6, 0, [self.user_vip.id])],
            }
        )
        status = badge.with_user(self.user_granter)._get_badge_grant_status()
        self.assertEqual(status, badge.USER_NOT_VIP)

    # --- rule_auth = 'having' ---

    def test_having_with_prerequisite_badge(self):
        """User with the prerequisite badge can grant."""
        prereq_badge = self.env["gamification.badge"].create(
            {
                "name": "Prerequisite Badge",
                "rule_auth": "everyone",
            }
        )
        badge = self.env["gamification.badge"].create(
            {
                "name": "Having Badge",
                "rule_auth": "having",
                "rule_auth_badge_ids": [(6, 0, [prereq_badge.id])],
            }
        )
        # Grant prerequisite to granter
        self.env["gamification.badge.user"].create(
            {
                "user_id": self.user_granter.id,
                "badge_id": prereq_badge.id,
                "sender_id": self.user_admin.id,
            }
        )

        status = badge.with_user(self.user_granter)._get_badge_grant_status()
        self.assertEqual(status, badge.CAN_GRANT)

    def test_having_without_prerequisite_badge(self):
        """User without the prerequisite badge gets BADGE_REQUIRED."""
        prereq_badge = self.env["gamification.badge"].create(
            {
                "name": "Prerequisite Badge",
                "rule_auth": "everyone",
            }
        )
        badge = self.env["gamification.badge"].create(
            {
                "name": "Having Badge",
                "rule_auth": "having",
                "rule_auth_badge_ids": [(6, 0, [prereq_badge.id])],
            }
        )
        status = badge.with_user(self.user_granter)._get_badge_grant_status()
        self.assertEqual(status, badge.BADGE_REQUIRED)

    # --- Monthly limits ---

    def test_monthly_limit_not_exceeded(self):
        """Badge with monthly limit allows granting when under the cap."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Limited Badge",
                "rule_auth": "everyone",
                "rule_max": True,
                "rule_max_number": 3,
            }
        )
        status = badge.with_user(self.user_granter)._get_badge_grant_status()
        self.assertEqual(status, badge.CAN_GRANT)

    def test_monthly_limit_exceeded(self):
        """Badge returns TOO_MANY when monthly limit is reached."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Limited Badge",
                "rule_auth": "everyone",
                "rule_max": True,
                "rule_max_number": 1,
            }
        )
        # Grant once (as granter via wizard to respect create_uid)
        self.env["gamification.badge.user"].with_user(self.user_granter).create(
            {
                "user_id": self.user_recipient.id,
                "badge_id": badge.id,
                "sender_id": self.user_granter.id,
            }
        )

        # Invalidate computed stats
        badge.invalidate_recordset()
        status = badge.with_user(self.user_granter)._get_badge_grant_status()
        self.assertEqual(status, badge.TOO_MANY)

    def test_remaining_sending_calc(self):
        """remaining_sending correctly computes remaining grants."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Limited Badge",
                "rule_auth": "everyone",
                "rule_max": True,
                "rule_max_number": 3,
            }
        )
        badge_as_granter = badge.with_user(self.user_granter)
        # No grants yet — should have 3 remaining
        self.assertEqual(badge_as_granter.remaining_sending, 3)

    def test_remaining_sending_unlimited(self):
        """Badge without monthly limit returns -1 (infinite)."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Unlimited Badge",
                "rule_auth": "everyone",
                "rule_max": False,
            }
        )
        badge_as_granter = badge.with_user(self.user_granter)
        self.assertEqual(badge_as_granter.remaining_sending, -1)

    def test_remaining_sending_nobody(self):
        """Badge with rule_auth='nobody' returns 0 remaining."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Nobody Badge",
                "rule_auth": "nobody",
            }
        )
        badge_as_granter = badge.with_user(self.user_granter)
        self.assertEqual(badge_as_granter.remaining_sending, 0)

    # --- check_granting raises ---

    def test_check_granting_raises_on_nobody(self):
        """check_granting raises UserError for nobody badges."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Nobody Badge",
                "rule_auth": "nobody",
            }
        )
        with self.assertRaises(UserError):
            badge.with_user(self.user_granter).check_granting()

    def test_check_granting_raises_on_unauthorized_user(self):
        """check_granting raises UserError when user is not in auth list."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "VIP Badge",
                "rule_auth": "users",
                "rule_auth_user_ids": [(6, 0, [self.user_vip.id])],
            }
        )
        with self.assertRaises(UserError):
            badge.with_user(self.user_granter).check_granting()

    def test_check_granting_raises_on_missing_prerequisite(self):
        """check_granting raises UserError when prerequisite badge is missing."""
        prereq_badge = self.env["gamification.badge"].create(
            {
                "name": "Prerequisite",
                "rule_auth": "everyone",
            }
        )
        badge = self.env["gamification.badge"].create(
            {
                "name": "Having Badge",
                "rule_auth": "having",
                "rule_auth_badge_ids": [(6, 0, [prereq_badge.id])],
            }
        )
        with self.assertRaises(UserError):
            badge.with_user(self.user_granter).check_granting()

    def test_check_granting_raises_on_too_many(self):
        """check_granting raises UserError when monthly limit exceeded."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Limited Badge",
                "rule_auth": "everyone",
                "rule_max": True,
                "rule_max_number": 1,
            }
        )
        self.env["gamification.badge.user"].with_user(self.user_granter).create(
            {
                "user_id": self.user_recipient.id,
                "badge_id": badge.id,
                "sender_id": self.user_granter.id,
            }
        )
        badge.invalidate_recordset()
        with self.assertRaises(UserError):
            badge.with_user(self.user_granter).check_granting()

    # --- Badge stats ---

    def test_badge_granted_count(self):
        """granted_count and granted_users_count are computed correctly."""
        badge = self.env["gamification.badge"].create(
            {
                "name": "Stats Badge",
                "rule_auth": "everyone",
            }
        )
        # Grant twice to same user + once to another
        self.env["gamification.badge.user"].create(
            {
                "user_id": self.user_recipient.id,
                "badge_id": badge.id,
                "sender_id": self.user_granter.id,
            }
        )
        self.env["gamification.badge.user"].create(
            {
                "user_id": self.user_recipient.id,
                "badge_id": badge.id,
                "sender_id": self.user_vip.id,
            }
        )
        self.env["gamification.badge.user"].create(
            {
                "user_id": self.user_vip.id,
                "badge_id": badge.id,
                "sender_id": self.user_granter.id,
            }
        )

        badge.invalidate_recordset()
        self.assertEqual(badge.granted_count, 3, "Total grants should be 3")
        self.assertEqual(badge.granted_users_count, 2, "Unique owners should be 2")


class TestBadgeUserKanbanCardTemplate(common.TransactionCase):
    """`badge_user_kanban_view`'s `<templates>` must declare a single
    `t-name="card"` node -- a nested duplicate silently overwrites the
    outer node's attributes (e.g. its `row g-0` class) in the compiled
    kanban template.
    """

    def test_only_one_card_template_node(self):
        view = self.env.ref("gamification.badge_user_kanban_view")
        arch = etree.fromstring(view.arch_db)
        card_nodes = arch.findall('.//templates/t[@t-name="card"]')
        self.assertEqual(
            len(card_nodes),
            1,
            'badge_user_kanban_view must declare exactly one t-name="card" node',
        )
        self.assertEqual(
            card_nodes[0].get("class"),
            "row g-0",
            "the card template's class must not be silently overwritten",
        )


class TestGrantBadgeWizardActionContext(common.TransactionCase):
    """`action_grant_wizard`'s context must only carry the context keys the
    wizard actually reads -- `default_badge_id` (consumed by the wizard's
    `badge_id` field default). The `badge_id` context key is dead: nothing
    in the module reads a plain (non-`default_`) `badge_id` context key.
    """

    def test_context_has_no_dead_badge_id_key(self):
        from odoo.tools.safe_eval import safe_eval

        action = self.env.ref("gamification.action_grant_wizard")
        context = safe_eval(action.context, {"active_id": 1})
        self.assertIn("default_badge_id", context)
        self.assertNotIn(
            "badge_id",
            context,
            "the plain 'badge_id' context key is dead -- nothing reads it",
        )
