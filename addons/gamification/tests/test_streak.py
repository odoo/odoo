from datetime import date, timedelta
from unittest.mock import patch

from freezegun import freeze_time
from psycopg.errors import UniqueViolation

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, common

from odoo.addons.mail.tests.common import mail_new_test_user


class TestStreakCommon(common.TransactionCase):
    """Common setup for streak tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Patch send_mail to avoid actual email sending
        patch_email = patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            lambda *args, **kwargs: None,
        )
        cls.startClassPatcher(patch_email)

        cls.test_user = mail_new_test_user(
            cls.env,
            login="streak_user",
            name="Streak User",
            email="streak@example.com",
            karma=0,
            groups="base.group_user",
        )
        # Use res.partner as the target model — universally available
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.date_field = cls.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "write_date")],
            limit=1,
        )

        cls.streak_type = cls.env["gamification.streak.type"].create(
            {
                "name": "Daily Partner Update",
                "model_id": cls.partner_model.id,
                "date_field_id": cls.date_field.id,
                "domain": "[('create_uid', '=', user.id)]",
                "karma_bonus": 10,
                "freeze_allowance": 2,
            }
        )


class TestStreak(TestStreakCommon):
    """Tests for the gamification streak system."""

    def setUp(self):
        super().setUp()
        # Clean up any pre-existing streaks for the test user to avoid
        # unique constraint violations from other tests or setup logic
        self.env["gamification.streak"].search(
            [
                ("user_id", "=", self.test_user.id),
            ]
        ).unlink()

    def test_streak_type_form_resolves_its_domain_model(self):
        self.assertEqual(self.streak_type.model_name, "res.partner")
        form = Form(self.env["gamification.streak.type"])
        self.assertFalse(form.model_name)
        form.model_id = self.partner_model
        self.assertEqual(form.model_name, "res.partner")

    def test_get_user_streaks_creates_missing(self):
        """_get_user_streaks creates streak records for all active types."""
        Streak = self.env["gamification.streak"]
        # Clear any existing streaks for test user
        Streak.search([("user_id", "=", self.test_user.id)]).unlink()

        Streak._get_user_streaks(self.test_user)

        streaks = Streak.search([("user_id", "=", self.test_user.id)])
        active_types = self.env["gamification.streak.type"].search(
            [("active", "=", True)]
        )
        self.assertEqual(
            len(streaks),
            len(active_types),
            "Should create one streak per active type",
        )

    def test_get_user_streaks_idempotent(self):
        """Calling _get_user_streaks twice does not duplicate records."""
        Streak = self.env["gamification.streak"]
        Streak.search([("user_id", "=", self.test_user.id)]).unlink()

        Streak._get_user_streaks(self.test_user)
        count_1 = Streak.search_count([("user_id", "=", self.test_user.id)])

        Streak._get_user_streaks(self.test_user)
        count_2 = Streak.search_count([("user_id", "=", self.test_user.id)])

        self.assertEqual(count_1, count_2, "Second call should not create duplicates")

    def test_record_activity_increments_count(self):
        """_record_activity increments current_count and sets last_activity_date."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        self.assertEqual(streak.current_count, 0)

        streak._record_activity()

        self.assertEqual(streak.current_count, 1)
        self.assertEqual(streak.last_activity_date, fields.Date.today())
        self.assertEqual(streak.longest_count, 1)

    def test_record_activity_idempotent_same_day(self):
        """Recording activity twice on the same day does not double-count."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        streak._record_activity()
        streak._record_activity()

        self.assertEqual(streak.current_count, 1, "Should not count same day twice")

    def test_record_activity_rejects_mixed_streak_types_for_one_user(self):
        """_record_activity's karma_per_user is keyed by user_id alone: two
        different-type streaks for the same user in one call would silently
        misattribute source/reason to whichever streak came first. The sole
        production caller can't reach this (it groups by streak_type_id
        first), but a direct call with a mixed recordset must raise rather
        than silently misattribute.
        """
        other_streak_type = self.env["gamification.streak.type"].create(
            {
                "name": "Other Streak Type",
                "model_id": self.partner_model.id,
                "date_field_id": self.date_field.id,
                "domain": "[('create_uid', '=', user.id)]",
                "karma_bonus": 5,
                "freeze_allowance": 2,
            }
        )
        streak_a = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        streak_b = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": other_streak_type.id,
                "freeze_remaining": other_streak_type.freeze_allowance,
            }
        )
        with self.assertRaises(UserError):
            (streak_a | streak_b)._record_activity()

    def test_record_activity_grants_karma(self):
        """Daily streak activity grants karma bonus."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        initial_karma = self.test_user.karma

        streak._record_activity()

        self.assertEqual(
            self.test_user.karma,
            initial_karma + self.streak_type.karma_bonus,
        )
        self.assertEqual(streak.total_karma_earned, self.streak_type.karma_bonus)

    def test_milestone_karma_multiplier(self):
        """Milestone days (7, 30, 100, 365) multiply the karma bonus."""
        from odoo.addons.gamification.models.gamification_streak import (
            STREAK_MILESTONES,
        )

        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
                "current_count": 6,  # next activity will be day 7
                "longest_count": 6,
            }
        )
        # Override readonly by writing directly
        streak.env.cr.execute(
            "UPDATE gamification_streak SET current_count = 6, longest_count = 6 WHERE id = %s",
            [streak.id],
        )
        streak.invalidate_recordset()
        initial_karma = self.test_user.karma

        # Use a different day so last_activity_date doesn't block
        with freeze_time("2026-04-01"):
            streak._record_activity()

        expected_multiplier = STREAK_MILESTONES[7]
        expected_karma = self.streak_type.karma_bonus * expected_multiplier
        self.assertEqual(
            self.test_user.karma,
            initial_karma + expected_karma,
            f"Day 7 milestone should grant {expected_multiplier}x karma",
        )

    def test_break_streak_resets_count(self):
        """Breaking a streak resets current_count but preserves longest_count."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        # Simulate a 5-day streak
        streak.env.cr.execute(
            "UPDATE gamification_streak SET current_count = 5, longest_count = 5 WHERE id = %s",
            [streak.id],
        )
        streak.invalidate_recordset()

        streak._break_streak()

        self.assertEqual(streak.current_count, 0)
        self.assertEqual(streak.state, "broken")
        self.assertEqual(streak.longest_count, 5, "Longest should be preserved")

    def test_record_activity_revives_broken_streak(self):
        """Recording activity on a broken streak revives it."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        streak._break_streak()
        self.assertEqual(streak.state, "broken")

        streak._record_activity()

        self.assertEqual(streak.state, "active")
        self.assertEqual(streak.current_count, 1)

    def test_cron_freeze_day_used(self):
        """Cron uses a freeze day when no activity is found, instead of breaking."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": 2,
            }
        )
        # Set a past activity date so the cron picks it up
        streak.env.cr.execute(
            "UPDATE gamification_streak SET current_count = 3, last_activity_date = %s WHERE id = %s",
            [date.today() - timedelta(days=2), streak.id],
        )
        streak.invalidate_recordset()

        # No activity yesterday, so freeze should be used
        with patch.object(
            type(self.streak_type),
            "_check_user_activity_batch",
            side_effect=lambda users, check_date: set(),
        ):
            self.env["gamification.streak"]._cron_update_streaks()

        streak.invalidate_recordset()
        self.assertEqual(streak.state, "active", "Should still be active after freeze")
        self.assertEqual(streak.freeze_remaining, 1, "One freeze day should be used")

    def test_cron_breaks_streak_no_freeze(self):
        """Cron breaks the streak when no activity and no freeze days left."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": 0,
            }
        )
        streak.env.cr.execute(
            "UPDATE gamification_streak SET current_count = 3, last_activity_date = %s WHERE id = %s",
            [date.today() - timedelta(days=2), streak.id],
        )
        streak.invalidate_recordset()

        with patch.object(
            type(self.streak_type),
            "_check_user_activity_batch",
            side_effect=lambda users, check_date: set(),
        ):
            self.env["gamification.streak"]._cron_update_streaks()

        streak.invalidate_recordset()
        self.assertEqual(streak.state, "broken")
        self.assertEqual(streak.current_count, 0)

    def test_cron_records_activity_when_found(self):
        """Cron records activity when the batch check reports the user active."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": 2,
            }
        )
        streak.env.cr.execute(
            "UPDATE gamification_streak SET current_count = 3, last_activity_date = %s WHERE id = %s",
            [date.today() - timedelta(days=2), streak.id],
        )
        streak.invalidate_recordset()

        with patch.object(
            type(self.streak_type),
            "_check_user_activity_batch",
            side_effect=lambda users, check_date: set(users.ids),
        ):
            self.env["gamification.streak"]._cron_update_streaks()

        streak.invalidate_recordset()
        self.assertEqual(streak.state, "active")
        self.assertEqual(streak.current_count, 4)

    @freeze_time("2026-04-01")
    def test_cron_resets_freeze_on_first_of_month(self):
        """Freeze allowance is reset on the 1st of each month."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": 0,
            }
        )
        streak.env.cr.execute(
            "UPDATE gamification_streak SET last_activity_date = %s WHERE id = %s",
            [date(2026, 3, 31), streak.id],
        )
        streak.invalidate_recordset()

        with patch.object(
            type(self.streak_type),
            "_check_user_activity_batch",
            side_effect=lambda users, check_date: set(users.ids),
        ):
            self.env["gamification.streak"]._cron_update_streaks()

        streak.invalidate_recordset()
        self.assertEqual(
            streak.freeze_remaining,
            self.streak_type.freeze_allowance,
            "Freeze should be reset on 1st of month",
        )

    def test_unique_constraint_user_streak_type(self):
        """A user can only have one streak per type (unique constraint)."""
        self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        with self.assertRaises(UniqueViolation):
            self.env["gamification.streak"].create(
                {
                    "user_id": self.test_user.id,
                    "streak_type_id": self.streak_type.id,
                    "freeze_remaining": self.streak_type.freeze_allowance,
                }
            )

    def test_streak_type_user_count(self):
        """Streak type user_count reflects active streaks."""
        user2 = mail_new_test_user(
            self.env,
            login="streak_user2",
            name="Streak User 2",
            email="streak2@example.com",
            karma=0,
            groups="base.group_user",
        )
        self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        s2 = self.env["gamification.streak"].create(
            {
                "user_id": user2.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        self.streak_type.invalidate_recordset(["user_count"])
        self.assertEqual(self.streak_type.user_count, 2)

        s2._break_streak()
        self.streak_type.invalidate_recordset(["user_count"])
        self.assertEqual(
            self.streak_type.user_count, 1, "Broken streaks should not count"
        )

    def test_get_user_streaks_as_employee(self):
        """_get_user_streaks works for employees who lack create permission.

        Regression: employees have perm_create=0 on gamification.streak.
        The method uses sudo() internally so the dashboard doesn't crash.
        """
        Streak = self.env["gamification.streak"]
        Streak.search([("user_id", "=", self.test_user.id)]).unlink()

        # Call as the employee user (group_user only, no erp_manager)
        Streak.with_user(self.test_user)._get_user_streaks(self.test_user)

        streaks = Streak.search([("user_id", "=", self.test_user.id)])
        active_types = self.env["gamification.streak.type"].search(
            [("active", "=", True)]
        )
        self.assertEqual(
            len(streaks),
            len(active_types),
            "Employee should be able to create streaks via _get_user_streaks",
        )

    def test_cron_revives_broken_streak_on_activity(self):
        """Cron revives a broken streak when the user performed qualifying activity.

        Regression: the cron previously only checked state='active', so broken
        streaks could never be revived even when _record_activity supports it.
        """
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": 0,
            }
        )
        streak._break_streak()
        self.assertEqual(streak.state, "broken")
        self.assertEqual(streak.current_count, 0)

        # Simulate: user was active yesterday
        with patch.object(
            type(self.streak_type),
            "_check_user_activity_batch",
            side_effect=lambda users, check_date: set(users.ids),
        ):
            self.env["gamification.streak"]._cron_update_streaks()

        streak.invalidate_recordset()
        self.assertEqual(
            streak.state, "active", "Broken streak should revive on activity"
        )
        self.assertEqual(streak.current_count, 1)

    @freeze_time("2026-04-01")
    def test_cron_revival_gets_this_months_freeze_reset(self):
        """A broken streak revived in the same run still gets the monthly reset.

        Regression: the monthly freeze-day reset only queried
        state='active' streaks. On the 1st of the month, a streak that was
        'broken' at the start of this same cron run -- but qualifies for
        activity and gets revived to 'active' later in the very same call --
        never got that month's freeze allowance, because the reset ran and
        finished before the revival happened.
        """
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": 0,
            }
        )
        streak._break_streak()
        self.assertEqual(streak.state, "broken")

        with patch.object(
            type(self.streak_type),
            "_check_user_activity_batch",
            side_effect=lambda users, check_date: set(users.ids),
        ):
            self.env["gamification.streak"]._cron_update_streaks()

        streak.invalidate_recordset()
        self.assertEqual(
            streak.state, "active", "Broken streak should revive on activity"
        )
        self.assertEqual(
            streak.freeze_remaining,
            self.streak_type.freeze_allowance,
            "A streak revived on the 1st of the month should still receive "
            "that month's freeze allowance",
        )

    def test_cron_does_not_rebreak_broken_streak(self):
        """Cron leaves broken streaks alone when there's no activity.

        Broken streaks without activity yesterday should not waste freeze days
        or trigger redundant _break_streak calls.
        """
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": 2,
            }
        )
        streak._break_streak()
        self.assertEqual(streak.state, "broken")

        with patch.object(
            type(self.streak_type),
            "_check_user_activity_batch",
            side_effect=lambda users, check_date: set(),
        ):
            self.env["gamification.streak"]._cron_update_streaks()

        streak.invalidate_recordset()
        self.assertEqual(streak.state, "broken")
        self.assertEqual(
            streak.freeze_remaining,
            2,
            "Freeze days should not be consumed on broken streaks",
        )

    def test_display_name(self):
        """Display name shows streak type name and day count."""
        streak = self.env["gamification.streak"].create(
            {
                "user_id": self.test_user.id,
                "streak_type_id": self.streak_type.id,
                "freeze_remaining": self.streak_type.freeze_allowance,
            }
        )
        self.assertIn("0 days", streak.display_name)
        self.assertIn(self.streak_type.name, streak.display_name)

    def test_domain_not_referencing_user_is_accepted_as_a_shared_streak(self):
        """A domain that never mentions 'user' is a deliberate shape, not an error.

        `_check_user_activity_batch` groups candidates by their *evaluated*
        domain: every candidate whose domain does not reference `user` at
        all evaluates to the same text, so they share one query and its
        answer -- a company-wide/shared streak (e.g. "did anyone log a
        sale today") rather than a per-user one. That is intentional and
        must keep working (existing fixtures rely on it, e.g.
        TestCronErrorIsolation's "Good Streak"/"Good Achievement"), so this
        only pins the field's help text calling the shape out, rather than
        rejecting it -- a hard validation was tried and reverted because it
        broke that legitimate usage.
        """
        streak_type = self.env["gamification.streak.type"].create(
            {
                "name": "Global Domain Streak",
                "model_id": self.partner_model.id,
                "date_field_id": self.date_field.id,
                "domain": "[('active', '=', True)]",
            }
        )
        self.assertTrue(streak_type)
        self.assertIn(
            "credited",
            self.env["gamification.streak.type"]._fields["domain"].help,
            "the domain field must document the shared-query caveat for a "
            "domain that never references 'user'",
        )

    def test_domain_referencing_user_is_accepted(self):
        """A domain that does reference 'user' saves without error."""
        streak_type = self.env["gamification.streak.type"].create(
            {
                "name": "Per-User Domain Streak",
                "model_id": self.partner_model.id,
                "date_field_id": self.date_field.id,
                "domain": "[('create_uid', '=', user.id)]",
            }
        )
        self.assertTrue(streak_type)
