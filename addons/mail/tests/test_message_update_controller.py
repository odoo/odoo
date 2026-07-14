# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

import odoo
from odoo.tests import JsonRpcException
from odoo.addons.mail.tests.test_controller_common import TestControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestMessageUpdateControllerCommon(TestControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_body = "Message body"
        cls.alter_message_body = "Altered message body"

    def _execute_subtests(self, message, subtests):
        for data_user, allowed, *args in subtests:
            route_kw = args[0] if args else {}
            user = data_user if data_user._name == "res.users" else self.user_public
            guest = data_user if data_user._name == "mail.guest" else self.env["mail.guest"]
            self._authenticate_user(user=user, guest=guest)
            msg = str(message.body) if message != self.fake_message else "fake message"
            with self.subTest(message=msg, user=user.name, guest=guest.name, route_kw=route_kw):
                if allowed:
                    self._update_content(message.id, self.alter_message_body, route_kw)
                    self.assertEqual(message.body,
                                     Markup('<p>Altered message body<span class="o-mail-Message-edited"></span></p>'))
                else:
                    with self.assertRaises(
                        JsonRpcException,
                        msg="update message content should raise NotFound",
                    ):
                        self._update_content(message.id, self.alter_message_body, route_kw)

    def _update_content(self, message_id, body, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/update_content",
            params={
                "message_id": message_id,
                "body": body,
                "attachment_ids": [],
                **route_kw,
            },
        )


@odoo.tests.tagged("-at_install", "post_install")
class TestMessageUpdateController(TestMessageUpdateControllerCommon):
    def test_message_update_partner_as_owner(self):
        """Test only admin user and message author can update the message content."""
        message = self.user_demo.partner_id.message_post(
            body=self.message_body,
            author_id=self.user_demo.partner_id.id,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_demo, True),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )

    def test_message_update_non_owner_partner(self):
        """Test only admin user can update the message content if the user is not the author."""
        message = self.user_demo.partner_id.message_post(
            body=self.message_body,
            author_id=self.user_admin.partner_id.id,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_demo, False),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )

    def test_message_update_fake_message(self):
        """Test update a non-existing message."""
        self._execute_subtests(
            self.fake_message,
            (
                (self.guest, False),
                (self.user_admin, False),
                (self.user_demo, False),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )
