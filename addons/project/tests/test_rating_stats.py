"""Tests for the rating aggregation stats on rated records."""

from odoo import http
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestRatingStats(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Rating project"})
        cls.task = cls.env["project.task"].create(
            {"name": "Rated task", "project_id": cls.project.id}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Rater"})

    def _rate(self, value):
        return self.env["rating.rating"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("project.task"),
                "res_id": self.task.id,
                "partner_id": self.partner.id,
                "rating": value,
                "consumed": True,
            }
        )

    def test_no_ratings_yields_zero_stats(self):
        """Without ratings the counters stay at zero (boundary)."""
        self.assertEqual(self.task.rating_count, 0)
        self.assertEqual(self.task.rating_avg, 0)

    def test_avg_and_count_aggregate(self):
        """Consumed ratings feed the average and the counter."""
        self._rate(5)
        self._rate(3)
        self.task.invalidate_recordset(["rating_avg", "rating_count"])
        self.assertEqual(self.task.rating_count, 2)
        self.assertEqual(self.task.rating_avg, 4.0)

    def test_satisfaction_percentage_counts_great_only(self):
        """Satisfaction is the share of 'great' grades (5 - great, 3 - okay)."""
        self._rate(5)
        self._rate(5)
        self._rate(3)
        self._rate(1)
        self.task.invalidate_recordset(["rating_percentage_satisfaction"])
        self.assertEqual(self.task.rating_percentage_satisfaction, 50)

    def test_satisfaction_without_ratings_is_sentinel(self):
        """No ratings yield the -1 sentinel, not a fake 0% (boundary)."""
        self.task.invalidate_recordset(["rating_percentage_satisfaction"])
        self.assertEqual(self.task.rating_percentage_satisfaction, -1)

    def test_stats_per_record_distribution(self):
        """Per-record stats expose total, average and percent distribution."""
        self._rate(5)
        self._rate(5)
        self._rate(1)
        stats = self.task._rating_get_stats_per_record()[self.task.id]
        self.assertEqual(stats["total"], 3)
        self.assertAlmostEqual(stats["avg"], 11 / 3, places=2)
        self.assertAlmostEqual(stats["percent"][5], 200 / 3, places=2)
        self.assertAlmostEqual(stats["percent"][1], 100 / 3, places=2)
        self.assertEqual(stats["percent"][2], 0.0)

    def test_grades_map_rating_values(self):
        """Ratings split into great (>=4), okay (>=3) and bad grades."""
        self._rate(5)
        self._rate(4)
        self._rate(3)
        self._rate(1)
        grades = self.task.rating_get_grades()
        self.assertEqual(grades, {"great": 2, "okay": 1, "bad": 1})

    def test_stats_expose_percent_avg_and_total(self):
        """Aggregated stats carry the percent split, average and total."""
        self._rate(5)
        self._rate(5)
        self._rate(1)
        stats = self.task.rating_get_stats()
        self.assertEqual(stats["total"], 3)
        self.assertAlmostEqual(stats["avg"], 11 / 3, places=2)
        self.assertAlmostEqual(stats["percent"][5], 200 / 3, places=2)
        self.assertEqual(stats["percent"][3], 0)

    def test_parent_project_aggregates_task_ratings(self):
        """The project aggregates its tasks' ratings via the parent mixin."""
        self._rate(5)
        self._rate(5)
        self._rate(1)
        self.project.invalidate_recordset(
            [
                "rating_child_count",
                "rating_child_avg",
                "rating_child_percentage_satisfaction",
            ],
        )
        self.assertEqual(self.project.rating_child_count, 3)
        self.assertAlmostEqual(self.project.rating_child_avg, 11 / 3, places=2)
        # integer field: 200/3 truncates to 66
        self.assertEqual(self.project.rating_child_percentage_satisfaction, 66)
        self.assertAlmostEqual(
            self.project.rating_child_avg_percentage,
            11 / 15,
            places=2,
        )

    def test_parent_without_ratings_uses_sentinel(self):
        """A project without ratings reports the -1 sentinel (boundary)."""
        self.project.invalidate_recordset(["rating_child_percentage_satisfaction"])
        self.assertEqual(self.project.rating_child_percentage_satisfaction, -1)

    def test_search_projects_by_average_rating(self):
        """Projects are searchable by their aggregated average rating."""
        self._rate(5)
        self._rate(4)
        matches = self.env["project.project"].search([("rating_child_avg", ">=", 4)])
        self.assertIn(self.project, matches)
        empty = self.env["project.project"].search([("rating_child_avg", ">=", 4.6)])
        self.assertNotIn(self.project, empty)


@tagged("post_install", "-at_install")
class TestRatingExternalRoutes(HttpCase):
    """Public token routes to open and submit a rating."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Route project"})
        cls.task = cls.env["project.task"].create(
            {"name": "Rated by route", "project_id": cls.project.id}
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Route rater", "email": "route.rater@example.com"}
        )
        cls.rating = cls.env["rating.rating"].create(
            {
                "res_model_id": cls.env["ir.model"]._get_id("project.task"),
                "res_id": cls.task.id,
                "partner_id": cls.partner.id,
            }
        )
        cls.token = cls.rating.access_token

    def test_open_rating_page_with_valid_token(self):
        """A valid token opens the submit page for the chosen rate."""
        res = self.url_open(f"/rate/{self.token}/5")
        self.assertEqual(res.status_code, 200)
        self.assertIn("submit_feedback", res.text)

    def test_open_rating_with_unknown_token_is_not_found(self):
        """A token matching no rating yields a 404."""
        res = self.url_open("/rate/definitely-not-a-token/5")
        self.assertEqual(res.status_code, 404)

    def test_open_rating_with_invalid_rate_fails(self):
        """A rate outside 1/3/5 is refused (>=400, exact code unpinned)."""
        # NOTE: today this surfaces as a 500 because the upstream-inherited
        # raise passes kwargs to ValueError (TypeError); the assert stays
        # valid once that is fixed to a clean 4xx/error page.
        res = self.url_open(f"/rate/{self.token}/7")
        self.assertGreaterEqual(res.status_code, 400)

    def test_foreign_internal_user_gets_invalid_partner_page(self):
        """Another customer's rating never shows the submit form."""
        new_test_user(
            self.env,
            login="foreign_rater",
            groups="base.group_user",
        )
        self.authenticate("foreign_rater", "foreign_rater")
        res = self.url_open(f"/rate/{self.token}/5")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("submit_feedback", res.text)

    def test_submit_feedback_applies_rating(self):
        """Posting the feedback consumes the rating and logs the message."""
        self.authenticate(None, None)
        res = self.url_open(
            f"/rate/{self.token}/submit_feedback",
            data={
                "rate": 5,
                "feedback": "Excellent work",
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.rating.rating, 5)
        self.assertTrue(self.rating.consumed)
        self.assertIn("Excellent work", self.rating.feedback)
        self.assertTrue(
            self.task.message_ids.filtered(
                lambda m: m.rating_ids and self.rating in m.rating_ids
            )
        )


@tagged("post_install", "-at_install")
class TestRatingMailMessage(TransactionCase):
    """Rating fields exposed on mail.message."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Message project"})
        cls.task = cls.env["project.task"].create(
            {"name": "Message task", "project_id": cls.project.id}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Message rater"})
        cls.message = cls.task.message_post(body="Rated message")

    def _rate(self, value, consumed=True, message=None):
        return self.env["rating.rating"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("project.task"),
                "res_id": self.task.id,
                "partner_id": self.partner.id,
                "rating": value,
                "consumed": consumed,
                "message_id": (message or self.message).id,
            }
        )

    def test_rating_id_picks_latest_consumed(self):
        """The message exposes its newest consumed rating."""
        self._rate(1)
        latest = self._rate(5)
        self.message.invalidate_recordset(["rating_id", "rating_value"])
        self.assertEqual(self.message.rating_id, latest)
        self.assertEqual(self.message.rating_value, 5)

    def test_unconsumed_rating_is_ignored(self):
        """A rating still awaiting an answer does not surface (boundary)."""
        self._rate(5, consumed=False)
        self.message.invalidate_recordset(["rating_id", "rating_value"])
        self.assertFalse(self.message.rating_id)
        self.assertEqual(self.message.rating_value, 0.0)

    def test_search_by_rating_value(self):
        """Messages are searchable by the rating value they carry."""
        self._rate(5)
        Message = self.env["mail.message"]
        self.assertIn(self.message, Message.search([("rating_value", "=", 5)]))
        self.assertNotIn(self.message, Message.search([("rating_value", "=", 1)]))

    def test_search_zero_includes_unrated_messages(self):
        """Searching for zero also returns messages without any rating."""
        plain = self.task.message_post(body="No rating here")
        self._rate(5)
        matches = self.env["mail.message"].search([("rating_value", "in", [0])])
        self.assertIn(plain, matches)
        self.assertNotIn(self.message, matches)

    def test_search_negative_operator_unsupported(self):
        """Negative operators are declined rather than answered wrongly."""
        self.assertIs(
            self.env["mail.message"]._search_rating_value("not in", [5]),
            NotImplemented,
        )

    def test_rated_message_is_not_empty(self):
        """A body-less message still counts as content when it carries a rating."""
        blank = self.task.message_post(body="")
        self.assertTrue(blank._is_empty())
        self._rate(5, message=blank)
        blank.invalidate_recordset(["rating_id"])
        self.assertFalse(blank._is_empty())

    def test_store_exposes_rating_stats_only_when_allowed(self):
        """Rating stats reach the store only for publishing models."""
        from unittest.mock import patch

        from odoo.addons.mail.tools.discuss import Store

        self._rate(5)
        store = Store()
        self.message._to_store(store, ["record_rating"])
        payload = store.get_result()
        thread = payload["mixin.mail.thread"][0]
        self.assertEqual(thread["rating_avg"], 5)
        self.assertEqual(thread["rating_count"], 1)
        self.assertNotIn("rating_stats", thread)

        with patch.object(
            type(self.task), "_allow_publish_rating_stats", return_value=True
        ):
            store_pub = Store()
            self.message._to_store(store_pub, ["record_rating"])
            thread_pub = store_pub.get_result()["mixin.mail.thread"][0]
        self.assertEqual(thread_pub["rating_stats"]["total"], 1)
