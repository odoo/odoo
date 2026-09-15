"""Regression tests for defects found in the gamification audit.

Each test here failed before its corresponding fix and passes after it.
Where the defect was a security one, the test also asserts the control path
(the route that was always correctly blocked) so a future refactor that
loosens the guard is caught rather than silently accepted.
"""

import datetime
from datetime import date, timedelta
from unittest.mock import patch

from psycopg import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common

from odoo.addons.mail.tests.common import mail_new_test_user


class TestKarmaIntegrity(common.TransactionCase):
    """karma == sum of every recorded gain, under all insertion orders."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tracking = cls.env["gamification.karma.tracking"]

    def _user(self, login):
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )

    def test_batch_create_accumulates(self):
        """Several rows for one user in a single create() must all count."""
        user = self._user("karma_batch")
        self.env.flush_all()
        self.Tracking.create(
            [{"user_id": user.id, "gain": 10}, {"user_id": user.id, "gain": 5}]
        )
        self.env.flush_all()
        user.invalidate_recordset()
        self.assertEqual(user.karma, 15, "Both rows of a batch must be counted")

    def test_backdated_row_still_counts(self):
        """A row inserted with an older tracking_date must not be swallowed."""
        user = self._user("karma_backdate")
        user.karma = 150
        self.env.flush_all()
        self.Tracking.create(
            [
                {
                    "user_id": user.id,
                    "gain": 25,
                    "tracking_date": fields.Datetime.now() - timedelta(days=365),
                }
            ]
        )
        self.env.flush_all()
        user.invalidate_recordset()
        self.assertEqual(user.karma, 175, "Backdated gains must still apply")

    def test_consolidation_preserves_pending_recompute(self):
        """Consolidating must not discard a karma recompute pending in the
        same transaction."""
        user = self._user("karma_consol")
        self.env.flush_all()
        old = fields.Datetime.now() - timedelta(days=70)
        self.Tracking.create([{"user_id": user.id, "gain": 30, "tracking_date": old}])
        self.env.flush_all()
        user.invalidate_recordset()
        self.assertEqual(user.karma, 30)

        user._add_karma(40, reason="pending during consolidation")
        self.Tracking._consolidate_cron()
        self.env.flush_all()
        user.invalidate_recordset()
        self.assertEqual(
            user.karma, 70, "Consolidation must be karma-neutral, not destructive"
        )

    def test_consolidation_is_karma_neutral(self):
        """CONTROL: consolidation alone changes no karma."""
        user = self._user("karma_neutral")
        self.env.flush_all()
        old = fields.Datetime.now() - timedelta(days=70)
        self.Tracking.create([{"user_id": user.id, "gain": 30, "tracking_date": old}])
        self.env.flush_all()
        user.invalidate_recordset()
        before = user.karma
        self.Tracking._consolidate_cron()
        self.env.flush_all()
        user.invalidate_recordset()
        self.assertEqual(user.karma, before, "CONTROL: consolidation is neutral")


class TestGoalStateMachine(common.TransactionCase):
    """State transitions must not depend on the measured value changing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_test = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Goal State User",
                    "login": "goal_state_user",
                    "email": "gs@example.com",
                    "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.model_goal = cls.env["ir.model"]._get("gamification.goal")

    def _definition(self, code):
        return self.env["gamification.goal.definition"].create(
            {
                "name": "State Def",
                "computation_mode": "python",
                "model_id": self.model_goal.id,
                "compute_code": code,
                "condition": "higher",
            }
        )

    def _goal(self, definition, target, current, end_date, state="inprogress"):
        return self.env["gamification.goal"].create(
            {
                "definition_id": definition.id,
                "user_id": self.user_test.id,
                "target_goal": target,
                "current": current,
                "state": state,
                "start_date": date.today() - timedelta(days=30),
                "end_date": end_date,
            }
        )

    def test_expired_goal_fails_even_when_value_flat(self):
        goal = self._goal(
            self._definition("result = 5"),
            target=100,
            current=5,
            end_date=date.today() - timedelta(days=1),
        )
        goal.update_goal()
        self.assertEqual(goal.state, "failed")
        self.assertTrue(goal.closed)

    def test_expired_goal_fails_when_value_changed(self):
        """CONTROL: the path that always worked still works."""
        goal = self._goal(
            self._definition("result = 5"),
            target=100,
            current=3,
            end_date=date.today() - timedelta(days=1),
        )
        goal.update_goal()
        self.assertEqual(goal.current, 5)
        self.assertEqual(goal.state, "failed")

    def test_reached_goal_reverts_when_value_drops(self):
        goal = self._goal(
            self._definition("result = 20"), target=100, current=0, end_date=False
        )
        goal.write({"state": "reached"})
        goal.update_goal()
        self.assertEqual(goal.state, "inprogress")

    def test_goal_becomes_reached(self):
        """CONTROL: crossing the target still sets reached."""
        goal = self._goal(
            self._definition("result = 150"), target=100, current=0, end_date=False
        )
        goal.update_goal()
        self.assertEqual(goal.state, "reached")

    def test_draft_goal_untouched_by_recomputation(self):
        """A draft goal must not be auto-started by an update."""
        goal = self._goal(
            self._definition("result = 150"),
            target=100,
            current=0,
            end_date=False,
            state="draft",
        )
        goal.update_goal()
        self.assertEqual(goal.state, "draft")


