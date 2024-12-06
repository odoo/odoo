# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestMessageReactionControllerCommon(HttpCaseWithUserDemo, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        cls.public_user = cls.env.ref("base.public_user")
        cls.guest = cls.env["mail.guest"].create({"name": "Guest"})
        cls.public_w_guest = cls.public_user
        cls.no_user = cls.env["res.users"]  # same as public user but with no guest
        last_message = cls.env["mail.message"].search([], order="id desc", limit=1)
        cls.fake_message = cls.env["mail.message"].browse(last_message.id + 1000000)
        cls.reaction = "😊"

    def _execute_subtests(self, message, subtests):
        for user, allowed in subtests:
            if not user:
                self.authenticate(None, None)
            elif user != self.public_w_guest:
                self.authenticate(user.login, user.login)
            else:
                self.authenticate(None, None)
                self.opener.cookies[self.guest._cookie_name] = (
                    f"{self.guest.id}{self.guest._cookie_separator}{self.guest.access_token}"
                )
            msg = str(message.body) if message != self.fake_message else "fake message"
            with self.subTest(message=msg, login=user.login):
                if allowed:
                    data = self._add_reaction(message, self.reaction)
                    self.assertNotIn("error", data)
                    reactions = self._find_reactions(message)
                    self.assertEqual(len(reactions), 1)
                    if user == self.public_w_guest:
                        self.assertEqual(reactions.guest_id, self.guest)
                    else:
                        self.assertEqual(reactions.partner_id, user.partner_id)
                    data = self._remove_reaction(message, self.reaction)
                    self.assertNotIn("error", data)
                    self.assertEqual(len(self._find_reactions(message)), 0)
                else:
                    data = self._add_reaction(message, self.reaction)
                    self.assertIn("error", data)
                    data = self._remove_reaction(message, self.reaction)
                    self.assertIn("error", data)

    def _add_reaction(self, message, content):
        res = self.opener.post(
            url=f"{self.env.user.get_base_url()}/mail/message/add_reaction",
            json={"params": {"message_id": message.id, "content": content}},
        )
        return json.loads(res.content)

    def _remove_reaction(self, message, content):
        res = self.opener.post(
            url=f"{self.env.user.get_base_url()}/mail/message/remove_reaction",
            json={"params": {"message_id": message.id, "content": content}},
        )
        return json.loads(res.content)

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
                (self.no_user, False),
                (self.public_w_guest, False),
                (self.user_portal, False),
                # False because not group_partner_manager
                (self.user_employee, False),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_public_channel(self):
        """Test access of message reaction for a public channel."""
        channel = self.env["mail.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        message = channel.message_post(body="public message")
        self._execute_subtests(
            message,
            (
                (self.no_user, False),
                (self.public_w_guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_channel_as_member(self):
        """Test access of message reaction for a channel as member."""
        channel = self.env["mail.channel"].browse(
            self.env["mail.channel"].create_group(
                partners_to=(self.user_portal + self.user_employee + self.user_demo).partner_id.ids
            )["id"]
        )
        channel.add_members(guest_ids=self.guest.ids)
        message = channel.message_post(body="invite message")
        self._execute_subtests(
            message,
            (
                (self.no_user, False),
                (self.public_w_guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_message_reaction_channel_as_non_member(self):
        """Test access of message reaction for a channel as non-member."""
        channel = self.env["mail.channel"].browse(
            self.env["mail.channel"].create_group(partners_to=[])["id"]
        )
        message = channel.message_post(body="private message")
        self._execute_subtests(
            message,
            (
                (self.no_user, False),
                (self.public_w_guest, False),
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
                (self.no_user, False),
                (self.public_w_guest, False),
                (self.user_portal, False),
                (self.user_employee, False),
                (self.user_demo, False),
                (self.user_admin, False),
            ),
        )
