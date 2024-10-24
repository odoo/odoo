# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_binary_controller import TestBinaryControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestDiscussBinaryControllerCommon(TestBinaryControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env["discuss.channel"].create({"name": "Group", "channel_type": "group"})

    def _execute_options(self, options, data_user, record):
        if options.get("with_channel"):
            self._add_member([data_user, record])
        if options.get("join_channel"):
            self._add_member([data_user])
        if options.get("member_left"):
            record_member = self._add_member([record])
            user = record if record._name == "res.users" else self.user_public
            guest = record if record._name == "mail.guest" else self.env["mail.guest"]
            self._authenticate_user(user=user, guest=guest)
            self.make_jsonrpc_request(
                route="/mail/message/post",
                params={
                    "thread_model": self.group._name,
                    "thread_id": self.group.id,
                    "post_data": {
                        "body": "Test",
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_comment",
                    },
                },
            )
            record_member.unlink()

    def _add_member(self, members):
        partner_ids = []
        guest_ids = []
        for member in members:
            if member._name == "res.users":
                partner_ids.append(member.partner_id.id)
            else:
                guest_ids.append(member.id)
        return self.group.add_members(partner_ids, guest_ids)


@odoo.tests.tagged("-at_install", "post_install")
class TestDiscussBinaryController(TestDiscussBinaryControllerCommon):

    def test_open_guest_avatar_with_channel(self):
        """Test access to open a guest avatar in a common channel."""
        self._execute_subtests(
            self.guest_2,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
            {"with_channel": True},
        )

    def test_open_partner_avatar_with_channel(self):
        """Test access to open a partner avatar in a common channel."""
        self._execute_subtests(
            self.test_user,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
            {"with_channel": True},
        )

    def test_open_left_guest_avatar(self):
        """Test access to open a left guest avatar in a channel."""
        self._execute_subtests(
            self.guest_2,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
            {"member_left": True},
        )
        self._execute_subtests(
            self.guest_2,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
            {"member_left": True, "join_channel": True},
        )

    def test_open_left_partner_avatar(self):
        """Test access to open a left partner avatar in a channel."""
        self._execute_subtests(
            self.test_user,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
            {"member_left": True},
        )
        self._execute_subtests(
            self.test_user,
            (
                (self.user_public, False),
                (self.guest, True),
                (self.user_portal, True),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
            {"member_left": True, "join_channel": True},
        )