class TestMentorshipSecurity(common.TransactionCase):
    """A mentor must not be able to mint karma for themselves."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        emp = cls.env.ref("base.group_user")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.attacker = Users.create(
            {
                "name": "Mentor Attacker",
                "login": "m_attacker",
                "email": "ma@example.com",
                "group_ids": [(6, 0, [emp.id])],
            }
        )
        cls.victim = Users.create(
            {
                "name": "Mentee Victim",
                "login": "m_victim",
                "email": "mv@example.com",
                "group_ids": [(6, 0, [emp.id])],
            }
        )

    def test_employee_cannot_set_own_payout(self):
        """Reward fields are manager-only, so the amount is never attacker-set."""
        with self.assertRaises(AccessError):
            self.env["gamification.mentorship"].with_user(self.attacker).create(
                {
                    "mentor_id": self.attacker.id,
                    "mentee_id": self.victim.id,
                    "mentor_karma_on_completion": 999999,
                }
            )

    def test_mentor_cannot_complete_own_mentorship(self):
        """Completion pays the mentor, so the mentor may not trigger it."""
        mentorship = self.env["gamification.mentorship"].create(
            {"mentor_id": self.attacker.id, "mentee_id": self.victim.id}
        )
        mentorship.with_user(self.victim).action_accept()
        with self.assertRaises(AccessError):
            mentorship.with_user(self.attacker).action_complete()

    def test_mentee_can_complete_and_mentor_is_paid(self):
        """CONTROL: the legitimate path still works and still pays."""
        mentorship = self.env["gamification.mentorship"].create(
            {
                "mentor_id": self.attacker.id,
                "mentee_id": self.victim.id,
                "mentor_karma_on_completion": 100,
            }
        )
        mentorship.with_user(self.victim).action_accept()
        before = self.attacker.karma
        mentorship.with_user(self.victim).action_complete()
        self.attacker.invalidate_recordset()
        self.assertEqual(mentorship.state, "completed")
        self.assertEqual(self.attacker.karma, before + 100)

    def test_mentor_cannot_confirm_own_pending_mentorship_by_direct_write(self):
        """`state` carries no readonly/groups=, so nothing at the ORM layer
        stopped the proposer from writing `state` directly -- bypassing
        `_check_may_accept()`'s consent gate entirely.
        """
        mentorship = self.env["gamification.mentorship"].create(
            {"mentor_id": self.attacker.id, "mentee_id": self.victim.id}
        )
        self.assertEqual(mentorship.state, "pending")
        with self.assertRaises(UserError):
            mentorship.with_user(self.attacker).write({"state": "active"})
        mentorship.invalidate_recordset()
        self.assertEqual(
            mentorship.state,
            "pending",
            "state must not move without the mentee's consent",
        )

    def test_sudo_can_still_write_state(self):
        """CONTROL: action_accept/decline/complete/cancel themselves rely on
        sudo() to apply the state change after their own checks pass.
        """
        mentorship = self.env["gamification.mentorship"].create(
            {"mentor_id": self.attacker.id, "mentee_id": self.victim.id}
        )
        mentorship.sudo().write({"state": "active"})
        self.assertEqual(mentorship.state, "active")

    def test_employee_cannot_see_third_party_mentorship(self):
        """The record rule hides pairings the user is not part of."""
        other_a = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Other A",
                    "login": "other_a",
                    "email": "oa@example.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        mentorship = self.env["gamification.mentorship"].create(
            {"mentor_id": other_a.id, "mentee_id": self.victim.id}
        )
        visible = (
            self.env["gamification.mentorship"]
            .with_user(self.attacker)
            .search([("id", "=", mentorship.id)])
        )
        self.assertFalse(visible, "Third-party mentorship must not be visible")


class TestStreakCronIdempotency(common.TransactionCase):
    def test_repeated_cron_runs_are_noops(self):
        """Running the streak cron repeatedly in one day must not burn
        freeze days or break a streak."""
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Streak User",
                    "login": "streak_idem",
                    "email": "si@example.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        stype = self.env["gamification.streak.type"].create(
            {
                "name": "Idem Streak",
                "model_id": self.env.ref("base.model_res_partner").id,
                "date_field_id": self.env["ir.model.fields"]
                ._get("res.partner", "create_date")
                .id,
                "domain": "[('id','=',-1)]",  # never matches
            }
        )
        Streak = self.env["gamification.streak"]
        streak = Streak.create(
            {
                "user_id": user.id,
                "streak_type_id": stype.id,
                "current_count": 10,
                "state": "active",
                "last_activity_date": fields.Date.today() - timedelta(days=1),
            }
        )
        streak.freeze_remaining = 2
        self.env.flush_all()

        Streak._cron_update_streaks()
        after_first = streak.freeze_remaining
        self.assertEqual(after_first, 1, "First run consumes exactly one freeze day")

        for _ in range(3):
            Streak._cron_update_streaks()
        self.assertEqual(
            streak.freeze_remaining,
            after_first,
            "Repeat runs in the same day must be no-ops",
        )
        self.assertEqual(streak.current_count, 10, "Streak must survive repeat runs")
        self.assertEqual(streak.state, "active")


class TestStreakTimezone(common.TransactionCase):
    """A streak day is the user's calendar day, not a UTC day.

    Storage stays UTC; only the day *window* is resolved in the user's
    timezone, following the ``lunch.supplier`` / ``hr.employee._get_schedule_tz``
    pattern used elsewhere in core for calendar-day business logic.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stype = cls.env["gamification.streak.type"].create(
            {
                "name": "TZ Streak",
                "model_id": cls.env["ir.model"]._get("res.partner").id,
                "date_field_id": cls.env["ir.model.fields"]
                ._get("res.partner", "create_date")
                .id,
                "domain": "[('user_id','=',user.id)]",
            }
        )
        cls.monday = date(2026, 7, 13)
        cls.tuesday = date(2026, 7, 14)

    def _user_with_activity(self, login, tz, stored_utc):
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "tz": tz,
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        partner = self.env["res.partner"].create(
            {"name": f"{login} work", "user_id": user.id}
        )
        self.env.cr.execute(
            "UPDATE res_partner SET create_date=%s WHERE id=%s",
            (stored_utc, partner.id),
        )
        self.env.flush_all()
        self.env.invalidate_all()
        return user

    def test_evening_work_west_of_utc_counts_same_day(self):
        """UTC-6, Monday 19:00 local (Tuesday 01:00 UTC) is Monday activity."""
        user = self._user_with_activity(
            "tz_west", "America/Mexico_City", "2026-07-14 01:00:00"
        )
        self.assertTrue(self.stype._check_user_activity(user, self.monday))
        self.assertFalse(self.stype._check_user_activity(user, self.tuesday))

    def test_early_work_east_of_utc_counts_same_day(self):
        """UTC+9, Tuesday 07:00 local (Monday 22:00 UTC) is Tuesday activity."""
        user = self._user_with_activity("tz_east", "Asia/Tokyo", "2026-07-13 22:00:00")
        self.assertFalse(self.stype._check_user_activity(user, self.monday))
        self.assertTrue(self.stype._check_user_activity(user, self.tuesday))

    def test_user_without_timezone_uses_utc_day(self):
        """CONTROL: no tz set behaves exactly as before."""
        user = self._user_with_activity("tz_unset", False, "2026-07-13 12:00:00")
        self.assertTrue(self.stype._check_user_activity(user, self.monday))
        self.assertFalse(self.stype._check_user_activity(user, self.tuesday))

    def test_batch_check_groups_users_by_timezone(self):
        """Users in different timezones are bucketed independently in one batch."""
        west = self._user_with_activity(
            "tz_batch_west", "America/Mexico_City", "2026-07-14 01:00:00"
        )
        east = self._user_with_activity(
            "tz_batch_east", "Asia/Tokyo", "2026-07-13 22:00:00"
        )
        monday_active = self.stype._check_user_activity_batch(west + east, self.monday)
        self.assertEqual(
            monday_active,
            {west.id},
            "Only the UTC-6 user worked on Monday in their own timezone",
        )
        tuesday_active = self.stype._check_user_activity_batch(
            west + east, self.tuesday
        )
        self.assertEqual(tuesday_active, {east.id})


