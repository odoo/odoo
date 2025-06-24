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

    def test_load_more(self):
        self.env["mail.message"].create(
            [
                {
                    "author_id": self.user_employee.partner_id.id,
                    "body": f"Test Message {i + 1}",
                    "model": self.record_portal._name,
                    "res_id": self.record_portal.id,
                    "subtype_id": self.ref("mail.mt_comment"),
                }
                for i in range(30)
            ]
        )
        self.start_tour(
            f"/my/test_portal_records/{self.record_portal.id}",
            "load_more_tour",
            login=self.user_employee.login,
        )

    def test_message_actions_without_login(self):
        self.start_tour(
            f"/my/test_portal_records/{self.record_portal.id}?token={self.record_portal._portal_ensure_token()}",
            "message_actions_tour",
        )

    def test_rating_record_portal(self):
        record_rating = self.env["mail.test.rating"].create({"name": "Test rating record"})
        self.start_tour(
            f"/my/test_portal_rating_records/{record_rating.id}?token={record_rating._portal_ensure_token()}",
            "portal_rating_tour",
        )
