# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user, tagged


@tagged("post_install", "-at_install")
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
        cls.user_portal = new_test_user(
            cls.env, login="user_portal", name="User Portal", groups="base.group_portal"
        )
        cls.user_public = new_test_user(
            cls.env, login="user_public", name="User Public", groups="base.group_public"
        )


        cls.group = cls.env['discuss.channel'].create({
            'name': 'Group',
            'channel_type': 'group',
        })
        cls.group_restricted_channel = cls.env['discuss.channel'].create({
            'name': 'Group restricted channel',
            'channel_type': 'channel',
            'group_public_id': cls.secret_group.id,
        })
        cls.public_channel = cls.env['discuss.channel']._create_channel(group_id=None, name='Public channel of user 1')
        (cls.group | cls.group_restricted_channel | cls.public_channel).channel_member_ids.unlink()

    # ------------------------------------------------------------
    # GROUP
    # ------------------------------------------------------------

    def test_group_01(self):
        """Test access on group."""
        res = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertFalse(res)

        # User 1 can join group with SUDO
        self.group.with_user(self.user_1).sudo()._add_members(users=self.user_1)
        res = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertEqual(res.partner_id, self.user_1.partner_id)

        # User 2 can not join group
        with self.assertRaises(AccessError):
            self.group.with_user(self.user_2)._add_members(users=self.user_2)

        # User 2 can not create a `discuss.channel.member` to join the group
        with self.assertRaises(AccessError):
            self.env['discuss.channel.member'].with_user(self.user_2).create({
                'partner_id': self.user_2.partner_id.id,
                'channel_id': self.group.id,
            })

        # User 2 can not write on `discuss.channel.member` to join the group
        channel_member = self.env['discuss.channel.member'].with_user(self.user_2).search([('is_self', '=', True)])[0]
        with self.assertRaises(AccessError):
            channel_member.channel_id = self.group.id
        with self.assertRaises(AccessError):
            channel_member.write({'channel_id': self.group.id})

        # Even with SUDO, channel_id of channel.member should not be changed.
        with self.assertRaises(AccessError):
            channel_member.sudo().channel_id = self.group.id

        # User 2 can not write on the `partner_id` of `discuss.channel.member`
        # of an other partner to join a group
        channel_member_1 = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id), ('partner_id', '=', self.user_1.partner_id.id)])
        with self.assertRaises(AccessError):
            channel_member_1.with_user(self.user_2).partner_id = self.user_2.partner_id
        self.assertEqual(channel_member_1.partner_id, self.user_1.partner_id)

        # Even with SUDO, partner_id of channel.member should not be changed.
        with self.assertRaises(AccessError):
            channel_member_1.with_user(self.user_2).sudo().partner_id = self.user_2.partner_id

    def test_group_members(self):
        """Test invitation in group part 1 (invite using crud methods)."""
        self.group.with_user(self.user_1).sudo()._add_members(users=self.user_1)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertEqual(len(channel_members), 1)

        # User 2 is not in the group, they can not invite user 3
        with self.assertRaises(AccessError):
            self.env['discuss.channel.member'].with_user(self.user_2).create({
                'partner_id': self.user_portal.partner_id.id,
                'channel_id': self.group.id,
            })

        # User 1 is in the group, they can invite other users
        self.env['discuss.channel.member'].with_user(self.user_1).create({
            'partner_id': self.user_portal.partner_id.id,
            'channel_id': self.group.id,
        })
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_portal.partner_id)

        # But User 3 can not write on the `discuss.channel.member` of other user
        channel_member_1 = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id), ('partner_id', '=', self.user_1.partner_id.id)])
        channel_member_3 = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id), ('partner_id', '=', self.user_portal.partner_id.id)])
        channel_member_3.with_user(self.user_portal).custom_channel_name = 'Test'
        with self.assertRaises(AccessError):
            channel_member_1.with_user(self.user_2).custom_channel_name = 'Blabla'
        self.assertNotEqual(channel_member_1.custom_channel_name, 'Blabla')

    def test_group_invite(self):
        """Test invitation in group part 2 (use `invite` action)."""
        self.group.with_user(self.user_1).sudo()._add_members(users=self.user_1)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # User 2 is not in the group, they can not invite user_portal
        with self.assertRaises(AccessError):
            self.group.with_user(self.user_2)._add_members(users=self.user_portal)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # User 1 is in the group, they can invite user_portal
        self.group.with_user(self.user_1)._add_members(users=self.user_portal)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_portal.partner_id)

    def test_group_leave(self):
        """Test kick/leave channel."""
        self.group.with_user(self.user_1).sudo()._add_members(users=self.user_1)
        self.group.with_user(self.user_portal).sudo()._add_members(users=self.user_portal)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group.id)])
        self.assertEqual(len(channel_members), 2)

        # User 2 is not in the group, they can not kick user 1
        with self.assertRaises(AccessError):
            channel_members.with_user(self.user_2).unlink()

        # User 3 is in the group, but not admin/owner, they can not kick user 1
        with self.assertRaises(AccessError):
            channel_members.with_user(self.user_portal).unlink()

    # ------------------------------------------------------------
    # GROUP BASED CHANNELS
    # ------------------------------------------------------------

    def test_group_restricted_channel(self):
        """Test basics on group channel."""
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group_restricted_channel.id)])
        self.assertFalse(channel_members)

        # user 1 is in the channel, they can join the channel
        self.group_restricted_channel.with_user(self.user_1)._add_members(users=self.user_1)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group_restricted_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # user 3 is not in the channel, they can not join
        with self.assertRaises(AccessError):
            self.group_restricted_channel.with_user(self.user_portal)._add_members(users=self.user_portal)

        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group_restricted_channel.id)])
        with self.assertRaises(AccessError):
            channel_members.with_user(self.user_portal).partner_id = self.user_portal.partner_id

        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group_restricted_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        self.group_restricted_channel.with_user(self.user_1)._add_members(users=self.user_portal)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group_restricted_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_portal.partner_id)

        # but user 2 is in the channel and can be invited by user 1
        self.group_restricted_channel.with_user(self.user_1)._add_members(users=self.user_2)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.group_restricted_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id | self.user_portal.partner_id)

    # ------------------------------------------------------------
    # PUBLIC CHANNELS
    # ------------------------------------------------------------

    def test_public_channel(self):
        """ Test access on public channels """
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.public_channel.id)])
        self.assertFalse(channel_members)

        self.public_channel.with_user(self.user_1)._add_members(users=self.user_1)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        self.public_channel.with_user(self.user_2)._add_members(users=self.user_2)
        channel_members = self.env['discuss.channel.member'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

        self.public_channel.with_user(self.user_portal)._add_members(users=self.user_portal)
        with self.assertRaises(ValidationError):  # public cannot join without having a guest
            self.public_channel.with_user(self.user_public)._add_members(users=self.user_public)

    def test_channel_member_invite_with_guest(self):
        guest = self.env['mail.guest'].create({'name': 'Guest'})
        partner = self.env['res.partner'].create({
            'name': 'ToInvite',
            'active': True,
            'type': 'contact',
            'user_ids': self.user_1,
        })
        self.public_channel._add_members(guests=guest)
        data = self.env["res.partner"].search_for_channel_invite(
            partner.name, channel_id=self.public_channel.id
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
