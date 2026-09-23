from unittest.mock import patch

from psycopg.errors import UniqueViolation

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common

from odoo.addons.mail.tests.common import mail_new_test_user


class TestQuest(common.TransactionCase):
    """Tests for the quest system: quests, steps, enrollments, completions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        patch_email = patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            lambda *args, **kwargs: None,
        )
        cls.startClassPatcher(patch_email)

        cls.user = mail_new_test_user(
            cls.env,
            login="quest_user",
            name="Quest User",
            email="quest@example.com",
            karma=100,
            groups="base.group_user",
        )

        cls.quest = cls.env["gamification.quest"].create(
            {
                "name": "The Data Crusade",
                "description": "<p>Clean all the data!</p>",
                "quest_mode": "solo",
                "difficulty": "intermediate",
                "reward_karma": 50,
            }
        )

        cls.step_1 = cls.env["gamification.quest.step"].create(
            {
                "quest_id": cls.quest.id,
                "name": "Step 1: Foundations",
                "sequence": 1,
                "karma_reward": 10,
            }
        )
        cls.step_2 = cls.env["gamification.quest.step"].create(
            {
                "quest_id": cls.quest.id,
                "name": "Step 2: Advanced",
                "sequence": 2,
                "prerequisite_ids": [(6, 0, [cls.step_1.id])],
                "karma_reward": 20,
            }
        )

    def test_quest_step_count(self):
        """Quest step_count reflects the number of steps."""
        self.assertEqual(self.quest.step_count, 2)

    def test_enroll_in_quest(self):
        """User can enroll in a quest."""
        enrollment = self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )
        self.assertEqual(enrollment.state, "in_progress")
        self.assertEqual(enrollment.progress_percent, 0)

    def test_complete_step(self):
        """Completing a step updates progress and grants karma."""
        enrollment = self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )
        initial_karma = self.user.karma

        enrollment.complete_step(self.step_1)

        self.assertEqual(len(enrollment.completion_ids), 1)
        self.assertEqual(enrollment.progress_percent, 50.0)
        self.assertEqual(self.user.karma, initial_karma + self.step_1.karma_reward)

    def test_prerequisite_enforcement(self):
        """Cannot complete a step before its prerequisites."""
        enrollment = self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )

        with self.assertRaises(UserError):
            enrollment.complete_step(self.step_2)

    def test_complete_with_prerequisites(self):
        """Can complete step 2 after step 1 is done."""
        enrollment = self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )
        enrollment.complete_step(self.step_1)
        enrollment.complete_step(self.step_2)

        self.assertEqual(len(enrollment.completion_ids), 2)

    def test_quest_auto_completes(self):
        """Quest auto-completes when all steps are done."""
        enrollment = self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )
        initial_karma = self.user.karma

        enrollment.complete_step(self.step_1)
        enrollment.complete_step(self.step_2)

        self.assertEqual(enrollment.state, "completed")
        # Should have step rewards + quest completion reward
        expected = (
            initial_karma
            + self.step_1.karma_reward
            + self.step_2.karma_reward
            + self.quest.reward_karma
        )
        self.assertEqual(self.user.karma, expected)

    def test_duplicate_step_completion_ignored(self):
        """Completing the same step twice returns False."""
        enrollment = self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )
        enrollment.complete_step(self.step_1)
        result = enrollment.complete_step(self.step_1)

        self.assertFalse(result)
        self.assertEqual(len(enrollment.completion_ids), 1)

    def test_self_prerequisite_prevented(self):
        """A step cannot be its own prerequisite."""
        with self.assertRaises(ValidationError):
            self.step_1.prerequisite_ids = [(6, 0, [self.step_1.id])]

    def test_abandon_quest(self):
        """User can abandon a quest."""
        enrollment = self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )
        enrollment.action_abandon()
        self.assertEqual(enrollment.state, "abandoned")

    def test_enrollment_uniqueness(self):
        """A user can only enroll once per quest."""
        self.env["gamification.quest.enrollment"].create(
            {
                "quest_id": self.quest.id,
                "user_id": self.user.id,
            }
        )
        with self.assertRaises(UniqueViolation):
            self.env["gamification.quest.enrollment"].create(
                {
                    "quest_id": self.quest.id,
                    "user_id": self.user.id,
                }
            )


class TestSeason(common.TransactionCase):
    """Tests for the seasonal events system."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        patch_email = patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            lambda *args, **kwargs: None,
        )
        cls.startClassPatcher(patch_email)

    def test_season_lifecycle(self):
        """Season transitions: draft → active → ended → archived."""
        season = self.env["gamification.season"].create(
            {
                "name": "Q1 Sprint",
                "start_date": "2026-01-01",
                "end_date": "2026-03-31",
            }
        )
        self.assertEqual(season.state, "draft")

        season.action_activate()
        self.assertEqual(season.state, "active")

        season.action_end()
        self.assertEqual(season.state, "ended")

        season.action_archive()
        self.assertEqual(season.state, "archived")

    def test_season_leaderboard(self):
        """Season leaderboard returns karma earned during the window, sorted."""
        user_a = mail_new_test_user(
            self.env,
            login="season_a",
            name="Season User A",
            email="season_a@example.com",
            karma=0,
            groups="base.group_user",
        )
        user_b = mail_new_test_user(
            self.env,
            login="season_b",
            name="Season User B",
            email="season_b@example.com",
            karma=0,
            groups="base.group_user",
        )
        # Grant karma so tracking records exist within the season window
        user_a._add_karma(50, source=user_a, reason="test")
        user_b._add_karma(100, source=user_b, reason="test")

        season = self.env["gamification.season"].create(
            {
                "name": "Test Season",
                "start_date": "2020-01-01",
                "end_date": "2030-12-31",
            }
        )
        result = season.get_season_leaderboard(limit=5)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 2, "Leaderboard should include both users")
        # Verify sorted by karma descending
        karmas = [r["season_karma"] for r in result]
        self.assertEqual(karmas, sorted(karmas, reverse=True))

    def test_season_leaderboard_empty(self):
        """Season leaderboard returns empty list when no karma in window."""
        season = self.env["gamification.season"].create(
            {
                "name": "Empty Season",
                "start_date": "1990-01-01",
                "end_date": "1990-12-31",
            }
        )
        result = season.get_season_leaderboard(limit=5)
        self.assertEqual(result, [])