class TestCronErrorIsolation(common.TransactionCase):
    """One broken record must not abort a whole cron run."""

    def _user(self, login):
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )

    def test_bad_achievement_does_not_block_the_others(self):
        """A poison trigger_domain must not stop later achievements."""
        user = self._user("ach_isolation")
        partner_model = self.env["ir.model"]._get("res.partner")
        self.env["res.partner"].create({"name": "Isolation Partner"})

        # Ordered by sequence: the broken one is evaluated first.
        self.env["gamification.achievement"].create(
            {
                "name": "Broken Achievement",
                "sequence": 1,
                "model_id": partner_model.id,
                "trigger_domain": "[('field_that_does_not_exist','=',1)]",
                "trigger_count": 1,
                "karma_reward": 10,
            }
        )
        good = self.env["gamification.achievement"].create(
            {
                "name": "Good Achievement",
                "sequence": 2,
                "model_id": partner_model.id,
                "trigger_domain": "[]",
                "trigger_count": 1,
                "karma_reward": 10,
            }
        )
        self.env.flush_all()

        # Must not raise, and must still process the healthy achievement.
        self.env["gamification.achievement"]._cron_check_achievements()
        self.env.flush_all()

        unlocked = self.env["gamification.achievement.unlock"].search_count(
            [("achievement_id", "=", good.id), ("user_id", "=", user.id)]
        )
        self.assertTrue(
            unlocked,
            "A broken achievement must not prevent later ones from unlocking",
        )

    def test_bad_streak_type_does_not_block_the_others(self):
        """A poison streak domain must not stop later streaks."""
        user_bad = self._user("streak_bad")
        user_good = self._user("streak_good")
        partner_field = self.env["ir.model.fields"]._get("res.partner", "create_date")
        partner_model = self.env.ref("base.model_res_partner")
        Streak = self.env["gamification.streak"]

        bad_type = self.env["gamification.streak.type"].create(
            {
                "name": "Broken Streak",
                "model_id": partner_model.id,
                "date_field_id": partner_field.id,
                "domain": "[('nope_not_a_field','=',1)]",
            }
        )
        good_type = self.env["gamification.streak.type"].create(
            {
                "name": "Good Streak",
                "model_id": partner_model.id,
                "date_field_id": partner_field.id,
                "domain": "[('id','=',-1)]",
            }
        )
        yesterday = fields.Date.today() - timedelta(days=1)
        Streak.create(
            {
                "user_id": user_bad.id,
                "streak_type_id": bad_type.id,
                "current_count": 3,
                "state": "active",
                "last_activity_date": yesterday,
            }
        )
        good_streak = Streak.create(
            {
                "user_id": user_good.id,
                "streak_type_id": good_type.id,
                "current_count": 3,
                "state": "active",
                "last_activity_date": yesterday,
            }
        )
        good_streak.freeze_remaining = 1
        self.env.flush_all()

        Streak._cron_update_streaks()

        self.assertEqual(
            good_streak.freeze_remaining,
            0,
            "The healthy streak must still be processed despite a broken one",
        )
        self.assertEqual(
            good_streak.last_checked_date,
            fields.Date.today(),
            "The healthy streak must be marked as checked",
        )


class TestSkillTreeWiring(common.TransactionCase):
    """The skill tree must actually unlock when its quest completes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Skill User",
                    "login": "skill_user",
                    "email": "sk@example.com",
                    "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
                }
            )
        )
        cls.quest = cls.env["gamification.quest"].create({"name": "Skill Quest"})
        cls.tree = cls.env["gamification.skill.tree"].create({"name": "Tree"})
        cls.root = cls.env["gamification.skill.node"].create(
            {
                "name": "Root Node",
                "tree_id": cls.tree.id,
                "quest_id": cls.quest.id,
                "karma_reward": 30,
            }
        )
        cls.leaf = cls.env["gamification.skill.node"].create(
            {
                "name": "Leaf Node",
                "tree_id": cls.tree.id,
                "prerequisite_ids": [(6, 0, [cls.root.id])],
                "karma_reward": 40,
            }
        )

    def _complete_quest(self):
        enrollment = self.env["gamification.quest.enrollment"].create(
            {"quest_id": self.quest.id, "user_id": self.user.id}
        )
        enrollment._complete_quest()
        return enrollment

    def test_quest_completion_unlocks_linked_node(self):
        """Completing the quest unlocks the node gated on it."""
        self._complete_quest()
        unlocked = self.env["gamification.skill.node.unlock"].search_count(
            [("node_id", "=", self.root.id), ("user_id", "=", self.user.id)]
        )
        self.assertTrue(unlocked, "Quest-linked skill node must unlock on completion")

    def test_unlock_cascades_to_dependents(self):
        """Unlocking the root satisfies the leaf's only prerequisite."""
        self._complete_quest()
        leaf_unlocked = self.env["gamification.skill.node.unlock"].search_count(
            [("node_id", "=", self.leaf.id), ("user_id", "=", self.user.id)]
        )
        self.assertTrue(
            leaf_unlocked, "A node whose prerequisites are now met must cascade-unlock"
        )

    def test_unlock_grants_karma(self):
        """CONTROL: both nodes' karma rewards are actually granted."""
        before = self.user.karma
        self._complete_quest()
        self.user.invalidate_recordset()
        # quest 0 karma + root 30 + leaf 40
        self.assertEqual(self.user.karma, before + 70)

    def test_unlock_is_idempotent(self):
        """Re-running the unlock must not double-grant."""
        self._complete_quest()
        karma_after_first = self.user.karma
        self.env["gamification.skill.node"]._unlock_nodes_for_quest(
            self.env["gamification.quest.enrollment"].search(
                [("quest_id", "=", self.quest.id), ("user_id", "=", self.user.id)]
            )
        )
        self.user.invalidate_recordset()
        self.assertEqual(
            self.user.karma,
            karma_after_first,
            "Already-unlocked nodes must not re-grant",
        )

    def test_prerequisite_cycle_rejected(self):
        """A prerequisite cycle must be rejected at write time."""
        a = self.env["gamification.skill.node"].create(
            {"name": "Cycle A", "tree_id": self.tree.id}
        )
        b = self.env["gamification.skill.node"].create(
            {
                "name": "Cycle B",
                "tree_id": self.tree.id,
                "prerequisite_ids": [(6, 0, [a.id])],
            }
        )
        with self.assertRaises(ValidationError):
            a.write({"prerequisite_ids": [(6, 0, [b.id])]})


class TestNudgeBudget(common.TransactionCase):
    def test_low_progress_user_keeps_nudge_eligibility(self):
        """Users who receive no nudge must not have their cooldown consumed."""
        definition = self.env["gamification.goal.definition"].create(
            {"name": "Nudge Def", "computation_mode": "manually", "condition": "higher"}
        )
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Low Progress",
                    "login": "nudge_low_r",
                    "email": "nl@example.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        self.env["gamification.goal"].sudo().create(
            {
                "definition_id": definition.id,
                "user_id": user.id,
                "target_goal": 100,
                "current": 10,
                "state": "inprogress",
                "closed": False,
            }
        )
        self.env["res.users"]._nudge_goals_almost_done()
        user.invalidate_recordset(["last_gamification_nudge_date"])
        self.assertFalse(user.last_gamification_nudge_date)

    def test_high_progress_user_is_nudged(self):
        """CONTROL: a user at 90% is nudged and marked."""
        definition = self.env["gamification.goal.definition"].create(
            {"name": "Nudge Def", "computation_mode": "manually", "condition": "higher"}
        )
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "High Progress",
                    "login": "nudge_high_r",
                    "email": "nh@example.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        self.env["gamification.goal"].sudo().create(
            {
                "definition_id": definition.id,
                "user_id": user.id,
                "target_goal": 100,
                "current": 90,
                "state": "inprogress",
                "closed": False,
            }
        )
        self.env["res.users"]._nudge_goals_almost_done()
        user.invalidate_recordset(["last_gamification_nudge_date"])
        self.assertEqual(user.last_gamification_nudge_date, fields.Date.today())


class TestProfilePrivacy(common.TransactionCase):
    def test_user_can_set_own_visibility(self):
        """The privacy control must be reachable by the person it protects."""
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Privacy User",
                    "login": "privacy_user",
                    "email": "pu@example.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        user.with_user(user).write({"gamification_visibility": "private"})
        self.assertEqual(user.gamification_visibility, "private")

    def test_private_user_activity_hidden_from_others(self):
        """A private profile's activity rows are hidden at the ORM layer, not
        only inside the curated feed helper."""
        emp = self.env.ref("base.group_user")
        Users = self.env["res.users"].with_context(no_reset_password=True)
        private = Users.create(
            {
                "name": "Private One",
                "login": "priv_one",
                "email": "p1@example.com",
                "group_ids": [(6, 0, [emp.id])],
                "gamification_visibility": "private",
            }
        )
        observer = Users.create(
            {
                "name": "Observer",
                "login": "observer_one",
                "email": "o1@example.com",
                "group_ids": [(6, 0, [emp.id])],
            }
        )
        activity = self.env["gamification.activity"].create(
            {
                "user_id": private.id,
                "activity_type": "level_up",
                "summary": "secret activity",
            }
        )
        self.env.flush_all()
        visible = (
            self.env["gamification.activity"]
            .with_user(observer)
            .search([("id", "=", activity.id)])
        )
        self.assertFalse(visible, "Private user's activity must not be readable")

    def test_public_user_activity_visible(self):
        """CONTROL: a public profile's activity remains visible."""
        emp = self.env.ref("base.group_user")
        Users = self.env["res.users"].with_context(no_reset_password=True)
        public = Users.create(
            {
                "name": "Public One",
                "login": "pub_one",
                "email": "pb1@example.com",
                "group_ids": [(6, 0, [emp.id])],
                "gamification_visibility": "public",
            }
        )
        observer = Users.create(
            {
                "name": "Observer Two",
                "login": "observer_two",
                "email": "o2@example.com",
                "group_ids": [(6, 0, [emp.id])],
            }
        )
        activity = self.env["gamification.activity"].create(
            {
                "user_id": public.id,
                "activity_type": "level_up",
                "summary": "public activity",
            }
        )
        self.env.flush_all()
        visible = (
            self.env["gamification.activity"]
            .with_user(observer)
            .search([("id", "=", activity.id)])
        )
        self.assertTrue(visible, "CONTROL: public activity stays visible")


