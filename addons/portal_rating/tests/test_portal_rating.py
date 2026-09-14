import logging

from markupsafe import Markup

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPortalRating(TransactionCase):
    def test_rating_metadata_queries_remain_batched(self):
        messages = self.Message.create(
            [{"body": f"Rated message {index}"} for index in range(30)]
        )
        ratings = self.Rating.create(
            [
                {
                    "message_id": message.id,
                    "rating": 5,
                    "consumed": True,
                    "res_model_id": self.env["ir.model"]._get("res.partner").id,
                    "res_id": self.env.user.partner_id.id,
                }
                for message in messages
            ]
        )
        expected = {rating.message_id.id: rating.id for rating in ratings}
        messages.portal_message_format(options={"rating_include": True})
        costs = []
        for batch in (messages[:3], messages):
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            values = batch.portal_message_format(options={"rating_include": True})
            costs.append(self.env.cr.sql_statement_count - before)
            for value in values:
                self.assertEqual(value["rating_id"]["id"], expected[value["id"]])
        _logger.debug("Rating metadata SQL for 3/30 messages: %s", costs)
        self.assertLessEqual(costs[1], costs[0] + 2)

    def test_format_uses_the_same_consumed_rating_as_the_message_value(self):
        message = self.Message.create({"body": "Multiple ratings"})
        rating_vals = {
            "message_id": message.id,
            "res_model_id": self.env["ir.model"]._get("res.partner").id,
            "res_id": self.env.user.partner_id.id,
        }
        older, newer, pending = self.Rating.create(
            [
                {**rating_vals, "rating": 1, "consumed": True},
                {**rating_vals, "rating": 5, "consumed": True},
                {**rating_vals, "rating": 3, "consumed": False},
            ]
        )
        # Distinct dates make the intended chronology independent of transaction time.
        self.env.cr.execute(
            "UPDATE rating_rating SET create_date = %s WHERE id = %s",
            ("2026-09-12 10:00:00", older.id),
        )
        self.env.cr.execute(
            "UPDATE rating_rating SET create_date = %s WHERE id = %s",
            ("2026-09-13 10:00:00", newer.id),
        )
        (older | newer | pending).invalidate_recordset(["create_date"])
        message.invalidate_recordset(["rating_id", "rating_value"])
        self.assertEqual(message.rating_id, newer)
        values = message.portal_message_format(options={"rating_include": True})[0]
        _logger.debug(
            "Selected rating=%s formatted rating=%s value=%s",
            message.rating_id.id,
            values["rating_id"].get("id"),
            values["rating_value"],
        )
        self.assertEqual(values["rating_value"], 5)
        self.assertEqual(values["rating_id"]["id"], newer.id)

    def test_unconsumed_rating_has_no_published_metadata(self):
        message = self.Message.create({"body": "Pending rating"})
        self.Rating.create(
            {
                "message_id": message.id,
                "rating": 4,
                "consumed": False,
                "res_model_id": self.env["ir.model"]._get("res.partner").id,
                "res_id": self.env.user.partner_id.id,
            }
        )
        values = message.portal_message_format(options={"rating_include": True})[0]
        _logger.debug("Pending rating format=%s", values)
        self.assertEqual(values["rating_value"], 0)
        self.assertEqual(values["rating_id"], {})

    def test_rating_format_keeps_linked_message_references(self):
        partner = self.env["res.partner"].create({"name": "Rated thread"})
        linked = self.Message.create(
            {
                "body": "Referenced message",
                "model": partner._name,
                "res_id": partner.id,
                "message_type": "comment",
            }
        )
        message = self.Message.create(
            {
                "body": Markup(
                    '<a class="o_message_redirect" data-oe-model="mail.message" data-oe-id="%s">Reference</a>'
                )
                % linked.id,
                "model": partner._name,
                "res_id": partner.id,
                "message_type": "comment",
            }
        )
        rating = self.Rating.create(
            {
                "res_model_id": self.env["ir.model"]._get(partner._name).id,
                "res_id": partner.id,
                "message_id": message.id,
                "rating": 5,
                "consumed": True,
            }
        )
        values = message.portal_message_format(options={"rating_include": True})
        _logger.debug(
            "Rating format original=%s returned ids=%s",
            message.ids,
            [value["id"] for value in values],
        )
        by_id = {value["id"]: value for value in values}
        self.assertEqual(set(by_id), {message.id, linked.id})
        self.assertEqual(by_id[message.id]["rating_id"]["id"], rating.id)
        self.assertNotIn("rating_id", by_id[linked.id])

    def test_rating_format_tolerates_an_uninstalled_thread_model(self):
        message = self.Message.create({"body": "Orphaned thread"})
        self.env.cr.execute(
            "UPDATE mail_message SET model = %s, res_id = %s WHERE id = %s",
            ("x.module.was.uninstalled", 1, message.id),
        )
        message.invalidate_recordset(["model", "res_id"])
        values = message.portal_message_format(options={"rating_include": True})[0]
        _logger.debug("Orphaned rating format keys=%s", sorted(values))
        self.assertEqual(values["id"], message.id)
        self.assertFalse(values["thread"]["has_mail_thread"])
        self.assertNotIn("rating_stats", values)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Message = cls.env["mail.message"]
        cls.Rating = cls.env["rating.rating"]

    def test_format_properties_exclude_rating_by_default(self):
        """Rating fields are not requested unless the caller opts in."""
        names = self.Message._portal_get_default_format_properties_names()
        self.assertNotIn("rating", names)

    def test_format_properties_include_rating_on_option(self):
        """The rating_include option adds the rating fields to the request."""
        names = self.Message._portal_get_default_format_properties_names(
            options={"rating_include": True}
        )
        self.assertIn("rating", names)
        self.assertIn("rating_value", names)

    def test_format_rating_with_publisher(self):
        """A rating with a publisher exposes the avatar, name, and comment."""
        formatted = self.Message._portal_message_format_rating(
            {
                "publisher_id": [7, "Bob"],
                "publisher_comment": "Thanks!",
                "publisher_datetime": fields.Datetime.now(),
            }
        )
        self.assertEqual(formatted["publisher_id"], 7)
        self.assertEqual(formatted["publisher_name"], "Bob")
        self.assertEqual(formatted["publisher_comment"], "Thanks!")
        self.assertEqual(
            formatted["publisher_avatar"],
            "/web/image/res.partner/7/avatar_128/50x50",
        )

    def test_format_rating_without_publisher(self):
        """A rating with no publisher blanks the avatar, name, and comment."""
        formatted = self.Message._portal_message_format_rating(
            {
                "publisher_id": False,
                "publisher_comment": False,
                "publisher_datetime": False,
            }
        )
        self.assertEqual(formatted["publisher_id"], False)
        self.assertEqual(formatted["publisher_name"], "")
        self.assertEqual(formatted["publisher_comment"], "")
        self.assertEqual(formatted["publisher_avatar"], "")
        self.assertEqual(formatted["publisher_datetime"], "")

    def test_synchronize_publisher_values_fills_metadata(self):
        """A publisher comment auto-stamps the publisher partner and datetime."""
        values = self.Rating._prepare_publisher_values({"publisher_comment": "Nice"})
        self.assertEqual(values["publisher_id"], self.env.user.partner_id.id)
        self.assertTrue(values["publisher_datetime"])

    def test_publisher_comment_requires_write_access(self):
        """Commenting a rating needs write access on the related record."""
        company = self.env.ref("base.main_company")
        rating = self.Rating.create(
            {
                "res_model_id": self.env["ir.model"]._get("res.company").id,
                "res_id": company.id,
            }
        )
        restricted = new_test_user(
            self.env, login="rating_restricted", groups="base.group_user"
        )
        with self.assertRaises(AccessError):
            rating.with_user(restricted)._check_publisher_values()
