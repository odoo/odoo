# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_binary_controller import TestBinaryControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestDiscussBinaryControllerCommon(TestBinaryControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_channel = cls.env["discuss.channel"].create(
            {"name": "Private Channel", "channel_type": "group"}
        )
        cls.public_channel = cls.env["discuss.channel"].channel_create(
            name="Public Channel", group_id=None
        )
        cls.partner_ids = (
            cls.user_public + cls.user_portal + cls.user_employee + cls.user_demo + cls.user_admin
        ).partner_id.ids


@odoo.tests.tagged("-at_install", "post_install")
class TestDiscussBinaryController(TestDiscussBinaryControllerCommon):
    def test_open_guest_avatar(self):
        """Test access to open the avatar of a guest.
        There is no common channel or any interaction from the guest."""
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
        )

    def test_01_guest_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: False"""
        self.private_channel.add_members(self.partner_ids, (self.guest + self.guest_2).ids)
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
        )

    def test_01_partner_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: partner
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: False"""
        self.private_channel.add_members(
            self.partner_ids + [self.user_test.partner_id.id], self.guest.id
        )
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_02_guest_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: True"""
        self.private_channel.add_members(self.partner_ids, (self.guest + self.guest_2).ids)
        self._send_message(self.guest_2, self.private_channel._name, self.private_channel.id)
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
        )

    def test_02_partner_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: partner
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: True"""
        self.private_channel.add_members(
            self.partner_ids + [self.user_test.partner_id.id], self.guest.id
        )
        self._send_message(self.user_test, self.private_channel._name, self.private_channel.id)
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_03_guest_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: False
        - target leaves the channel: True"""
        self.private_channel.add_members(self.partner_ids, (self.guest + self.guest_2).ids)
        self.env["discuss.channel.member"].search(
            [("guest_id", "=", self.guest_2.id), ("channel_id", "=", self.private_channel.id)]
        ).unlink()
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
        )

    def test_03_partner_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: partner
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: False
        - target leaves the channel: True"""
        self.private_channel.add_members(
            self.partner_ids + [self.user_test.partner_id.id], self.guest.id
        )
        self.env["discuss.channel.member"].search(
            [
                ("partner_id", "=", self.user_test.partner_id.id),
                ("channel_id", "=", self.private_channel.id),
            ]
        ).unlink()
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_04_guest_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: True
        - target leaves the channel: True"""
        self.private_channel.add_members(self.partner_ids, (self.guest + self.guest_2).ids)
        self._send_message(self.guest_2, self.private_channel._name, self.private_channel.id)
        self.env["discuss.channel.member"].search(
            [("guest_id", "=", self.guest_2.id), ("channel_id", "=", self.private_channel.id)]
        ).unlink()
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
        )

    def test_04_partner_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: partner
        - channel type: group
        - target joins the channel: True
        - other users join the channel: True
        - target sends a message: True
        - target leaves the channel: True"""
        self.private_channel.add_members(
            self.partner_ids + [self.user_test.partner_id.id], self.guest.id
        )
        self._send_message(self.user_test, self.private_channel._name, self.private_channel.id)
        self.env["discuss.channel.member"].search(
            [
                ("partner_id", "=", self.user_test.partner_id.id),
                ("channel_id", "=", self.private_channel.id),
            ]
        ).unlink()
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_05_guest_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: group
        - target joins the channel: False
        - other users join the channel: False
        - target sends a message: True"""
        self.private_channel.with_user(self.user_public).with_context(
            guest=self.guest_2
        ).sudo().message_post(body="Test", subtype_xmlid="mail.mt_comment", message_type="comment")
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
        )

    def test_05_partner_avatar_private_channel(self):
        """Test access to open the avatar:
        - target type: partner
        - channel type: group
        - target joins the channel: False
        - other users join the channel: False
        - target sends a message: True"""
        self.private_channel.message_post(
            body="Test",
            subtype_xmlid="mail.mt_comment",
            message_type="comment",
            author_id=self.user_test.partner_id.id,
        )
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_01_guest_avatar_public_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: public
        - target joins the channel: False
        - other users join the channel: False
        - target sends a message: True"""
        self.public_channel.with_user(self.user_public).with_context(
            guest=self.guest_2
        ).sudo().message_post(body="Test", subtype_xmlid="mail.mt_comment", message_type="comment")
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
        )

    def test_01_partner_avatar_public_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: public
        - target joins the channel: False
        - other users join the channel: False
        - target sends a message: True"""
        self._send_message(self.user_test, self.public_channel._name, self.public_channel.id)
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_02_guest_avatar_public_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: public
        - target joins the channel: True
        - other users join the channel: False
        - target sends a message: False
        - target leaves the channel: True"""
        target_member = self.public_channel.add_members(guest_ids=self.guest_2.id)
        target_member.unlink()
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
        )

    def test_02_partner_avatar_public_channel(self):
        """Test access to open the avatar:
        - target type: partner
        - channel type: public
        - target joins the channel: True
        - other users join the channel: False
        - target sends a message: False
        - target leaves the channel: True"""
        target_member = self.public_channel.add_members(self.user_test.partner_id.id)
        target_member.unlink()
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_03_guest_avatar_public_channel(self):
        """Test access to open the avatar:
        - target type: guest
        - channel type: public
        - target joins the channel: True
        - other users join the channel: False
        - target sends a message: True
        - target leaves the channel: True"""
        target_member = self.public_channel.add_members(guest_ids=self.guest_2.id)
        self._send_message(self.guest_2, self.public_channel._name, self.public_channel.id)
        target_member.unlink()
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
        )

    def test_03_partner_avatar_public_channel(self):
        """Test access to open the avatar:
        - target type: partner
        - channel type: public
        - target joins the channel: True
        - other users join the channel: False
        - target sends a message: True
        - target leaves the channel: True"""
        target_member = self.public_channel.add_members(self.user_test.partner_id.id)
        self._send_message(self.user_test, self.public_channel._name, self.public_channel.id)
        target_member.unlink()
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )
