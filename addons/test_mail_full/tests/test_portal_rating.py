import json

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("-at_install", "post_install", "portal")
class TestPortalRatingControllers(HttpCase):
    def setUp(self):
        super().setUp()
        self.partner_1 = self.env["res.partner"].create({"name": "Test Partner Portal"})

        self.portal_record = self.env["mail.test.portal"].create(
            {
                "name": "Test Portal Record",
                "partner_id": self.partner_1.id,
            }
        )

    def test_portal_message_fetch_with_ratings(self):
        """Test retrieving chatter messages with ratings through the portal controller"""

        if not self.env["ir.module.module"].search(
            [("name", "=", "portal_rating"), ("state", "=", "installed")]
        ):
            self.skipTest(
                "This test requires the installation of the `Portal Rating` module"
            )

        self.authenticate(None, None)
        message_fetch_url = "/mail/chatter_fetch"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": {
                "res_model": "mail.test.portal",
                "res_id": self.portal_record.id,
                "token": self.portal_record.access_token,
            },
        }

        def get_chatter_message_count():
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
            self.portal_record.message_post(
                body=param["body"],
                author_id=self.partner_1.id,
                message_type="comment",
                subtype_id=self.env.ref("mail.mt_comment").id,
                rating_value=param.get("rating_value", None),
            )

        self.assertEqual(get_chatter_message_count(), 1)
        payload["params"]["rating_include"] = True
        self.assertEqual(get_chatter_message_count(), 2)
