# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError


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

        cls.user_1 = mail_new_test_user(
            cls.env, login='user_1',
            name='User 1',
            groups='base.group_user,mail.secret_group')
        cls.user_2 = mail_new_test_user(
            cls.env, login='user_2',
            name='User 2',
            groups='base.group_user,mail.secret_group')
        cls.user_portal = mail_new_test_user(
            cls.env, login='user_portal',
            name='User Portal',
            groups='base.group_portal')
        cls.user_public = mail_new_test_user(
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
        (cls.private_channel | cls.group_channel | cls.public_channel).channel_last_seen_partner_ids.unlink()

    # ------------------------------------------------------------
    # PRIVATE CHANNELS
    # ------------------------------------------------------------

    def test_channel_private_01(self):
        """Test access on private channel."""
        res = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertFalse(res)

        # User 1 can join private channel with SUDO
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        res = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(res.partner_id, self.user_1.partner_id)

        # User 2 can not join private channel
        with self.assertRaises(AccessError):
            self.private_channel.with_user(self.user_2).add_members(self.user_2.partner_id.ids)

        # User 2 can not create a `mail.channel.partner` to join the private channel
        with self.assertRaises(AccessError):
            self.env['mail.channel.partner'].with_user(self.user_2).create({
                'partner_id': self.user_2.partner_id.id,
                'channel_id': self.private_channel.id,
            })

        # User 2 can not write on `mail.channel.partner` to join the private channel
        channel_partner = self.env['mail.channel.partner'].with_user(self.user_2).search([('partner_id', '=', self.user_2.partner_id.id)])[0]
        with self.assertRaises(AccessError):
            channel_partner.channel_id = self.private_channel.id
        with self.assertRaises(AccessError):
            channel_partner.write({'channel_id': self.private_channel.id})

        # Even with SUDO, channel_id of channel.partner should not be changed.
        with self.assertRaises(AccessError):
            channel_partner.sudo().channel_id = self.private_channel.id

        # User 2 can not write on the `partner_id` of `mail.channel.partner`
        # of an other partner to join a private channel
        channel_partner_1 = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id), ('partner_id', '=', self.user_1.partner_id.id)])
        with self.assertRaises(AccessError):
            channel_partner_1.with_user(self.user_2).partner_id = self.user_2.partner_id
        self.assertEqual(channel_partner_1.partner_id, self.user_1.partner_id)

        # Even with SUDO, partner_id of channel.partner should not be changed.
        with self.assertRaises(AccessError):
            channel_partner_1.with_user(self.user_2).sudo().partner_id = self.user_2.partner_id

    def test_channel_private_members(self):
        """Test invitation in private channel part 1 (invite using crud methods)."""
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(len(channel_partners), 1)

        # User 2 is not in the private channel, he can not invite user 3
        with self.assertRaises(AccessError):
            self.env['mail.channel.partner'].with_user(self.user_2).create({
                'partner_id': self.user_portal.partner_id.id,
                'channel_id': self.private_channel.id,
            })

        # User 1 is in the private channel, he can invite other users
        self.env['mail.channel.partner'].with_user(self.user_1).create({
            'partner_id': self.user_portal.partner_id.id,
            'channel_id': self.private_channel.id,
        })
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_portal.partner_id)

        # But User 3 can not write on the `mail.channel.partner` of other user
        channel_partner_1 = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id), ('partner_id', '=', self.user_1.partner_id.id)])
        channel_partner_3 = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id), ('partner_id', '=', self.user_portal.partner_id.id)])
        channel_partner_3.with_user(self.user_portal).custom_channel_name = 'Test'
        with self.assertRaises(AccessError):
            channel_partner_1.with_user(self.user_2).custom_channel_name = 'Blabla'
        self.assertNotEqual(channel_partner_1.custom_channel_name, 'Blabla')

    def test_channel_private_invite(self):
        """Test invitation in private channel part 2 (use `invite` action)."""
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # User 2 is not in the channel, he can not invite user_portal
        with self.assertRaises(AccessError):
            self.private_channel.with_user(self.user_2).add_members(self.user_portal.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # User 1 is in the channel, he can invite user_portal
        self.private_channel.with_user(self.user_1).add_members(self.user_portal.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_portal.partner_id)

    def test_channel_private_leave(self):
        """Test kick/leave channel."""
        self.private_channel.with_user(self.user_1).sudo().add_members(self.user_1.partner_id.ids)
        self.private_channel.with_user(self.user_portal).sudo().add_members(self.user_portal.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel.id)])
        self.assertEqual(len(channel_partners), 2)

        # User 2 is not in the channel, he can not kick user 1
        with self.assertRaises(AccessError):
            channel_partners.with_user(self.user_2).unlink()

        # User 3 is in the channel, he can kick user 1
        channel_partners.with_user(self.user_portal).unlink()

    # ------------------------------------------------------------
    # GROUP BASED CHANNELS
    # ------------------------------------------------------------

    def test_channel_group(self):
        """Test basics on group channel."""
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertFalse(channel_partners)

        # user 1 is in the group, he can join the channel
        self.group_channel.with_user(self.user_1).add_members(self.user_1.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # user 3 is not in the group, he can not join
        with self.assertRaises(AccessError):
            self.group_channel.with_user(self.user_portal).add_members(self.user_portal.partner_id.ids)

        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        with self.assertRaises(AccessError):
            channel_partners.with_user(self.user_portal).partner_id = self.user_portal.partner_id

        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # user 1 can not invite user 3 because he's not in the group
        with self.assertRaises(UserError):
            self.group_channel.with_user(self.user_1).add_members(self.user_portal.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # but user 2 is in the group and can be invited by user 1
        self.group_channel.with_user(self.user_1).add_members(self.user_2.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

    # ------------------------------------------------------------
    # PUBLIC CHANNELS
    # ------------------------------------------------------------

    def test_channel_public(self):
        """ Test access on public channels """
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel.id)])
        self.assertFalse(channel_partners)

        self.public_channel.with_user(self.user_1).add_members(self.user_1.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        self.public_channel.with_user(self.user_2).add_members(self.user_2.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

        # portal/public users still cannot join a public channel, should go through dedicated controllers
        with self.assertRaises(AccessError):
            self.public_channel.with_user(self.user_portal).add_members(self.user_portal.partner_id.ids)
        with self.assertRaises(AccessError):
            self.public_channel.with_user(self.user_public).add_members(self.user_public.partner_id.ids)

    def test_channel_partner_invite_with_guest(self):
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
