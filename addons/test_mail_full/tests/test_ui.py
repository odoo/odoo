# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.test_mail_full.tests.test_portal import TestPortal


@tests.common.tagged("post_install", "-at_install")
class TestUIPortal(TestPortal):
    def test_star_message(self):
        self.env["mail.message"].create(
            {
                "author_id": self.user_employee.partner_id.id,
                "body": "Test Message",
                "model": self.record_portal._name,
                "res_id": self.record_portal.id,
                "subtype_id": self.ref("mail.mt_comment"),
            }
        )
        self.start_tour(
            f"/my/test_portal_records/{self.record_portal.id}",
            "star_message_tour",
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
