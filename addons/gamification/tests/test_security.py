from collections import defaultdict
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import common

from odoo.addons.mail.tests.common import mail_new_test_user


class TestSecurityRules(common.TransactionCase):
    """Tests for ir.rule security rules on gamification models."""

    @classmethod
    def setUpClass(cls):
        """Set up two standard users and shared test data."""
        super().setUpClass()
        patch_email = patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            lambda *args, **kwargs: None,
        )
        cls.startClassPatcher(patch_email)

        cls.user_a = mail_new_test_user(
            cls.env,
            login="sec_user_a",
            name="Security User A",
            email="sec_a@example.com",
            karma=0,
            groups="base.group_user",
        )
        cls.user_b = mail_new_test_user(
            cls.env,
            login="sec_user_b",
            name="Security User B",
            email="sec_b@example.com",
            karma=0,
            groups="base.group_user",
        )

        # Streak type setup (required for streak records)
        partner_model = cls.env["ir.model"]._get("res.partner")
        date_field = cls.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "write_date")],
            limit=1,
        )
        cls.streak_type = cls.env["gamification.streak.type"].create(
            {
                "name": "Test Streak Type",
                "model_id": partner_model.id,
                "date_field_id": date_field.id,
                "domain": "[('create_uid', '=', user.id)]",
                "karma_bonus": 5,
                "freeze_allowance": 1,
            }
        )

        # Kudos category
        cls.kudos_category = cls.env.ref("gamification.kudos_category_teamwork")

    def test_streak_user_write_rule(self):
        """Users cannot modify another user's streak record."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.user_a.id,
                "streak_type_id": self.streak_type.id,
            }
        )
        with self.assertRaises(AccessError):
            streak.with_user(self.user_b).write({"freeze_remaining": 5})

    def test_kudos_user_write_rule(self):
        """Users cannot modify kudos sent by another user."""
        kudos = (
            self.env["gamification.kudos"]
            .with_user(self.user_a)
            .create(
                {
                    "sender_id": self.user_a.id,
                    "recipient_id": self.user_b.id,
                    "category_id": self.kudos_category.id,
                    "message": "Great work!",
                }
            )
        )
        with self.assertRaises(AccessError):
            kudos.with_user(self.user_b).write({"message": "Tampered!"})

    def test_karma_tracking_system_only(self):
        """Non-system users cannot read karma tracking records."""
        # Create a tracking record as superuser
        self.env["gamification.karma.tracking"].create(
            {
                "user_id": self.user_a.id,
                "old_value": 0,
                "new_value": 10,
            }
        )
        with self.assertRaises(AccessError):
            self.env["gamification.karma.tracking"].with_user(self.user_a).search([])


class TestGroupMigration(common.TransactionCase):
    """Tests for the app's own access tiers and how they are populated."""

    def test_group_user_implies_gamification_user(self):
        """Every internal user reaches the app tier through base.group_user."""
        group_user = self.env.ref("base.group_user")
        app_group = self.env.ref("gamification.group_gamification_user")
        self.assertIn(app_group, group_user.implied_ids)

        employee = mail_new_test_user(
            self.env,
            login="gam_plain_employee",
            name="Plain Employee",
            email="gam_plain@example.com",
            groups="base.group_user",
        )
        self.assertTrue(employee.has_group("gamification.group_gamification_user"))

    def test_erp_manager_implies_gamification_manager(self):
        """The previous administrators keep their reach through the manager tier."""
        erp_manager = self.env.ref("base.group_erp_manager")
        app_manager = self.env.ref("gamification.group_gamification_manager")
        self.assertIn(app_manager, erp_manager.implied_ids)

        manager = mail_new_test_user(
            self.env,
            login="gam_erp_manager",
            name="ERP Manager",
            email="gam_erp@example.com",
            groups="base.group_user,base.group_erp_manager",
        )
        self.assertTrue(manager.has_group("gamification.group_gamification_manager"))
        # The manager tier implies the user tier, not the other way round.
        self.assertTrue(manager.has_group("gamification.group_gamification_user"))

    def test_no_implication_cycle(self):
        """The app tier must not imply back the group that grants it."""
        app_group = self.env.ref("gamification.group_gamification_user")
        group_user = self.env.ref("base.group_user")
        self.assertNotIn(group_user, app_group.implied_ids)
        self.assertNotIn(group_user, app_group.all_implied_ids)


