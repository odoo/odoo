# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import new_test_user


class TestDiscussChannelMember(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.secret_group = cls.env['res.groups'].create({
            'name': 'Secret User Group',
        })
        cls.env['ir.model.data'].create({
            'name': 'secret_group',
            'module': 'mail',
            'model': cls.secret_group._name,
            'res_id': cls.secret_group.id,
        })
        cls.user_1 = new_test_user(
            cls.env, login="user_1", name="User 1", groups="base.group_user,mail.secret_group"
        )
        cls.user_2 = new_test_user(
            cls.env, login="user_2", name="User 2", groups="base.group_user,mail.secret_group"
        )
        cls.user_3 = new_test_user(
            cls.env, login="user_3", name="User 3", groups="base.group_user,mail.secret_group"
        )
        cls.group = cls.env["discuss.channel"].create({"name": "Group", "channel_type": "group"})
        cls.group.channel_member_ids.unlink()

    def test_cannot_change_member_immutable_fields(self):
        channel = self.env["discuss.channel"]._create_channel(group_id=None, name="General")
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        another_channel = self.env["discuss.channel"]._create_channel(group_id=None, name="Another channel")
        another_partner = self.env["res.partner"].create({"name": "John"})
        guest = self.env["mail.guest"].create({"name": "Jane"})
        member = channel._add_members(users=bob)
        with self.assertRaises(AccessError):
            member.channel_id = another_channel
        with self.assertRaises(AccessError):
            member.partner_id = another_partner
        with self.assertRaises(AccessError):
            member.guest_id = guest

    def test_user_public_cannot_join_channel(self):
        channel = self.env["discuss.channel"]._create_channel(group_id=None, name="Public")
        public = new_test_user(self.env, "public_user", groups="base.group_public")
        with self.assertRaises(ValidationError):
            channel._add_members(users=public)

    # ------------------------------------------------------------
    # GROUP
    # ------------------------------------------------------------

    def test_group_subchannel_join(self):
        """Test join subchannel."""
        self.group.add_members((self.user_1 | self.user_2).partner_id.ids)
        group_subchannel = self.group.with_user(self.user_1)._create_sub_channel()
        group_subchannel.with_user(self.user_2).add_members(self.user_2.partner_id.id)
        self.assertEqual(group_subchannel.channel_member_ids.partner_id, (self.user_1 | self.user_2).partner_id)

    # ------------------------------------------------------------
    # PUBLIC CHANNELS
    # ------------------------------------------------------------

    def test_channel_member_invite_with_guest(self):
        public_channel = self.env["discuss.channel"]._create_channel(group_id=None, name="Public")
        guest = self.env['mail.guest'].create({'name': 'Guest'})
        partner = self.env['res.partner'].create({
            'name': 'ToInvite',
            'active': True,
            'type': 'contact',
            'user_ids': self.user_1,
        })
        public_channel._add_members(guests=guest)
        data = self.env["res.partner"].search_for_channel_invite(
            partner.name,
            channel_id=public_channel.id,
        )["store_data"]
        self.assertEqual(len(data["res.partner"]), 1)
        self.assertEqual(data["res.partner"][0]["id"], partner.id)

    # ------------------------------------------------------------
    # UNREAD COUNTER TESTS
    # ------------------------------------------------------------

    def test_unread_counter_with_message_post(self):
        channel_as_user_1 = self.env['discuss.channel'].with_user(self.user_1)._create_channel(group_id=None, name='Public channel')
        channel_as_user_1.with_user(self.user_1)._add_members(users=self.user_1)
        channel_as_user_1.with_user(self.user_1)._add_members(users=self.user_2)
        channel_1_rel_user_2 = self.env['discuss.channel.member'].search([
            ('channel_id', '=', channel_as_user_1.id),
            ('partner_id', '=', self.user_2.partner_id.id)
        ])
        self.assertEqual(channel_1_rel_user_2.message_unread_counter, 0, "should not have unread message initially as notification type is ignored")

        channel_as_user_1.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_1_rel_user_2 = self.env['discuss.channel.member'].search([
            ('channel_id', '=', channel_as_user_1.id),
            ('partner_id', '=', self.user_2.partner_id.id)
        ])
        self.assertEqual(channel_1_rel_user_2.message_unread_counter, 1, "should have 1 unread message after someone else posted a message")

    def test_unread_counter_with_message_post_multi_channel(self):
        channel_1_as_user_1 = self.env['discuss.channel'].with_user(self.user_1)._create_channel(group_id=None, name='wololo channel')
        channel_2_as_user_2 = self.env['discuss.channel'].with_user(self.user_2)._create_channel(group_id=None, name='walala channel')
        channel_1_as_user_1._add_members(users=self.user_2)
        channel_2_as_user_2._add_members(users=self.user_1)
        channel_2_as_user_2._add_members(users=self.user_3)
        channel_1_as_user_1.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_1_as_user_1.message_post(body='Test 2', message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_2_as_user_2.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        members = self.env['discuss.channel.member'].search([('channel_id', 'in', (channel_1_as_user_1 + channel_2_as_user_2).ids)], order="id")
        self.assertEqual(members.mapped('message_unread_counter'), [
            0,  # channel 1 user 1: posted last message
            0,  # channel 2 user 2: posted last message
            2,  # channel 1 user 2: received 2 messages (from message post)
            1,  # channel 2 user 1: received 1 message (from message post)
            1,  # channel 2 user 3: received 1 message (from message post)
        ])
