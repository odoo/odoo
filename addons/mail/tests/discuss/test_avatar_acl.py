# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.tests import HttpCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestAvatarAcl(HttpCase):
    def get_avatar_url(self, record):
        return f"/web/image?field=avatar_128&id={record.id}&model={record._name}&unique={fields.Datetime.to_string(record.write_date)}"

    def test_partner_open_guest_avatar(self):
        self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        guest = self.env["mail.guest"].create({"name": "Guest"})
        res = self.url_open(url=self.get_avatar_url(guest))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=Guest.svg")

    def test_partner_open_guest_avatar_with_channel(self):
        testuser = self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        guest = self.env["mail.guest"].create({"name": "Guest"})
        partner = self.env["res.users"].browse(testuser.id).partner_id
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel.add_members(guest_ids=[guest.id], partner_ids=[partner.id])
        res = self.url_open(url=self.get_avatar_url(guest))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=Guest.svg")

    def test_guest_open_partner_avatar(self):
        self.authenticate(None, None)
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
        testuser = self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        partner = self.env["res.users"].browse(testuser.id).partner_id
        res = self.url_open(url=self.get_avatar_url(partner))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")

    def test_guest_open_partner_avatar_with_channel(self):
        self.authenticate(None, None)
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
        testuser = self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        partner = self.env["res.users"].browse(testuser.id).partner_id
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel.add_members(guest_ids=[guest.id], partner_ids=[partner.id])
        res = self.url_open(url=self.get_avatar_url(partner))
        self.assertEqual(res.headers["Content-Disposition"], f'inline; filename="{partner.name}.svg"')

    def test_guest_open_left_member_avatar(self):
        self.authenticate(None, None)
        guest_1 = self.env["mail.guest"].create({"name": "Guest 1"})
        guest_2 = self.env["mail.guest"].create({"name": "Guest 2"})
        user = self.env["res.users"].create(
            {
                "email": "testuser1@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User 1",
                "login": "testuser1",
                "password": "testuser1",
            },
        )
        partner = user.partner_id
        channel = self.env["discuss.channel"].create(
            {
                "channel_type": "group",
                "name": "Test channel",
            }
        )
        partner_member, guest_member = channel.add_members(
            partner_ids=[partner.id], guest_ids=[guest_1.id]
        )
        channel.message_post(
            body="Test",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=partner.id,
        )
        channel.with_user(self.env.ref("base.public_user")).with_context(
            guest=guest_1
        ).message_post(
            body="Test",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        (partner_member + guest_member).unlink()
        for author in [guest_1, partner]:
            res = self.url_open(url=self.get_avatar_url(author))
            self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")
        self.opener.cookies[guest_2._cookie_name] = guest_2._format_auth_cookie()
        channel.add_members(guest_ids=[guest_2.id])
        for author in [guest_1, partner]:
            res = self.url_open(url=self.get_avatar_url(author))
            self.assertEqual(
                res.headers["Content-Disposition"], f'inline; filename="{author.name}.svg"'
            )

    def test_partner_open_partner_avatar(self):
        testuser = self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        testuser2 = self.env["res.users"].create(
            {
                "email": "testuser2@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User 2",
                "login": "testuser 2",
                "password": "testuser 2",
            }
        )
        partner = self.env["res.users"].browse(testuser.id).partner_id
        partner2 = self.env["res.users"].browse(testuser2.id).partner_id
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel.add_members(partner_ids=[partner.id, partner2.id])
        res = self.url_open(url=self.get_avatar_url(partner2))
        self.assertEqual(res.headers["Content-Disposition"], f'inline; filename="{partner2.name}.svg"')

    def test_guest_open_guest_avatar(self):
        self.authenticate(None, None)
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
        guest2 = self.env["mail.guest"].create({"name": "Guest 2"})
        res = self.url_open(url=self.get_avatar_url(guest2))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")

    def test_guest_open_guest_avatar_with_channel(self):
        self.authenticate(None, None)
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
        guest2 = self.env["mail.guest"].create({"name": "Guest 2"})
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel.add_members(guest_ids=[guest.id, guest2.id])
        res = self.url_open(url=self.get_avatar_url(guest2))
        self.assertEqual(res.headers["Content-Disposition"], 'inline; filename="Guest 2.svg"')

    def test_portal_open_partner_avatar(self):
        self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_portal")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        testuser2 = self.env["res.users"].create(
            {
                "email": "testuser2@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User 2",
                "login": "testuser 2",
                "password": "testuser 2",
            }
        )
        partner2 = self.env["res.users"].browse(testuser2.id).partner_id
        res = self.url_open(url=self.get_avatar_url(partner2))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")

    def test_portal_open_partner_avatar_with_channel(self):
        testuser = self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_portal")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        testuser2 = self.env["res.users"].create(
            {
                "email": "testuser2@testuser.com",
                "groups_id": [Command.set([self.ref("base.group_user")])],
                "name": "Test User 2",
                "login": "testuser 2",
                "password": "testuser 2",
            }
        )
        partner = self.env["res.users"].browse(testuser.id).partner_id
        partner2 = self.env["res.users"].browse(testuser2.id).partner_id
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel.add_members(partner_ids=[partner.id, partner2.id])
        res = self.url_open(url=self.get_avatar_url(partner2))
        self.assertEqual(res.headers["Content-Disposition"], f'inline; filename="{partner2.name}.svg"')

    def test_portal_open_left_member_avatar(self):
        self.authenticate(None, None)
        guest = self.env["mail.guest"].create({"name": "Guest 1"})
        user_1, portal_user = self.env["res.users"].create(
            [
                {
                    "email": "testuser1@testuser.com",
                    "name": "Test User 1",
                    "groups_id": [Command.set([self.ref("base.group_user")])],
                    "login": "testuser1",
                    "password": "testuser1",
                },
                {
                    "email": "testuser2@testuser.com",
                    "groups_id": [Command.set([self.ref("base.group_portal")])],
                    "name": "Test User 2",
                    "login": "testuser2",
                    "password": "testuser2",
                },
            ]
        )
        partner = user_1.partner_id
        channel = self.env["discuss.channel"].create(
            {
                "channel_type": "group",
                "name": "Test channel",
            }
        )
        partner_member, guest_member = channel.add_members(
            partner_ids=[partner.id], guest_ids=[guest.id]
        )
        channel.message_post(
            body="Test",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=partner.id,
        )
        channel.with_user(self.env.ref('base.public_user')).with_context(guest=guest).message_post(
            body="Test",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        (partner_member + guest_member).unlink()
        self.authenticate(portal_user.login, portal_user.login)
        for author in [guest, partner]:
            res = self.url_open(url=self.get_avatar_url(author))
            self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")
        channel.add_members(partner_ids=[portal_user.partner_id.id])
        for author in [guest, partner]:
            res = self.url_open(url=self.get_avatar_url(author))
            self.assertEqual(
                res.headers["Content-Disposition"], f'inline; filename="{author.name}.svg"'
            )