class TestAclParity(common.TransactionCase):
    """The app tiers must grant exactly what base.group_user/erp_manager did."""

    # model -> (read, write, create, unlink), as this module's own CSV granted
    # base.group_user before the tiers existed. Hardcoded rather than derived:
    # once the change is merged the "before" state is no longer queryable, so
    # the reference has to travel with the test or it asserts nothing.
    USER_GRANTS = {
        "gamification.achievement": (1, 0, 0, 0),
        "gamification.achievement.unlock": (1, 0, 0, 0),
        "gamification.activity": (1, 0, 0, 0),
        "gamification.badge": (1, 0, 0, 0),
        "gamification.badge.user": (1, 0, 1, 0),
        "gamification.badge.user.wizard": (1, 1, 1, 0),
        "gamification.challenge": (1, 0, 0, 0),
        "gamification.challenge.line": (1, 0, 0, 0),
        "gamification.engagement.snapshot": (1, 0, 0, 0),
        "gamification.goal": (1, 1, 0, 0),
        "gamification.goal.definition": (1, 0, 0, 0),
        "gamification.goal.wizard": (1, 1, 1, 0),
        "gamification.karma.rank": (1, 0, 0, 0),
        "gamification.kudos": (1, 1, 1, 0),
        "gamification.kudos.category": (1, 0, 0, 0),
        "gamification.mentorship": (1, 1, 1, 0),
        "gamification.quest": (1, 0, 0, 0),
        "gamification.quest.enrollment": (1, 1, 1, 0),
        "gamification.quest.step": (1, 0, 0, 0),
        # Read-only since 1.2.  It was employee-writable with no record rule, so
        # anyone could INSERT a completion on someone else's enrolment and skip
        # the prerequisite check that only complete_step performs; that method
        # sudo()es the create now.
        "gamification.quest.step.completion": (1, 0, 0, 0),
        "gamification.season": (1, 0, 0, 0),
        "gamification.skill.node": (1, 0, 0, 0),
        "gamification.skill.node.unlock": (1, 0, 0, 0),
        "gamification.skill.tree": (1, 0, 0, 0),
        "gamification.streak": (1, 0, 0, 0),
        "gamification.streak.type": (1, 0, 0, 0),
        "gamification.team": (1, 0, 0, 0),
    }

    # Same, for base.group_erp_manager. gamification.karma.rank is the one
    # deliberate addition: the old CSV only gave it to base.group_system, which
    # left the manager tier unable to configure ranks from its own menu.
    MANAGER_GRANTS = {
        model: (1, 1, 1, 1)
        for model in USER_GRANTS
        if not model.endswith(".wizard")  # transients reached via the user tier
    } | {"gamification.karma.rank": (1, 1, 1, 1)}

    def _module_grants(self, group_xmlid):
        """Return {model: perms} for this module's permission rows on one group.

        Scoped to rows owned by ``gamification`` so a bridge module granting
        the same group elsewhere (hr_gamification does) cannot mask a regression.
        An operation counts whatever the row's domain, as the access line it
        was converted from granted it whatever the rules then narrowed, and
        on a model the tier has a row for, the rows of the groups it implies
        count too: the conversion does not repeat on the manager what the user
        tier already grants.

        :param str group_xmlid: external id of the group to collect
        :rtype: dict[str, tuple[int, int, int, int]]
        """
        xmlids = self.env["ir.model.data"].search(
            [("module", "=", "gamification"), ("model", "=", "ir.access")]
        )
        group = self.env.ref(group_xmlid)
        accesses = self.env["ir.access"].browse(xmlids.mapped("res_id"))
        granting = accesses.filtered(
            lambda access: (
                access.kind == "permission" and access.domain != "[(0, '=', 1)]"
            )
        )
        own = set(
            granting.filtered(lambda a: a.group_id == group).model_id.mapped("model")
        )
        operations = defaultdict(set)
        for access in granting:
            model = access.model_id.model
            if model in own and access.group_id in group.all_implied_ids:
                operations[model].update(access.operation)
        return {
            model: tuple(int(letter in ops) for letter in "rucd")
            for model, ops in operations.items()
        }

    def test_user_tier_grants_match_the_old_employee_rows(self):
        """No internal user gained or lost model access in the re-pointing."""
        self.assertEqual(
            self._module_grants("gamification.group_gamification_user"),
            self.USER_GRANTS,
        )

    def test_manager_tier_grants_match_the_old_erp_manager_rows(self):
        """The seven erp_manager holders keep the same CRUD, plus karma ranks."""
        self.assertEqual(
            self._module_grants("gamification.group_gamification_manager"),
            self.MANAGER_GRANTS,
        )

    def test_no_row_still_points_at_a_base_tier(self):
        """The module owns its access tiers; no CSV row names base.* any more."""
        stale = {
            acl.model_id.model
            for acl in self.env["ir.access"].browse(
                self.env["ir.model.data"]
                .search(
                    [
                        ("module", "=", "gamification"),
                        ("model", "=", "ir.access"),
                    ]
                )
                .mapped("res_id")
            )
            if acl.kind == "permission"
            and acl.group_id
            in (
                self.env.ref("base.group_user"),
                self.env.ref("base.group_erp_manager"),
            )
        }
        self.assertFalse(stale)

    def test_plain_employee_reads_every_model_but_karma_tracking(self):
        """Behavioural counterpart: the tier actually reaches the employee.

        Only ``read`` is asserted here. Writes stay in the grant maps above,
        because an installed bridge module may legitimately widen them for a
        plain employee and that is not this module's regression to catch.
        """
        employee = mail_new_test_user(
            self.env,
            login="gam_acl_employee",
            name="ACL Employee",
            email="gam_acl@example.com",
            groups="base.group_user",
        )
        for model in self.USER_GRANTS:
            with self.subTest(model=model):
                records = self.env[model].with_user(employee).browse()
                self.assertTrue(records.has_access("read"))

        tracking = self.env["gamification.karma.tracking"].with_user(employee)
        self.assertFalse(tracking.browse().has_access("read"))

    def test_manager_can_write_karma_rank_but_not_karma_tracking(self):
        """The new rank row lands on the tier, and the audit trail stays closed.

        karma.tracking is deliberately left system-only: it is the karma audit
        trail, not configuration, so a gamification administrator without
        base.group_system must not reach it.
        """
        manager = mail_new_test_user(
            self.env,
            login="gam_rank_manager",
            name="Rank Manager",
            email="gam_rank@example.com",
            groups="base.group_user,gamification.group_gamification_manager",
        )
        self.assertFalse(manager.has_group("base.group_system"))

        rank = self.env["gamification.karma.rank"].with_user(manager)
        self.assertTrue(rank.browse().has_access("write"))
        self.assertTrue(rank.browse().has_access("create"))

        tracking = self.env["gamification.karma.tracking"].with_user(manager)
        self.assertFalse(tracking.browse().has_access("write"))
