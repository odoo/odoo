import json

from odoo import http
from odoo.addons.mail.tests.common_controllers import MailControllerThreadCommon
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install", "mail_controller")
class TestMessageController(MailControllerThreadCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_public_record = cls.env["mail.test.access.public"].create({"name": "Public Channel", "email": "john@test.be", "mobile": "+32455001122"})

    @mute_logger("odoo.http")
    def test_thread_attachment_hijack(self):
        att = self.env["ir.attachment"].create({
            "name": "arguments_for_firing_marc_demo",
            "res_id": 0,
            "res_model": "mail.compose.message",
        })
        self.authenticate(self.user_employee.login, self.user_employee.login)
        record = self.env["mail.test.access.public"].create({"name": "Public Channel"})
        record.with_user(self.user_employee).write({'name': 'updated'})  # can access, update, ...
        # if this test breaks, it might be due to a change in /web/content, or the default rules for accessing an attachment. This is not an issue but it makes this test irrelevant.
        self.assertFalse(self.url_open(f"/web/content/{att.id}").ok)
        response = self.url_open(
            url="/mail/message/post",
            headers={"Content-Type": "application/json"},  # route called as demo
            data=json.dumps(
                {
                    "params": {
                        "post_data": {
                            "attachment_ids": [att.id],  # demo does not have access to this attachment id
                            "body": "",
                            "message_type": "comment",
                            "partner_ids": [],
                            "subtype_xmlid": "mail.mt_comment",
                        },
                        "thread_id": record.id,
                        "thread_model": record._name,
                    }
                },
            ),
        )
        self.assertNotIn(
            "arguments_for_firing_marc_demo", response.text
        )  # demo should not be able to see the name of the document

    def test_thread_partner_from_email_authenticated(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        res3 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "emails": ["john@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john@test.be"), ('phone', '=', "+32455001122")]),
            "authenticated users can create a partner from an email",
        )
        # should not create another partner with same email
        res4 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "emails": ["john@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john@test.be")]),
            "'mail/partner/from_email' does not create another user if there's already a user with matching email",
        )

        self.test_public_record.write({'email': 'john2@test.be'})
        res5 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "post_data": {
                            "body": "test",
                            "partner_emails": ["john2@test.be"],
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res5.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john2@test.be"), ('phone', '=', "+32455001122")]),
            "authenticated users can create a partner from an email from message_post",
        )
        # should not create another partner with same email
        res6 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.test_public_record._name,
                        "thread_id": self.test_public_record.id,
                        "post_data": {
                            "body": "test",
                            "partner_emails": ["john2@test.be"],
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res6.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john2@test.be")]),
            "'mail/message/post' does not create another user if there's already a user with matching email",
        )

    def test_thread_post_archived_record(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        archived_partner = self.env["res.partner"].create({"name": "partner", "active": False})

        # 1. posting a message
        data = self.make_jsonrpc_request("/mail/message/post", {
            "thread_model": "res.partner",
            "thread_id": archived_partner.id,
            "post_data": {
                "body": "A great message",
            }
        })
        self.assertEqual(["markup", "<p>A great message</p>"], data["mail.message"][0]["body"])

        # 2. attach a file
        response = self.url_open(
            "/mail/attachment/upload",
            {
                "csrf_token": http.Request.csrf_token(self),
                "thread_id": archived_partner.id,
                "thread_model": "res.partner",
            },
            files={"ufile": b""},
        )
        self.assertEqual(response.status_code, 200)
