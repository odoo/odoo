# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from odoo import tests
from odoo.addons.test_mail_full.tests.test_portal import TestPortal


@tests.common.tagged("post_install", "-at_install")
class TestUIPortal(TestPortal):

    def setUp(self):
        super().setUp()
        self.env["mail.message"].create(
            {
                "author_id": self.user_employee.partner_id.id,
                "body": "Test Message",
                "model": self.record_portal._name,
                "res_id": self.record_portal.id,
                "subtype_id": self.ref("mail.mt_comment"),
            }
        )

    def test_star_message(self):
        self.start_tour(
            f"/my/test_portal_records/{self.record_portal.id}",
            "star_message_tour",
            login=self.user_employee.login,
        )

    def test_no_copy_link_for_non_readable_portal_record(self):
        # mail.test.portal has read access only for base.group_user
        self.start_tour(
            f"/my/test_portal_records/{self.record_portal.id}?{urlencode({'token': self.record_portal.access_token})}",
            "portal_no_copy_link_tour",
            login=None,
        )

    def test_copy_link_for_readable_portal_record(self):
        # mail.test.portal has read access only for base.group_user
        self.start_tour(
            f"/my/test_portal_records/{self.record_portal.id}?{urlencode({'token': self.record_portal.access_token})}",
            "portal_copy_link_tour",
            login=self.user_employee.login,
        )

    def test_rating_record_portal(self):
        record_rating = self.env["mail.test.rating"].create({"name": "Test rating record"})
        # To check if there is no message with rating, there is no rating cards feature.
        record_rating.message_post(
            body="Message without rating",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.start_tour(
            f"/my/test_portal_rating_records/{record_rating.id}?display_rating=True&token={record_rating._portal_ensure_token()}",
            "portal_rating_tour"
        )

    def test_display_rating_portal(self):
        record_rating = self.env["mail.test.rating"].create({"name": "Test rating record"})
        record_rating.message_post(
            body="Message with rating",
            message_type="comment",
            rating_value="5",
            subtype_xmlid="mail.mt_comment",
        )
        self.start_tour(
            f"/my/test_portal_rating_records/{record_rating.id}?display_rating=True&token={record_rating._portal_ensure_token()}",
            "portal_display_rating_tour",
        )
        self.start_tour(
            f"/my/test_portal_rating_records/{record_rating.id}?display_rating=False&token={record_rating._portal_ensure_token()}",
            "portal_not_display_rating_tour",
        )
