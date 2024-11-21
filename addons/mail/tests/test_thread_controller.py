# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import JsonRpcException
from odoo.addons.mail.tests.test_controller_common import TestControllerCommon


class MessagePostSubTestData:
    def __init__(
        self,
        user,
        allowed,
        /,
        *,
        partners=None,
        partner_emails=None,
        route_kw=None,
        exp_author=None,
        exp_partners=None,
        exp_emails=None,
    ):
        self.user = user if user._name == "res.users" else user.env.ref("base.public_user")
        self.guest = user if user._name == "mail.guest" else user.env["mail.guest"]
        self.allowed = allowed
        self.route_kw = {
            "context": {"mail_create_nosubscribe": True, "mail_post_autofollow": False},
            **(route_kw or {}),
        }
        if partner_emails is not None:
            self.route_kw["partner_emails"] = partner_emails
        self.post_data = {
            "body": "<p>Hello</p>",
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
        }
        if partners is not None:
            self.post_data["partner_ids"] = partners.ids
        self.exp_author = exp_author
        self.exp_partners = exp_partners
        self.exp_emails = exp_emails


@odoo.tests.tagged("-at_install", "post_install")
class TestThreadControllerCommon(TestControllerCommon):
    def _execute_message_post_subtests(self, record, tests: list[MessagePostSubTestData]):
        for test in tests:
            self._authenticate_user(user=test.user, guest=test.guest)
            with self.subTest(
                record=record, user=test.user.name, guest=test.guest.name, route_kw=test.route_kw
            ):
                if test.allowed:
                    self._message_post(record, test.post_data, test.route_kw)
                    message = self._find_message(record)
                    self.assertTrue(message)
                    if test.guest and not test.exp_author:
                        self.assertEqual(message.author_guest_id, test.guest)
                    else:
                        self.assertEqual(message.author_id, test.exp_author or test.user.partner_id)
                    if test.exp_partners is not None:
                        self.assertEqual(message.partner_ids, test.exp_partners)
                    if test.exp_emails is not None:
                        self.assertEqual(message.partner_ids.mapped("email"), test.exp_emails)
                else:
                    with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
                        self._message_post(record, test.post_data, test.route_kw)

    def _message_post(self, record, post_data, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/post",
            params={
                "thread_model": record._name,
                "thread_id": record.id,
                "post_data": post_data,
                **route_kw,
            },
        )

    def _find_message(self, record):
        return self.env["mail.message"].search(
            [("res_id", "=", record.id), ("model", "=", record._name)], order="id desc", limit=1
        )


@odoo.tests.tagged("-at_install", "post_install")
class TestThreadController(TestThreadControllerCommon):
    def test_partner_message_post_access(self):
        """Test access of message_post on partner record."""
        record = self.env["res.partner"].create({"name": "Test Partner"})

        def test_access(user, allowed):
            return MessagePostSubTestData(user, allowed)

        self._execute_message_post_subtests(
            record,
            (
                test_access(self.user_public, False),
                test_access(self.guest, False),
                test_access(self.user_portal, False),
                # False because not base.group_partner_manager
                test_access(self.user_employee, False),
                test_access(self.user_demo, True),
                test_access(self.user_admin, True),
            ),
        )

    def test_partner_message_post_partner_ids(self):
        """Test partner_ids of message_post on partner record."""
        record = self.env["res.partner"].create({"name": "Test Partner"})
        partners = (
            self.user_portal + self.user_employee + self.user_demo + self.user_admin
        ).partner_id
        no_partner = self.env["res.partner"]

        def test_partners(user, allowed, exp_partners):
            return MessagePostSubTestData(
                user, allowed, partners=partners, exp_partners=exp_partners
            )

        self._execute_message_post_subtests(
            record,
            (
                test_partners(self.user_public, False, no_partner),
                test_partners(self.guest, False, no_partner),
                test_partners(self.user_portal, False, no_partner),
                # False because not base.group_partner_manager
                test_partners(self.user_employee, False, no_partner),
                test_partners(self.user_demo, True, partners),
                test_partners(self.user_admin, True, partners),
            ),
        )
