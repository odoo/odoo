# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.tests import HttpCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestAvatarAcl(HttpCase):
    def get_avatar_url(self, record, add_token=False):
        access_token = ""
        if add_token:
            access_token = f"&access_token={record._get_avatar_128_access_token()}"
        return f"/web/image?field=avatar_128&id={record.id}&model={record._name}&unique={fields.Datetime.to_string(record.write_date)}{access_token}"

    def test_partner_open_guest_avatar(self):
        self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "group_ids": [Command.set([self.ref("base.group_user")])],
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
                "group_ids": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        guest = self.env["mail.guest"].create({"name": "Guest"})
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel._add_members(guests=guest, users=testuser)
        res = self.url_open(url=self.get_avatar_url(guest))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=Guest.svg")

    def test_guest_open_partner_avatar(self):
        self.authenticate(None, None)
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
        testuser = self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "group_ids": [Command.set([self.ref("base.group_user")])],
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
                "group_ids": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel._add_members(guests=guest, users=testuser)
        res = self.url_open(url=self.get_avatar_url(testuser.partner_id))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")
        res = self.url_open(url=self.get_avatar_url(testuser.partner_id, add_token=True))
        self.assertEqual(res.headers["Content-Disposition"], f'inline; filename="{testuser.partner_id.name}.svg"')

    def test_partner_open_partner_avatar(self):
        testuser = self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "group_ids": [Command.set([self.ref("base.group_user")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        testuser2 = self.env["res.users"].create(
            {
                "email": "testuser2@testuser.com",
                "group_ids": [Command.set([self.ref("base.group_user")])],
                "name": "Test User 2",
                "login": "testuser 2",
                "password": "testuser 2",
            }
        )
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel._add_members(users=testuser | testuser2)
        res = self.url_open(url=self.get_avatar_url(testuser2.partner_id))
        self.assertEqual(res.headers["Content-Disposition"], f'inline; filename="{testuser2.partner_id.name}.svg"')

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
        channel._add_members(guests=guest | guest2)
        res = self.url_open(url=self.get_avatar_url(guest2))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")
        res = self.url_open(url=self.get_avatar_url(guest2, add_token=True))
        self.assertEqual(res.headers["Content-Disposition"], 'inline; filename="Guest 2.svg"')

    def test_portal_open_partner_avatar(self):
        self.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "group_ids": [Command.set([self.ref("base.group_portal")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        testuser2 = self.env["res.users"].create(
            {
                "email": "testuser2@testuser.com",
                "group_ids": [Command.set([self.ref("base.group_user")])],
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
                "group_ids": [Command.set([self.ref("base.group_portal")])],
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            }
        )
        self.authenticate("testuser", "testuser")
        testuser2 = self.env["res.users"].create(
            {
                "email": "testuser2@testuser.com",
                "group_ids": [Command.set([self.ref("base.group_user")])],
                "name": "Test User 2",
                "login": "testuser 2",
                "password": "testuser 2",
            }
        )
        channel = self.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        channel._add_members(users=testuser | testuser2)
        res = self.url_open(url=self.get_avatar_url(testuser2.partner_id))
        self.assertEqual(res.headers["Content-Disposition"], "inline; filename=placeholder.png")
        res = self.url_open(url=self.get_avatar_url(testuser2.partner_id, add_token=True))
        self.assertEqual(res.headers["Content-Disposition"], f'inline; filename="{testuser2.partner_id.name}.svg"')
