# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from lxml import html
from itertools import product

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import UserError
from odoo.tests import HttpCase, JsonRpcException, new_test_user, users
from odoo.tools import mute_logger
from odoo.tools.misc import hash_sign


class TestDiscussChannelInvite(HttpCase, MailCommon):
    def test_01_invite_by_email_flow(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        john = new_test_user(self.env, "john", groups="base.group_user", email="john@test.com")
        group_chat = (
            self.env["discuss.channel"].with_user(bob)._create_group(users_to=bob)
        )
        with self.mock_mail_gateway():
            self.start_tour(
                f"/odoo/discuss?active_id={group_chat.id}", "discuss.invite_by_email", login="bob"
            )
        self.assertIn(john.partner_id, group_chat.channel_member_ids.partner_id)
        self.assertNoMail(self.env["res.partner"], "john@test.com")
        self.assertMailMail(
            self.env["res.partner"],
            status=None,
            email_to_all=["unknown_email@test.com"],
            author=bob.partner_id,
            email_values={
                "subject": f"{bob.name} has invited you to a channel",
            },
        )
        mail = self.env["mail.mail"].search(
            [("model", "=", "discuss.channel"), ("res_id", "=", group_chat.id)]
        )
        body_html = html.fromstring(mail.body_html)
        join_link = body_html.xpath('//a[normalize-space(text())="Join Channel"]')
        self.assertTrue(join_link)
        self.assertEqual(
            join_link[0].get("href"),
            f"{self.env['ir.config_parameter'].get_base_url()}{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'unknown_email@test.com')}",
        )

    def test_02_invite_by_email_excludes_member_emails(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        group_chat = (
            self.env["discuss.channel"].with_user(bob)._create_group(users_to=bob)
        )
        alfred_guest = self.env["mail.guest"].create({"email": "alfred@test.com", "name": "Alfred"})
        group_chat._add_members(guests=alfred_guest)
        with self.mock_mail_gateway():
            group_chat.invite_by_email(["alfred@test.com", "bob@test.com", "other@test.com"])
        self.assertMailMail(
            self.env["res.partner"],
            status=None,
            email_to_all=["other@test.com"],
            author=bob.partner_id,
        )
        self.assertNoMail(self.env["res.partner"], "bob@test.com")
        self.assertNoMail(self.env["res.partner"], "alfred@test.com")

    def test_03_only_invite_by_email_on_allowed_channel_types(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        john = new_test_user(self.env, "john", groups="base.group_user")
        group_chat = (
            self.env["discuss.channel"]
            .with_user(bob)
            ._create_group(users_to=john)
        )
        public_channel = self.env["discuss.channel"].create(
            {"name": "public community", "group_public_id": False}
        )
        private_channel = self.env["discuss.channel"].create(
            {
                "name": "user restricted channel",
                "channel_type": "channel",
                "group_public_id": self.env.ref("base.group_user").id,
            }
        )
        for channel in private_channel:
            with self.assertRaises(UserError) as exc:
                channel.invite_by_email(["some@email.com"])
            self.assertEqual(
                exc.exception.args[0],
                f"Inviting by email is not allowed for this channel type ({channel.channel_type}).",
            )
        with self.mock_mail_gateway():
            # Inviting by email on chat will be allowed but will convert it to a group channel first to allow multiple members.
            for channel in [group_chat, public_channel]:
                channel.invite_by_email(["some@email.com"])
                self.assertMailMail(
                    self.env["res.partner"],
                    status=None,
                    email_to_all=["some@email.com"],
                    email_values={"model": "discuss.channel", "res_id": channel.id},
                )

    def test_04_guest_email_updated_when_invited_from_email(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        group_chat = (
            self.env["discuss.channel"].with_user(bob)._create_group(users_to=bob)
        )
        # guest invited is not added to the channel members until they join the channel
        self.url_open(
            f"{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'alfred@test.com')}"
        )
        self.assertEqual(group_chat.channel_member_ids.guest_id, self.env["mail.guest"])
        # Guest email is updated if empty when invited from email
        guest = self.env["mail.guest"].create({"name": "Alice"})
        self.assertFalse(guest.email)
        self.url_open(
            f"{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'alice@test.com')}",
            cookies={
                guest._cookie_name: f"{guest.id}{guest._cookie_separator}{guest.access_token}",
            },
        )
        self.assertEqual(guest.email, "alice@test.com")
        self.assertEqual(guest.name, "Alice")
        self.assertEqual(group_chat.channel_member_ids.guest_id, self.env["mail.guest"])
        # Guest email is not overwriten if already filled
        guest = self.env["mail.guest"].create({"name": "John", "email": "john@test.com"})
        self.url_open(
            f"{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'john_other_email@test.com')}",
            cookies={
                guest._cookie_name: f"{guest.id}{guest._cookie_separator}{guest.access_token}",
            },
        )
        self.assertEqual(guest.email, "john@test.com")
        self.assertEqual(guest.name, "John")

    def test_05_search_for_channel_invite_selectable_email(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        john = new_test_user(self.env, "john", groups="base.group_user", email="john@test.com")
        alfred_guest = self.env["mail.guest"].create({"email": "alfred@test.com", "name": "Alfred"})
        group_chat = (
            self.env["discuss.channel"]
            .with_user(bob)
            ._create_group(users_to=john)
        )
        group_chat._add_members(guests=alfred_guest)
        public_channel = self.env["discuss.channel"].create(
            {"name": "public community", "group_public_id": False},
        )
        public_channel._add_members(guests=alfred_guest)
        private_channel = self.env["discuss.channel"].create(
            {
                "name": "user restricted channel",
                "channel_type": "channel",
                "group_public_id": self.env.ref("base.group_user").id,
            },
        )
        cases = [
            *product(
                [private_channel, group_chat, public_channel],
                ["foo@bar"],
                [False],
            ),
            # Channel types that do not allow inviting by email, not selectable.
            *product(
                private_channel,
                ["bob@odoo.com", "alfred@odoo.com", "jane@odoo.com"],
                [False],
            ),
            # Channel types that allow inviting by email, valid email, selectable.
            *product(
                [group_chat, public_channel],
                ["bob@odoo.com", "alfred@odoo.com", "jane@odoo.com"],
                [True],
            ),
        ]
        for channel, search_term, is_selectable in cases:
            with self.subTest(
                f"channel={channel.channel_type}_{channel.display_name}, search_term={search_term}, is_selectable={is_selectable}"
            ):
                result = self.env["res.partner"].search_for_channel_invite(
                    search_term, channel_id=channel.id
                )
                if is_selectable:
                    self.assertEqual(result["selectable_email"], search_term)
                    continue
                self.assertFalse(result["selectable_email"])

    @users("employee")
    def test_06_invite_by_email_posts_user_notification(self):
        group_chat = self.env["discuss.channel"]._create_group(users_to=self.user_employee)
        with self.mock_mail_gateway():
            group_chat.invite_by_email(["alfred@test.com"])
        last_message = group_chat._get_last_messages()
        self.assertEqual(last_message.message_type, "user_notification")

    def test_07_invite_link_rotation_revokes_old_access(self):
        public_channel = self.env["discuss.channel"].create(
            {"name": "Rotation Test Channel", "group_public_id": False},
        )
        old_url = public_channel.invitation_url
        response = self.url_open(old_url)
        self.assertEqual(response.status_code, 200)
        public_channel.action_reset_invitation_uuid()
        new_url = public_channel.invitation_url
        response = self.url_open(old_url)
        self.assertEqual(response.status_code, 404)
        response = self.url_open(new_url)
        self.assertEqual(response.status_code, 200)

    def test_08_invite_by_email_resent_while_invitation_is_pending(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        group_chat = self.env["discuss.channel"].with_user(bob)._create_group(users_to=bob)
        with self.mock_mail_gateway():
            group_chat.invite_by_email(["alfred@test.com"])
            self.assertMailMail(
                self.env["res.partner"],
                status=None,
                email_to_all=["alfred@test.com"],
                author=bob.partner_id,
            )
        pending_member = group_chat.channel_member_ids.filtered(
            lambda member: member.guest_id.email == "alfred@test.com"
        )
        self.assertTrue(pending_member.invitation_sent_dt)
        # A pending address is still selectable, and flagged as already invited.
        result = self.env["res.partner"].search_for_channel_invite(
            "alfred@test.com", channel_id=group_chat.id
        )
        self.assertEqual(result["selectable_email"], "alfred@test.com")
        self.assertTrue(result["email_already_sent"])
        # Inviting again sends the link a second time, reusing the pending member.
        with self.mock_mail_gateway():
            group_chat.invite_by_email(["alfred@test.com"])
            self.assertMailMail(
                self.env["res.partner"],
                status=None,
                email_to_all=["alfred@test.com"],
                author=bob.partner_id,
            )
        self.assertEqual(
            group_chat.channel_member_ids.filtered(
                lambda member: member.guest_id.email == "alfred@test.com"
            ),
            pending_member,
        )
        # Once the invitation is accepted, the address is no longer invitable.
        self.url_open(
            f"{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'alfred@test.com')}"
        )
        self.assertFalse(pending_member.invitation_sent_dt)
        result = self.env["res.partner"].search_for_channel_invite(
            "alfred@test.com", channel_id=group_chat.id
        )
        self.assertFalse(result["selectable_email"])
        with self.mock_mail_gateway():
            group_chat.invite_by_email(["alfred@test.com"])
            self.assertNoMail(self.env["res.partner"], email_to="alfred@test.com")

    def test_09_resend_invitation_from_the_member_list(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        group_chat = self.env["discuss.channel"].with_user(bob)._create_group(users_to=bob)
        with self.mock_mail_gateway():
            group_chat.invite_by_email(["alfred@test.com"])
        pending_member = group_chat.channel_member_ids.filtered(
            lambda member: member.guest_id.email == "alfred@test.com"
        )
        self.assertTrue(pending_member.invitation_sent_dt)
        # Backdate the first invitation to tell both invitation dates apart.
        first_sent_dt = pending_member.invitation_sent_dt - timedelta(days=1)
        pending_member.sudo().invitation_sent_dt = first_sent_dt
        self.authenticate("bob", "bob")
        with self.mock_mail_gateway():
            self.make_jsonrpc_request(
                "/discuss/channel/member/resend_invitation", {"member_id": pending_member.id}
            )
            self.assertMailMail(
                self.env["res.partner"],
                status=None,
                email_to_all=["alfred@test.com"],
                author=bob.partner_id,
            )
        pending_member.invalidate_recordset(["invitation_sent_dt"])
        self.assertGreater(pending_member.invitation_sent_dt, first_sent_dt)
        # Members who already joined have no invitation left to resend.
        with self.assertRaises(JsonRpcException), self.mock_mail_gateway():
            self.make_jsonrpc_request(
                "/discuss/channel/member/resend_invitation",
                {"member_id": group_chat.self_member_id.id},
            )

    def test_10_inviting_a_portal_user_shows_them_once_as_pending(self):
        """A portal user is mailed the link and shown as a single pending member: a guest for
        their address on top of their own member would look like two different people."""
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        joel = new_test_user(
            self.env, "joel", groups="base.group_portal", email="joel@test.com", name="Joel Willis"
        )
        group_chat = self.env["discuss.channel"].with_user(bob)._create_group(users_to=bob)
        self.authenticate("bob", "bob")
        with self.mock_mail_gateway():
            self.make_jsonrpc_request(
                "/mail/store",
                {
                    "fetch_params": [
                        [
                            "/discuss/channel/add_members",
                            {"channel_id": group_chat.id, "user_ids": joel.ids},
                        ],
                    ],
                },
            )
            self.assertMailMail(
                self.env["res.partner"],
                status=None,
                email_to_all=["joel@test.com"],
                author=bob.partner_id,
            )
        group_chat.invalidate_recordset(["channel_member_ids"])
        self.assertEqual(
            group_chat.channel_member_ids.partner_id, bob.partner_id + joel.partner_id
        )
        self.assertFalse(group_chat.channel_member_ids.guest_id)
        # The invitation is tracked on Joel's own member, so it can be sent again from there.
        joel_member = group_chat.channel_member_ids.filtered(
            lambda member: member.partner_id == joel.partner_id
        )
        self.assertEqual(group_chat.channel_member_ids.filtered("invitation_sent_dt"), joel_member)
        # Joel is a member from the start: he stays pending until he shows up himself.
        self.url_open(
            f"{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'joel@test.com')}"
        )
        joel_member.invalidate_recordset(["invitation_sent_dt"])
        self.assertTrue(joel_member.invitation_sent_dt, "the link was opened by bob, not joel")
        self.authenticate("joel", "joel")
        self.make_jsonrpc_request(
            "/discuss/channel/mark_as_read",
            {"channel_id": group_chat.id, "last_message_id": group_chat.message_ids[:1].id},
        )
        joel_member.invalidate_recordset(["invitation_sent_dt"])
        self.assertFalse(joel_member.invitation_sent_dt)

    def test_11_only_members_can_send_the_invitation_link_again(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        new_test_user(self.env, "john", groups="base.group_user", email="john@test.com")
        public_channel = self.env["discuss.channel"].create(
            {"name": "Public Channel", "group_public_id": False},
        )
        public_channel._add_members(users=bob)
        with self.mock_mail_gateway():
            public_channel.with_user(bob).invite_by_email(["alfred@test.com"])
        pending_member = public_channel.channel_member_ids.filtered(
            lambda member: member.guest_id.email == "alfred@test.com"
        )
        # John reaches the channel and its members, but did not join it.
        self.authenticate("john", "john")
        with (
            self.assertRaises(JsonRpcException, msg="odoo.exceptions.AccessError"),
            self.mock_mail_gateway(),
            mute_logger("odoo.http"),
        ):
            self.make_jsonrpc_request(
                "/discuss/channel/member/resend_invitation", {"member_id": pending_member.id}
            )
        with self.mock_mail_gateway():
            self.assertNoMail(self.env["res.partner"], email_to="alfred@test.com")

    def test_12_guest_invitation_adds_member_to_channel(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        group_chat = (
            self.env["discuss.channel"].with_user(bob)._create_group(users_to=bob)
        )
        self.start_tour(
            f"{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'alfred@test.com')}",
            "discuss.guest_accept_invitation",
        )
        guest = self.env["mail.guest"].search([("email", "=", "alfred@test.com")])
        self.assertEqual(len(guest), 1)
        self.assertIn(
            guest,
            group_chat.channel_member_ids.guest_id,
        )
        self.assertEqual(guest.name, "Alfredo Pasta")
