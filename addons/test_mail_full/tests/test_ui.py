# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests

from odoo.addons.mail.tests.common import mail_new_test_user
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

    def test_portal_message_highlight(self):
        self.user_portal = mail_new_test_user(
            self.env,
            company_id=self.user_admin.company_id.id,
            email='user.portal@test.example.com',
            login='user_portal',
            groups='base.group_portal',
            name='Paul Portal',
        )
        self.portal_record_no_partner = self.env["mail.test.portal.no.partner"].create({
            'name': 'Test Portal Record',
        })
        self.portal_message = self.env["mail.message"].create(
            {
                "author_id": self.user_portal.partner_id.id,
                "body": "Test Message",
                "model": self.portal_record_no_partner._name,
                "res_id": self.portal_record_no_partner.id,
                "message_type": "comment",
                "subtype_id": self.ref("mail.mt_comment"),
            }
        )
        self.start_tour(
            f"/mail/message/{self.portal_message.id}",
            "highlight_portal_message",
            login=self.user_portal.login,
        )
