import json

from odoo import models, fields
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("portal")
class TestPortalRating(HttpCase):
    def setUp(self):
        super().setUp()

        class MailTestPortalRating(models.Model):
            """A model intheriting from mail.thread and portal.mixin to test the portal
            chatter controller."""

            _description = "Chatter Model for Portal"
            _name = "x_test.portal_rating"
            _inherit = [
                "mail.thread",
                "portal.mixin",
            ]

            x_name = fields.Char()
            x_partner_id = fields.Many2one("res.partner", "Customer")

        # Register the model dynamically
        MailTestPortalRating._build_model(self.registry, self.env.cr)

        # Force a registry reload to ensure the new model is recognized
        self.env.registry.setup_models(self.env.cr)
        self.env.registry.init_models(
            self.env.cr, [MailTestPortalRating._name], {"module": ""}
        )

        self.partner_1 = self.env["res.partner"].create({"name": "Test Partner Portal"})

        self.record_portal = self.env["x_test.portal_rating"].create(
            {
                "x_partner_id": self.partner_1.id,
                "x_name": "Test Portal Record",
            }
        )

        self.record_portal._portal_ensure_token()


@tagged("-at_install", "post_install", "portal")
class TestPortalRatingControllers(TestPortalRating):
    def test_portal_message_fetch_with_ratings(self):
        """Test retrieving chatter messages with ratings through the portal controller"""
        self.authenticate(None, None)
        message_fetch_url = "/mail/chatter_fetch"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": {
                "res_model": "x_test.portal_rating",
                "res_id": self.record_portal.id,
                "token": self.record_portal.access_token,
            },
        }

        def get_chatter_message_count(rating_included=False):
            if rating_included:
                payload["params"]["rating_include"] = True
            res = self.url_open(
                url=message_fetch_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            return res.json().get("result", {}).get("message_count", 0)

        self.assertEqual(get_chatter_message_count(), 0)

        params = [
            {"body": ""},
            {"body": "", "rating_value": 5},
            {"body": "test 2", "rating_value": 5},
        ]

        for param in params:
            self.record_portal.message_post(
                body=param["body"],
                author_id=self.partner_1.id,
                message_type="comment",
                subtype_id=self.env.ref("mail.mt_comment").id,
                rating_value=param.get("rating_value", None),
            )

        self.assertEqual(get_chatter_message_count(rating_included=False), 1)
        self.assertEqual(get_chatter_message_count(rating_included=True), 2)
