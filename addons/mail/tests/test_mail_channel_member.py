# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError

mail_channel_new_test_user = partial(mail_new_test_user, context={'mail_channel_nosubscribe': False})


class TestMailChannelMembers(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailChannelMembers, cls).setUpClass()

        cls.secret_group = cls.env['res.groups'].create({
            'name': 'Secret User Group',
        })
        cls.env['ir.model.data'].create({
            'name': 'secret_group',
            'module': 'mail',
            'model': cls.secret_group._name,
            'res_id': cls.secret_group.id,
        })

        cls.user_1 = mail_channel_new_test_user(
            cls.env, login='user_1',
            name='User 1',
            groups='base.group_user,mail.secret_group')
        cls.user_2 = mail_channel_new_test_user(
            cls.env, login='user_2',
            name='User 2',
            groups='base.group_user,mail.secret_group')
        cls.user_3 = mail_channel_new_test_user(
            cls.env, login='user_3',
            name='User 3',
            groups='base.group_user,mail.secret_group')
        cls.user_portal = mail_channel_new_test_user(
            cls.env, login='user_portal',
            name='User Portal',
            groups='base.group_portal')
        cls.user_public = mail_channel_new_test_user(
            cls.env, login='user_ublic',
            name='User Public',
            groups='base.group_public')

        cls.private_channel = cls.env['mail.channel'].create({
            'name': 'Secret channel',
            'public': 'private',
            'channel_type': 'channel',
        })
        cls.group_channel = cls.env['mail.channel'].create({
            'name': 'Group channel',
            'public': 'groups',
            'channel_type': 'channel',
            'group_public_id': cls.secret_group.id,
        })
        cls.public_channel = cls.env['mail.channel'].create({
            'name': 'Public channel of user 1',
            'public': 'public',
            'channel_type': 'channel',
        })
        (cls.private_channel | cls.group_channel | cls.public_channel).channel_member_ids.unlink()

    # ------------------------------------------------------------
    # PRIVATE CHANNELS
    # ------------------------------------------------------------

    def test_channel_private_01(self):
        """Test access on private channel."""
        res = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertFalse(res)

        # User 1 can join private channel with SUDO
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        res = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(res.partner_id, self.user_1.partner_id)

        # User 2 can not join private channel
        with self.assertRaises(AccessError):
            self.private_channel.with_user(self.user_2).add_members(self.user_2.partner_id.ids)

        # User 2 can not create a `mail.channel.member` to join the private channel
        with self.assertRaises(AccessError):
            self.env['mail.channel.member'].with_user(self.user_2).create({
                'partner_id': self.user_2.partner_id.id,
                'channel_id': self.private_channel.id,
            })

        # User 2 can not write on `mail.channel.member` to join the private channel
        channel_member = self.env['mail.channel.member'].with_user(self.user_2).search([('partner_id', '=', self.user_2.partner_id.id)])[0]
        with self.assertRaises(AccessError):
            channel_member.channel_id = self.private_channel.id
        with self.assertRaises(AccessError):
            channel_member.write({'channel_id': self.private_channel.id})

        # Even with SUDO, channel_id of channel.member should not be changed.
        with self.assertRaises(AccessError):
            channel_member.sudo().channel_id = self.private_channel.id

        # User 2 can not write on the `partner_id` of `mail.channel.member`
        # of an other partner to join a private channel
        channel_member_1 = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id), ('partner_id', '=', self.user_1.partner_id.id)])
        with self.assertRaises(AccessError):
            channel_member_1.with_user(self.user_2).partner_id = self.user_2.partner_id
        self.assertEqual(channel_member_1.partner_id, self.user_1.partner_id)

        # Even with SUDO, partner_id of channel.member should not be changed.
        with self.assertRaises(AccessError):
            channel_member_1.with_user(self.user_2).sudo().partner_id = self.user_2.partner_id

    def test_channel_private_members(self):
        """Test invitation in private channel part 1 (invite using crud methods)."""
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(len(channel_members), 1)

        # User 2 is not in the private channel, they can not invite user 3
        with self.assertRaises(AccessError):
            self.env['mail.channel.member'].with_user(self.user_2).create({
                'partner_id': self.user_portal.partner_id.id,
                'channel_id': self.private_channel.id,
            })

        # User 1 is in the private channel, they can invite other users
        self.env['mail.channel.member'].with_user(self.user_1).create({
            'partner_id': self.user_portal.partner_id.id,
            'channel_id': self.private_channel.id,
        })
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_portal.partner_id)

        # But User 3 can not write on the `mail.channel.member` of other user
        channel_member_1 = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id), ('partner_id', '=', self.user_1.partner_id.id)])
        channel_member_3 = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id), ('partner_id', '=', self.user_portal.partner_id.id)])
        channel_member_3.with_user(self.user_portal).custom_channel_name = 'Test'
        with self.assertRaises(AccessError):
            channel_member_1.with_user(self.user_2).custom_channel_name = 'Blabla'
        self.assertNotEqual(channel_member_1.custom_channel_name, 'Blabla')

    def test_channel_private_invite(self):
        """Test invitation in private channel part 2 (use `invite` action)."""
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # User 2 is not in the channel, they can not invite user_portal
        with self.assertRaises(AccessError):
            self.private_channel.with_user(self.user_2).add_members(self.user_portal.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # User 1 is in the channel, they can invite user_portal
        self.private_channel.with_user(self.user_1).add_members(self.user_portal.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_portal.partner_id)

    def test_channel_private_leave(self):
        """Test kick/leave channel."""
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        self.private_channel.with_user(self.user_portal).sudo().add_members(self.user_portal.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(len(channel_members), 2)

        # User 2 is not in the channel, they can not kick user 1
        with self.assertRaises(AccessError):
            channel_members.with_user(self.user_2).unlink()

        # User 3 is in the channel, they can kick user 1
        channel_members.with_user(self.user_portal).unlink()

    # ------------------------------------------------------------
    # GROUP BASED CHANNELS
    # ------------------------------------------------------------

    def test_group_restricted_channel(self):
        """Test basics on group channel."""
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.group_channel.id)])
        self.assertFalse(channel_members)

        # user 1 is in the group, they can join the channel
        self.group_channel.with_user(self.user_1).add_members(self.user_1.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # user 3 is not in the group, they can not join
        with self.assertRaises(AccessError):
            self.group_channel.with_user(self.user_portal).add_members(self.user_portal.partner_id.ids)

        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.group_channel.id)])
        with self.assertRaises(AccessError):
            channel_members.with_user(self.user_portal).partner_id = self.user_portal.partner_id

        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # user 1 can not invite user 3 because they are not in the group
        with self.assertRaises(UserError):
            self.group_channel.with_user(self.user_1).add_members(self.user_portal.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        # but user 2 is in the group and can be invited by user 1
        self.group_channel.with_user(self.user_1).add_members(self.user_2.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

    # ------------------------------------------------------------
    # PUBLIC CHANNELS
    # ------------------------------------------------------------

    def test_public_channel(self):
        """ Test access on public channels """
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.public_channel.id)])
        self.assertFalse(channel_members)

        self.public_channel.with_user(self.user_1).add_members(self.user_1.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id)

        self.public_channel.with_user(self.user_2).add_members(self.user_2.partner_id.ids)
        channel_members = self.env['mail.channel.member'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_members.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

        # portal/public users still cannot join a public channel, should go through dedicated controllers
        with self.assertRaises(AccessError):
            self.public_channel.with_user(self.user_portal).add_members(self.user_portal.partner_id.ids)
        with self.assertRaises(AccessError):
            self.public_channel.with_user(self.user_public).add_members(self.user_public.partner_id.ids)

    def test_channel_member_invite_with_guest(self):
        guest = self.env['mail.guest'].create({'name': 'Guest'})
        partner = self.env['res.partner'].create({
            'name': 'ToInvite',
            'active': True,
            'type': 'contact',
            'user_ids': self.user_1,
        })
        self.public_channel.add_members(guest_ids=[guest.id])
        search = self.env['res.partner'].search_for_channel_invite(partner.name, channel_id=self.public_channel.id)
        self.assertEqual(len(search['partners']), 1)
        self.assertEqual(search['partners'][0]['id'], partner.id)

    # ------------------------------------------------------------
    # UNREAD COUNTER TESTS
    # ------------------------------------------------------------

    def test_unread_counter_with_message_post(self):
        channel_as_user_1 = self.env['mail.channel'].with_user(self.user_1).create({
            'name': 'Secret channel',
            'public': 'public',
            'channel_type': 'channel',
        })
        channel_as_user_1.with_user(self.user_1).add_members(self.user_1.partner_id.ids)
        channel_as_user_1.with_user(self.user_1).add_members(self.user_2.partner_id.ids)
        channel_1_rel_user_2 = self.env['mail.channel.member'].search([
            ('channel_id', '=', channel_as_user_1.id),
            ('partner_id', '=', self.user_2.partner_id.id)
        ])
        self.assertEqual(channel_1_rel_user_2.message_unread_counter, 0, "should not have unread message initially as notification type is ignored")

        channel_as_user_1.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_1_rel_user_2 = self.env['mail.channel.member'].search([
            ('channel_id', '=', channel_as_user_1.id),
            ('partner_id', '=', self.user_2.partner_id.id)
        ])
        self.assertEqual(channel_1_rel_user_2.message_unread_counter, 1, "should have 1 unread message after someone else posted a message")

    def test_unread_counter_with_message_post_multi_channel(self):
        channel_1_as_user_1 = self.env['mail.channel'].with_user(self.user_1).create({
            'name': 'wololo channel',
            'public': 'public',
            'channel_type': 'channel',
        })
        channel_2_as_user_2 = self.env['mail.channel'].with_user(self.user_2).create({
            'name': 'walala channel',
            'public': 'public',
            'channel_type': 'channel',
        })
        channel_1_as_user_1.add_members(self.user_2.partner_id.ids)
        channel_2_as_user_2.add_members(self.user_1.partner_id.ids)
        channel_2_as_user_2.add_members(self.user_3.partner_id.ids)
        channel_1_as_user_1.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_1_as_user_1.message_post(body='Test 2', message_type='comment', subtype_xmlid='mail.mt_comment')
        channel_2_as_user_2.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        members = self.env['mail.channel.member'].search([('channel_id', 'in', (channel_1_as_user_1 + channel_2_as_user_2).ids)], order="id")
        self.assertEqual(members.mapped('message_unread_counter'), [
            0,  # channel 1 user 1: posted last message
            0,  # channel 2 user 2: posted last message
            2,  # channel 1 user 2: received 2 messages (from message post)
            1,  # channel 2 user 1: received 1 message (from message post)
            1,  # channel 2 user 3: received 1 message (from message post)
        ])
