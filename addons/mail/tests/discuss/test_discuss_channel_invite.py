# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import html
from itertools import product

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import UserError
from odoo.tests import HttpCase, new_test_user, tagged, users
from odoo.tools.misc import hash_sign


@tagged("-at_install", "post_install")
class TestDiscussChannelInvite(HttpCase, MailCommon):
    def test_01_invite_by_email_flow(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        john = new_test_user(self.env, "john", groups="base.group_user", email="john@test.com")
        group_chat = (
            self.env["discuss.channel"].with_user(bob)._create_group(partners_to=bob.partner_id.ids)
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
            self.env["discuss.channel"].with_user(bob)._create_group(partners_to=bob.partner_id.ids)
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
        chat = (
            self.env["discuss.channel"]
            .with_user(bob)
            ._get_or_create_chat(partners_to=john.partner_id.ids)
        )
        group_chat = (
            self.env["discuss.channel"]
            .with_user(bob)
            ._create_group(partners_to=john.partner_id.ids)
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
        for channel in [chat, private_channel]:
            with self.assertRaises(UserError) as exc:
                channel.invite_by_email(["some@email.com"])
            self.assertEqual(
                exc.exception.args[0],
                f"Inviting by email is not allowed for this channel type ({channel.channel_type}).",
            )
        with self.mock_mail_gateway():
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
            self.env["discuss.channel"].with_user(bob)._create_group(partners_to=bob.partner_id.ids)
        )
        # Guest email is filled at create
        self.url_open(
            f"{group_chat.invitation_url}?email_token={hash_sign(self.env, 'mail.invite_email', 'alfred@test.com')}"
        )
        self.assertEqual(group_chat.channel_member_ids.guest_id.email, "alfred@test.com")
        self.assertEqual(group_chat.channel_member_ids.guest_id.name, "alfred@test.com")
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
        chat = (
            self.env["discuss.channel"]
            .with_user(bob)
            ._get_or_create_chat(partners_to=john.partner_id.ids)
        )
        group_chat = (
            self.env["discuss.channel"]
            .with_user(bob)
            ._create_group(partners_to=john.partner_id.ids)
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
                [chat, private_channel, group_chat, public_channel],
                ["foo@bar"],
                [False],
            ),
            # Channel types that do not allow inviting by email, not selectable.
            *product(
                [chat, private_channel],
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
        group_chat = self.env["discuss.channel"]._create_group(partners_to=self.user_employee.partner_id.ids)
        with self.mock_mail_gateway():
            group_chat.invite_by_email(["alfred@test.com"])
        last_message = group_chat._get_last_messages()
        self.assertEqual(last_message.message_type, "user_notification")