class TestGoalOutcomeFields(common.TransactionCase):
    """A participant must not be able to decide their own goal's outcome.

    ``write`` used to guard only ``current`` and ``state``.  Every field in
    ``OUTCOME_FIELDS`` feeds the reached/failed decision, so lowering your own
    ``target_goal`` was exactly as good as writing your own ``current`` -- and
    it collected the challenge's reward badge on the next cron run, including a
    ``rule_auth='nobody'`` badge that exists so users cannot grant it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = mail_new_test_user(
            cls.env,
            login="outcome_employee",
            name="Outcome Employee",
            email="outcome@example.com",
            groups="base.group_user",
        )
        cls.definition = cls.env["gamification.goal.definition"].create(
            {
                "name": "Outcome partners",
                "computation_mode": "count",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "domain": "[]",
                "condition": "higher",
            }
        )
        cls.badge = cls.env["gamification.badge"].create(
            {"name": "Outcome Reward", "rule_auth": "nobody"}
        )
        cls.challenge = cls.env["gamification.challenge"].create(
            {
                "name": "Outcome Challenge",
                "user_domain": f'[("id", "=", {cls.employee.id})]',
                "reward_id": cls.badge.id,
                "reward_realtime": True,
                "line_ids": [
                    (0, 0, {"definition_id": cls.definition.id, "target_goal": 10**9})
                ],
            }
        )
        cls.challenge.state = "inprogress"
        cls.goal = cls.env["gamification.goal"].search(
            [("challenge_id", "=", cls.challenge.id), ("user_id", "=", cls.employee.id)]
        )

    def test_owner_cannot_write_any_outcome_field(self):
        for field_name, value in (
            ("target_goal", 1),
            ("end_date", "2099-01-01"),
            ("closed", False),
            ("state", "reached"),
            ("current", 10**9),
        ):
            with self.subTest(field=field_name), self.assertRaises(UserError):
                self.goal.with_user(self.employee).write({field_name: value})

    def test_lowering_your_own_target_does_not_mint_the_reward(self):
        """The escalation end to end, through the real nightly cron."""
        with self.assertRaises(UserError):
            self.goal.with_user(self.employee).write({"target_goal": 1})

        self.env["gamification.challenge"]._cron_update(commit=False)
        self.goal.invalidate_recordset()

        self.assertNotEqual(self.goal.state, "reached")
        self.assertFalse(
            self.env["gamification.badge.user"].search_count(
                [("user_id", "=", self.employee.id), ("badge_id", "=", self.badge.id)]
            )
        )

    def test_a_manager_still_can(self):
        """CONTROL: the guard is about who writes, not about the field."""
        self.goal.write({"target_goal": 5})
        self.assertEqual(self.goal.target_goal, 5)


class TestQuestOwnership(common.TransactionCase):
    """Quest enrolments and step completions were the only employee-writable
    models in this module with no record rule, so anyone could rewrite another
    user's progress and skip the prerequisite check `complete_step` performs.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.intruder = mail_new_test_user(
            cls.env,
            login="quest_intruder",
            name="Intruder",
            email="qi@example.com",
            groups="base.group_user",
        )
        cls.owner = mail_new_test_user(
            cls.env,
            login="quest_owner",
            name="Owner",
            email="qo@example.com",
            groups="base.group_user",
        )
        cls.quest = cls.env["gamification.quest"].create({"name": "Ownership Quest"})
        cls.step_one = cls.env["gamification.quest.step"].create(
            {"quest_id": cls.quest.id, "name": "One", "sequence": 1}
        )
        cls.step_two = cls.env["gamification.quest.step"].create(
            {
                "quest_id": cls.quest.id,
                "name": "Two",
                "sequence": 2,
                "prerequisite_ids": [(6, 0, [cls.step_one.id])],
            }
        )
        cls.enrollment = cls.env["gamification.quest.enrollment"].create(
            {"quest_id": cls.quest.id, "user_id": cls.owner.id}
        )

    def test_cannot_forge_a_completion_on_another_users_enrolment(self):
        with self.assertRaises(AccessError):
            self.env["gamification.quest.step.completion"].with_user(
                self.intruder
            ).create({"enrollment_id": self.enrollment.id, "step_id": self.step_two.id})

    def test_cannot_write_another_users_enrolment(self):
        with self.assertRaises(AccessError):
            self.enrollment.with_user(self.intruder).write({"state": "abandoned"})

    def test_cannot_even_see_another_users_enrolment(self):
        self.assertFalse(
            self.env["gamification.quest.enrollment"]
            .with_user(self.intruder)
            .search([("id", "=", self.enrollment.id)])
        )

    def test_the_owner_still_progresses_normally(self):
        """CONTROL: complete_step sudoes the row it writes, so it still works.

        And it still refuses a step whose prerequisite is unmet -- the check
        the direct-INSERT hole used to walk straight past.
        """
        with self.assertRaises(UserError):
            self.enrollment.with_user(self.owner).complete_step(self.step_two)

        self.assertTrue(
            self.enrollment.with_user(self.owner).complete_step(self.step_one)
        )
        self.assertTrue(
            self.enrollment.with_user(self.owner).complete_step(self.step_two)
        )