class TestSkillTree(common.TransactionCase):
    """Tests for the skill tree system."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        patch_email = patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            lambda *args, **kwargs: None,
        )
        cls.startClassPatcher(patch_email)

        cls.user = mail_new_test_user(
            cls.env,
            login="skill_user",
            name="Skill User",
            email="skill@example.com",
            karma=200,
            groups="base.group_user",
        )

        cls.tree = cls.env["gamification.skill.tree"].create(
            {
                "name": "Sales Mastery",
            }
        )
        cls.node_root = cls.env["gamification.skill.node"].create(
            {
                "tree_id": cls.tree.id,
                "name": "Sales Basics",
                "level": 1,
                "karma_reward": 15,
            }
        )
        cls.node_advanced = cls.env["gamification.skill.node"].create(
            {
                "tree_id": cls.tree.id,
                "name": "Advanced Negotiation",
                "level": 2,
                "prerequisite_ids": [(6, 0, [cls.node_root.id])],
                "karma_threshold": 100,
                "karma_reward": 30,
            }
        )

    def test_tree_node_count(self):
        """Tree node_count reflects the number of nodes."""
        self.assertEqual(self.tree.node_count, 2)

    def test_unlock_root_node(self):
        """User can unlock a root node with no prerequisites."""
        result = self.node_root.unlock_for_user(self.user)
        self.assertTrue(result)

        # Verify unlock exists
        unlocks = self.env["gamification.skill.node.unlock"].search(
            [
                ("node_id", "=", self.node_root.id),
                ("user_id", "=", self.user.id),
            ]
        )
        self.assertEqual(len(unlocks), 1)

    def test_unlock_grants_karma(self):
        """Unlocking a node grants karma reward."""
        initial_karma = self.user.karma
        self.node_root.unlock_for_user(self.user)
        self.assertEqual(self.user.karma, initial_karma + self.node_root.karma_reward)

    def test_cannot_unlock_without_prerequisites(self):
        """Cannot unlock a node without completing prerequisites."""
        result = self.node_advanced.unlock_for_user(self.user)
        self.assertFalse(result)

    def test_unlock_with_prerequisites(self):
        """Can unlock advanced node after root is done."""
        self.node_root.unlock_for_user(self.user)
        result = self.node_advanced.unlock_for_user(self.user)
        self.assertTrue(result)

    def test_cannot_unlock_below_karma_threshold(self):
        """Cannot unlock a node if karma is below threshold."""
        low_karma_user = mail_new_test_user(
            self.env,
            login="low_karma",
            name="Low Karma",
            email="low@example.com",
            karma=10,
            groups="base.group_user",
        )
        # Root has no threshold, should work
        self.node_root.unlock_for_user(low_karma_user)
        # Advanced requires 100 karma, should fail
        result = self.node_advanced.unlock_for_user(low_karma_user)
        self.assertFalse(result)

    def test_duplicate_unlock_prevented(self):
        """Cannot unlock the same node twice."""
        self.node_root.unlock_for_user(self.user)
        result = self.node_root.unlock_for_user(self.user)
        self.assertFalse(result)

    def test_dependent_nodes_computed(self):
        """dependent_ids shows what this node unlocks."""
        self.assertIn(self.node_advanced, self.node_root.dependent_ids)
