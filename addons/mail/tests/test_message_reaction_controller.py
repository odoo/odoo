# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import JsonRpcException
from odoo.addons.mail.tests.test_controller_common import TestControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestMessageReactionControllerCommon(TestControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reaction = "😊"

    def _execute_subtests(self, message, subtests):
        for data_user, allowed, *args in subtests:
            route_kw = args[0] if args else {}
            kwargs = args[1] if len(args) > 1 else {}
            user = data_user if data_user._name == "res.users" else self.user_public
            guest = data_user if data_user._name == "mail.guest" else self.env["mail.guest"]
            self._authenticate_user(user=user, guest=guest)
            msg = str(message.body) if message != self.fake_message else "fake message"
            with self.subTest(message=msg, user=user.name, guest=guest.name, route_kw=route_kw):
                if allowed:
                    self._add_reaction(message, self.reaction, route_kw)
                    reactions = self._find_reactions(message)
                    self.assertEqual(len(reactions), 1)
                    expected_partner = kwargs.get("partner")
                    if guest and not expected_partner:
                        self.assertEqual(reactions.guest_id, guest)
                    else:
                        self.assertEqual(reactions.partner_id, expected_partner or user.partner_id)
                    self._remove_reaction(message, self.reaction, route_kw)
                    self.assertEqual(len(self._find_reactions(message)), 0)
                else:
                    with self.assertRaises(
                        JsonRpcException, msg="add reaction should raise NotFound"
                    ):
                        self._add_reaction(message, self.reaction, route_kw)
                    with self.assertRaises(
                        JsonRpcException, msg="remove reaction should raise NotFound"
                    ):
                        self._remove_reaction(message, self.reaction, route_kw)

    def _add_reaction(self, message, content, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/reaction",
            params={"action": "add", "content": content, "message_id": message.id, **route_kw},
        )

    def _remove_reaction(self, message, content, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/reaction",
            params={"action": "remove", "content": content, "message_id": message.id, **route_kw},
        )

    def _find_reactions(self, message):
        return self.env["mail.message.reaction"].search([("message_id", "=", message.id)])


@odoo.tests.tagged("-at_install", "post_install")
class TestMessageReactionController(TestMessageReactionControllerCommon):
    def test_message_reaction_partner(self):
        """Test access of message reaction for partner chatter."""
        message = self.user_demo.partner_id.message_post(body="partner message")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                # False because not group_partner_manager
                (self.user_employee, False),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_public_channel(self):
        """Test access of message reaction for a public channel."""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        message = channel.message_post(body="public message")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_channel_as_member(self):
        """Test access of message reaction for a channel as member."""
        channel = self.env["discuss.channel"].browse(
            self.env["discuss.channel"].create_group(
                partners_to=(self.user_portal + self.user_employee + self.user_demo).partner_id.ids
            )["id"]
        )
        channel.add_members(guest_ids=self.guest.ids)
        message = channel.message_post(body="invite message")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_channel_as_non_member(self):
        """Test access of message reaction for a channel as non-member."""
        channel = self.env["discuss.channel"].browse(
            self.env["discuss.channel"].create_group(partners_to=[])["id"]
        )
        message = channel.message_post(body="private message")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, False),
                (self.user_demo, False),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_fake_message(self):
        """Test access of message reaction for a non-existing message."""
        self._execute_subtests(
            self.fake_message,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, False),
                (self.user_demo, False),
                (self.user_admin, False),
            ),
        )