class TestChallengeRetargeting(common.TransactionCase):
    """`user_domain` says who takes part, so narrowing it must narrow the
    challenge.  It used to be unioned into `user_ids` and never subtracted, so
    moving a challenge from one team to another silently ran it for both, and
    `default_get` seeded the domain with *every* internal user.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_a = cls.env["res.groups"].create({"name": "Retarget A"})
        cls.group_b = cls.env["res.groups"].create({"name": "Retarget B"})
        cls.user_a = mail_new_test_user(
            cls.env,
            login="retarget_a",
            name="A",
            email="ra@example.com",
            groups="base.group_user",
        )
        cls.user_b = mail_new_test_user(
            cls.env,
            login="retarget_b",
            name="B",
            email="rb@example.com",
            groups="base.group_user",
        )
        cls.user_a.group_ids = [(4, cls.group_a.id)]
        cls.user_b.group_ids = [(4, cls.group_b.id)]
        cls.definition = cls.env["gamification.goal.definition"].create(
            {
                "name": "Retarget definition",
                "computation_mode": "manually",
                "domain": "[]",
                "condition": "higher",
            }
        )
        cls.challenge = cls.env["gamification.challenge"].create(
            {
                "name": "Retarget Challenge",
                "user_domain": f'[("all_group_ids", "in", [{cls.group_a.id}])]',
                "line_ids": [
                    (0, 0, {"definition_id": cls.definition.id, "target_goal": 1})
                ],
            }
        )
        cls.challenge.state = "inprogress"

    def test_narrowing_the_domain_narrows_the_roster(self):
        self.assertIn(self.user_a, self.challenge.user_ids)
        self.assertNotIn(self.user_b, self.challenge.user_ids)

        self.challenge.user_domain = f'[("all_group_ids", "in", [{self.group_b.id}])]'
        self.challenge._recompute_challenge_users()

        self.assertNotIn(
            self.user_a,
            self.challenge.user_ids,
            "retargeting must drop the audience it moved away from",
        )
        self.assertIn(self.user_b, self.challenge.user_ids)

    def test_hand_added_participants_survive_a_retarget(self):
        """That is what `manual_user_ids` is for."""
        self.challenge.manual_user_ids = [(4, self.user_b.id)]
        self.challenge.user_domain = "[]"
        self.challenge._recompute_challenge_users()
        self.assertIn(self.user_b, self.challenge.user_ids)


class TestConsolidationPreservesGain(common.TransactionCase):
    """Consolidation used to telescope: it kept the oldest `old_value` and the
    newest `new_value` and assumed every row in between chained.  Nothing
    declares or checks that, and an administrator editing or deleting a row in
    the technical view breaks it -- after which consolidation moved karma, in
    whichever direction the break went, up to two months later and silently.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            login="consolidation_user",
            name="Consolidation User",
            email="cons@example.com",
            groups="base.group_user",
        )
        cls.Tracking = cls.env["gamification.karma.tracking"]

    def _gains(self):
        return sum(
            row.new_value - (row.old_value or 0)
            for row in self.Tracking.search([("user_id", "=", self.user.id)])
        )

    def _consolidate_everything(self):
        self.env.cr.execute(
            "UPDATE gamification_karma_tracking SET tracking_date = %s WHERE user_id = %s",
            [datetime.datetime(2026, 5, 10, 12, 0), self.user.id],
        )
        self.env.invalidate_all()
        self.Tracking._process_consolidate(datetime.datetime(2026, 5, 1))
        self.env.invalidate_all()

    def test_gain_survives_an_edited_chain(self):
        for gain in (10, 20, 30):
            self.user._add_karma(gain, reason="seed")
        self.env.flush_all()

        rows = self.Tracking.search(
            [("user_id", "=", self.user.id)], order="tracking_date, id"
        )
        rows[1].write({"old_value": 0})  # the reachable administrative edit
        self.env.flush_all()
        expected = self._gains()

        self._consolidate_everything()

        self.assertEqual(self._gains(), expected)
        self.user._add_karma(1, reason="a later event")
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.user.karma, expected + 1)

    def test_gain_survives_a_deleted_row(self):
        for gain in (10, 20, 30):
            self.user._add_karma(gain, reason="seed")
        self.env.flush_all()

        rows = self.Tracking.search(
            [("user_id", "=", self.user.id)], order="tracking_date, id"
        )
        rows[1].unlink()
        self.env.flush_all()
        expected = self._gains()

        self._consolidate_everything()

        self.assertEqual(self._gains(), expected)

    def test_an_intact_chain_is_untouched(self):
        """CONTROL: the normal case still collapses to one row, same total."""
        for gain in (10, 20, 30):
            self.user._add_karma(gain, reason="seed")
        self.env.flush_all()
        expected = self._gains()

        self._consolidate_everything()

        rows = self.Tracking.search([("user_id", "=", self.user.id)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(self._gains(), expected)


class TestActivityFeedRendersAtReadTime(common.TransactionCase):
    """`summary` is written once, in the writer's language and with the names
    of that day. The feed re-renders it for the reader instead of serving the
    frozen string.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.actor = mail_new_test_user(
            cls.env,
            login="feed_actor",
            name="Original Name",
            email="feed@example.com",
            groups="base.group_user",
        )
        cls.badge = cls.env["gamification.badge"].create({"name": "Original Badge"})

    def test_a_rename_reaches_the_feed(self):
        self.env["gamification.activity"]._log_badge(self.actor, self.badge)
        self.env.flush_all()

        self.actor.name = "Renamed Person"
        self.badge.name = "Renamed Badge"
        self.env.flush_all()

        feed = self.env["gamification.activity"].get_activity_feed(limit=10)
        entry = next(e for e in feed if e["user_name"] == "Renamed Person")
        self.assertIn("Renamed Person", entry["summary"])
        self.assertIn("Renamed Badge", entry["summary"])

    def test_a_row_whose_source_is_gone_keeps_its_stored_sentence(self):
        """CONTROL: `badge_id` is ondelete='set null', so the render must fall
        back rather than raise or produce a sentence with a hole in it."""
        self.env["gamification.activity"]._log_badge(self.actor, self.badge)
        self.env.flush_all()
        stored = self.env["gamification.activity"].search(
            [("user_id", "=", self.actor.id)], limit=1
        )
        original = stored.summary
        self.badge.unlink()
        stored.invalidate_recordset()

        self.assertEqual(stored._get_display_summary(), original)


class TestClosedGoalCurrentFrozen(common.TransactionCase):
    """A closed goal's ``current`` must not move on an automatic update.

    ``update_goal()`` is reachable by the goal's own (non-manager) owner
    through the always-visible "refresh" button, which writes via ``sudo()``
    to bypass the ``OUTCOME_FIELDS`` guard -- that bypass must not extend to
    re-measuring a goal that is already closed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = mail_new_test_user(
            cls.env,
            login="closed_goal_employee",
            name="Closed Goal Employee",
            email="closed_goal@example.com",
            groups="base.group_user",
        )
        # Python mode so the employee-run update_goal() below only ever needs
        # to read `compute_code` (a Char on gamification.goal.definition
        # itself, readable by group_user) rather than `model_id.model`,
        # which needs `ir.model` read access a plain employee doesn't have --
        # an unrelated, pre-existing gap outside this finding's scope.
        cls.definition = cls.env["gamification.goal.definition"].create(
            {
                "name": "Closed Goal Partners",
                "computation_mode": "python",
                "model_id": cls.env["ir.model"]._get("gamification.goal").id,
                "compute_code": "result = 999",
                "condition": "higher",
            }
        )
        cls.challenge = cls.env["gamification.challenge"].create(
            {
                "name": "Closed Goal Challenge",
                "user_domain": f'[("id", "=", {cls.employee.id})]',
                "line_ids": [
                    (0, 0, {"definition_id": cls.definition.id, "target_goal": 10**9})
                ],
            }
        )
        cls.challenge.state = "inprogress"
        cls.goal = cls.env["gamification.goal"].search(
            [
                ("challenge_id", "=", cls.challenge.id),
                ("user_id", "=", cls.employee.id),
            ]
        )

    def test_update_goal_does_not_move_current_once_closed(self):
        # Force a closed goal whose stored `current` disagrees with what a
        # fresh measurement would produce (`compute_code` always yields 999)
        # -- exactly the state a goal is in once its period has ended and
        # its measured value has since moved on.
        self.goal.sudo().write({"state": "failed", "closed": True, "current": 0})

        self.goal.with_user(self.employee).update_goal()
        self.goal.invalidate_recordset()

        self.assertEqual(self.goal.current, 0)
        self.assertEqual(self.goal.state, "failed")
        self.assertTrue(self.goal.closed)

    def test_a_still_open_goal_still_updates(self):
        """CONTROL: the refresh button must keep working for open goals."""
        self.goal.sudo().write({"current": 0})

        self.goal.with_user(self.employee).update_goal()
        self.goal.invalidate_recordset()

        self.assertEqual(self.goal.current, 999)


class TestQuestStepCrossQuestGuard(common.TransactionCase):
    """``complete_step`` must reject a step from a different quest."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            login="quest_cross_user",
            name="Quest Cross User",
            email="quest_cross@example.com",
            groups="base.group_user",
        )
        definition = cls.env["gamification.goal.definition"].create(
            {
                "name": "Cross-quest step definition",
                "computation_mode": "manually",
                "model_id": cls.env.ref("base.model_res_partner").id,
            }
        )
        cls.quest_a = cls.env["gamification.quest"].create({"name": "Quest A"})
        cls.quest_b = cls.env["gamification.quest"].create({"name": "Quest B"})
        cls.step_a = cls.env["gamification.quest.step"].create(
            {
                "quest_id": cls.quest_a.id,
                "name": "A-step",
                "sequence": 1,
                "definition_id": definition.id,
                "target_goal": 1,
            }
        )
        cls.step_b = cls.env["gamification.quest.step"].create(
            {
                "quest_id": cls.quest_b.id,
                "name": "B-step",
                "sequence": 1,
                "definition_id": definition.id,
                "target_goal": 1,
                "karma_reward": 999,
            }
        )
        cls.enrollment_a = (
            cls.env["gamification.quest.enrollment"]
            .sudo()
            .create(
                {
                    "user_id": cls.user.id,
                    "quest_id": cls.quest_a.id,
                    "state": "in_progress",
                }
            )
        )

    def test_cannot_complete_a_foreign_quests_step(self):
        karma_before = self.user.karma
        with self.assertRaises(UserError):
            self.enrollment_a.with_user(self.user).complete_step(self.step_b)

        self.user.invalidate_recordset()
        self.enrollment_a.invalidate_recordset()
        self.assertEqual(self.user.karma, karma_before)
        self.assertEqual(self.enrollment_a.state, "in_progress")

    def test_can_still_complete_its_own_quests_step(self):
        """CONTROL: the guard must not block the normal, same-quest path."""
        completion = self.enrollment_a.with_user(self.user).complete_step(self.step_a)
        self.assertTrue(completion)
        self.assertEqual(self.enrollment_a.state, "completed")


class TestQuestEnrollmentStateNotDirectlyWritable(common.TransactionCase):
    """An employee must not be able to bypass complete_step/_complete_quest
    by writing `state` on their own enrollment directly.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            login="quest_state_write_user",
            name="Quest State Write User",
            email="quest_state_write@example.com",
            groups="base.group_user",
        )
        definition = cls.env["gamification.goal.definition"].create(
            {
                "name": "State-write-guard step definition",
                "computation_mode": "manually",
                "model_id": cls.env.ref("base.model_res_partner").id,
            }
        )
        quest = cls.env["gamification.quest"].create({"name": "Guard Quest"})
        cls.env["gamification.quest.step"].create(
            {
                "quest_id": quest.id,
                "name": "Only Step",
                "sequence": 1,
                "definition_id": definition.id,
                "target_goal": 1,
            }
        )
        cls.enrollment = (
            cls.env["gamification.quest.enrollment"]
            .sudo()
            .create(
                {
                    "user_id": cls.user.id,
                    "quest_id": quest.id,
                    "state": "in_progress",
                }
            )
        )

    def test_employee_cannot_write_state_directly(self):
        with self.assertRaises(UserError):
            self.enrollment.with_user(self.user).write({"state": "completed"})
        self.enrollment.invalidate_recordset()
        self.assertEqual(self.enrollment.state, "in_progress")

    def test_sudo_can_still_write_state(self):
        """CONTROL: complete_step/_complete_quest/action_abandon rely on
        sudo() to apply the state change after their own checks pass.
        """
        self.enrollment.sudo().write({"state": "abandoned"})
        self.assertEqual(self.enrollment.state, "abandoned")


class TestKudosImmutableAfterSend(common.TransactionCase):
    """A sent kudos' recognition-defining fields must not be editable."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sender = mail_new_test_user(
            cls.env,
            login="kudos_immutable_sender",
            name="Kudos Sender",
            email="kudos_sender@example.com",
            groups="base.group_user",
        )
        cls.recipient = mail_new_test_user(
            cls.env,
            login="kudos_immutable_recipient",
            name="Kudos Recipient",
            email="kudos_recipient@example.com",
            groups="base.group_user",
        )
        cls.category_a = cls.env["gamification.kudos.category"].create(
            {"name": "Category A", "karma_granted": 10}
        )
        cls.category_b = cls.env["gamification.kudos.category"].create(
            {"name": "Category B", "karma_granted": 50}
        )
        cls.kudos = (
            cls.env["gamification.kudos"]
            .with_user(cls.sender)
            .create(
                {
                    "recipient_id": cls.recipient.id,
                    "category_id": cls.category_a.id,
                    "message": "Great work",
                }
            )
        )

    def test_owner_cannot_edit_category(self):
        with self.assertRaises(UserError):
            self.kudos.with_user(self.sender).write({"category_id": self.category_b.id})
        self.kudos.invalidate_recordset()
        self.assertEqual(self.kudos.category_id, self.category_a)
        self.assertEqual(self.kudos.karma_granted, 10)

    def test_owner_cannot_edit_recipient_or_message(self):
        for field_name, value in (
            ("recipient_id", self.sender.id),
            ("message", "edited after the fact"),
        ):
            with self.subTest(field=field_name), self.assertRaises(UserError):
                self.kudos.with_user(self.sender).write({field_name: value})

    def test_owner_cannot_edit_sender(self):
        """sender_id feeds summary exactly like the other frozen fields; a
        sudo edit must not desync summary from karma_granted/the activity
        feed/the posted message, which all still name the original sender.
        """
        with self.assertRaises(UserError):
            self.kudos.with_user(self.sender).write({"sender_id": self.recipient.id})

    def test_sudo_sender_edit_desyncs_summary(self):
        """CONTROL: a sudo() edit is still allowed (imports/migrations), but
        confirms the desync the frozen field now guards against -- summary
        re-renders while karma_granted and the activity feed do not.
        """
        activity = self.env["gamification.activity"].search(
            [
                ("activity_type", "=", "kudos"),
                ("user_id", "=", self.sender.id),
                ("target_user_id", "=", self.recipient.id),
            ],
            limit=1,
        )
        self.assertTrue(activity, "the create()-time activity row must exist")
        self.kudos.sudo().write({"sender_id": self.recipient.id})
        self.assertIn(self.recipient.name, self.kudos.summary)
        self.assertEqual(self.kudos.karma_granted, 10)
        self.assertEqual(
            activity.user_id,
            self.sender,
            "the activity feed row must keep naming the original sender",
        )

    def test_a_sudo_caller_still_can(self):
        """CONTROL: imports/migrations, not end-user edits, keep working."""
        self.kudos.sudo().write({"category_id": self.category_b.id})
        self.assertEqual(self.kudos.category_id, self.category_b)


class TestStreakConcurrentFirstVisit(common.TransactionCase):
    """Two interleaved first-visit calls must not raise on the unique index."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            login="streak_race_user",
            name="Streak Race User",
            email="streak_race@example.com",
            groups="base.group_user",
        )
        partner_model = cls.env["ir.model"]._get("res.partner")
        date_field = cls.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "write_date")],
            limit=1,
        )
        cls.streak_type = cls.env["gamification.streak.type"].create(
            {
                "name": "Race Type",
                "model_id": partner_model.id,
                "date_field_id": date_field.id,
                "domain": "[]",
            }
        )

    def test_raw_duplicate_insert_is_rejected_by_the_unique_index(self):
        """CONTROL: the constraint this guard protects against is real."""
        Streak = self.env["gamification.streak"].sudo()
        Streak.create({"user_id": self.user.id, "streak_type_id": self.streak_type.id})
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Streak.create(
                    {
                        "user_id": self.user.id,
                        "streak_type_id": self.streak_type.id,
                    }
                )

    def test_get_user_streaks_survives_a_stale_missing_read(self):
        """Simulates the race: another transaction's insert committed
        between this call's ``NOT EXISTS`` check and its own ``create()`` --
        modeled here by forcing the "missing" read to report the type as
        absent even though a row for it already exists."""
        Streak = self.env["gamification.streak"]
        Streak.sudo().create(
            {"user_id": self.user.id, "streak_type_id": self.streak_type.id}
        )

        # Only the very first `fetchall()` call is faked (the one
        # `_get_user_streaks` itself makes for its NOT EXISTS query); every
        # later call -- flush's own bookkeeping queries included -- reaches
        # the real cursor, so only the race being simulated is affected.
        cursor_cls = type(self.env.cr)
        real_fetchall = cursor_cls.fetchall
        call_count = 0

        def fake_fetchall(cr_self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(self.streak_type.id, 0)]
            return real_fetchall(cr_self)

        with patch.object(cursor_cls, "fetchall", fake_fetchall):
            result = Streak._get_user_streaks(self.user)

        self.assertEqual(len(result), 1)
        self.assertEqual(
            Streak.search_count(
                [
                    ("user_id", "=", self.user.id),
                    ("streak_type_id", "=", self.streak_type.id),
                ]
            ),
            1,
        )
