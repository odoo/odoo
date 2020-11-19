# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.tests.common import SavepointCase
from odoo.exceptions import AccessError


class TestMailSecurity(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secret_group = cls.env['res.groups'].create({
            'name': 'secret group',
        })
        cls.user_1 = cls.env['res.users'].create({
            'name': 'User 1',
            'login': 'user_1',
            'email': '---',
            'groups_id': [(6, 0, [cls.secret_group.id, cls.env.ref('base.group_user').id])],
        })
        cls.user_2 = cls.env['res.users'].create({
            'name': 'User 2',
            'login': 'user_2',
            'email': '---',
            'groups_id': [(6, 0, [cls.secret_group.id, cls.env.ref('base.group_user').id])],
        })
        cls.user_3 = cls.env['res.users'].create({
            'name': 'User 3',
            'login': 'user_3',
            'email': '---',
        })

        cls.private_channel_1 = cls.env['mail.channel'].create({
            'name': 'Secret channel',
            'public': 'private',
            'channel_type': 'channel',
        })
        cls.group_channel_1 = cls.env['mail.channel'].create({
            'name': 'Group channel',
            'public': 'groups',
            'channel_type': 'channel',
            'group_public_id': cls.secret_group.id,
        })
        cls.public_channel_1 = cls.env['mail.channel'].create({
            'name': 'Public channel of user 1',
            'public': 'public',
            'channel_type': 'channel',
        })
        cls.private_channel_1.channel_last_seen_partner_ids.unlink()
        cls.group_channel_1.channel_last_seen_partner_ids.unlink()
        cls.public_channel_1.channel_last_seen_partner_ids.unlink()

    ###########################
    # PRIVATE CHANNEL & BASIC #
    ###########################

    def test_channel_acls_01(self):
        """Test access on private channel."""
        res = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertFalse(res)

        # User 1 can join private channel with SUDO
        self.private_channel_1.with_user(self.user_1).sudo().action_follow()
        res = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertEqual(res.partner_id, self.user_1.partner_id)

        # User 2 can not join private channel
        with self.assertRaises(AccessError):
            self.private_channel_1.with_user(self.user_2).action_follow()

        # But user 2 can join public channel
        self.public_channel_1.with_user(self.user_2).action_follow()
        res = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel_1.id)])
        self.assertEqual(res.partner_id, self.user_2.partner_id)

        # User 2 can not create a `mail.channel.partner` to join the private channel
        with self.assertRaises(AccessError):
            self.env['mail.channel.partner'].with_user(self.user_2).create({
                'partner_id': self.user_2.partner_id.id,
                'channel_id': self.private_channel_1.id,
            })

        # User 2 can not write on `mail.channel.partner` to join the private channel
        channel_partner = self.env['mail.channel.partner'].with_user(self.user_2).search([('partner_id', '=', self.user_2.partner_id.id)])[0]
        with self.assertRaises(AccessError):
            channel_partner.channel_id = self.private_channel_1.id
        with self.assertRaises(AccessError):
            channel_partner.write({'channel_id': self.private_channel_1.id})

        # But with SUDO, User 2 can
        channel_partner.sudo().channel_id = self.private_channel_1.id

        # User 2 can not write on the `partner_id` of `mail.channel.partner`
        # of an other partner to join a private channel
        channel_partner_1 = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id), ('partner_id', '=', self.user_1.partner_id.id)])
        with self.assertRaises(AccessError):
            channel_partner_1.with_user(self.user_2).partner_id = self.user_2.partner_id
        self.assertEqual(channel_partner_1.partner_id, self.user_1.partner_id)

        # but with SUDO he can...
        channel_partner_1.with_user(self.user_2).sudo().partner_id = self.user_2.partner_id
        self.assertEqual(channel_partner_1.partner_id, self.user_2.partner_id)

    def test_channel_acls_03(self):
        """Test invitation in private channel part 1 (invite using crud methods)."""
        self.private_channel_1.with_user(self.user_1).sudo().action_follow()
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertEqual(len(channel_partners), 1)

        # User 2 is not in the private channel, he can not invite user 3
        with self.assertRaises(AccessError):
            self.env['mail.channel.partner'].with_user(self.user_2).create({
                'partner_id': self.user_3.partner_id.id,
                'channel_id': self.private_channel_1.id,
            })

        # User 1 is in the private channel, he can invite other users
        self.env['mail.channel.partner'].with_user(self.user_1).create({
            'partner_id': self.user_3.partner_id.id,
            'channel_id': self.private_channel_1.id,
        })
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_3.partner_id)

        # But User 3 can not write on the `mail.channel.partner` of other user
        channel_partner_1 = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id), ('partner_id', '=', self.user_1.partner_id.id)])
        channel_partner_3 = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id), ('partner_id', '=', self.user_3.partner_id.id)])
        channel_partner_3.with_user(self.user_3).custom_channel_name = 'Test'
        with self.assertRaises(AccessError):
            channel_partner_1.with_user(self.user_2).custom_channel_name = 'Blabla'
        self.assertNotEqual(channel_partner_1.custom_channel_name, 'Blabla')

    def test_channel_acls_04(self):
        """Test invitation in private channel part 2 (use `invite` action)."""
        self.private_channel_1.with_user(self.user_1).sudo().action_follow()
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # User 2 is not in the channel, he can not invite user 3
        with self.assertRaises(AccessError):
            self.private_channel_1.with_user(self.user_2).channel_invite([self.user_3.partner_id.id])
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # User 1 is in the channel, he can not invite user 3
        self.private_channel_1.with_user(self.user_1).channel_invite([self.user_3.partner_id.id])
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_3.partner_id)

    def test_channel_acls_05(self):
        """Test kick/leave channel."""
        self.private_channel_1.with_user(self.user_1).sudo().action_follow()
        self.private_channel_1.with_user(self.user_3).sudo().action_follow()
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.private_channel_1.id)])
        self.assertEqual(len(channel_partners), 2)

        # User 2 is not in the channel, he can not kick user 1
        with self.assertRaises(AccessError):
            channel_partners.with_user(self.user_2).unlink()

        # User 3 is in the channel, he can kick user 1
        channel_partners.with_user(self.user_3).unlink()

    #################
    # GROUP CHANNEL #
    #################
    def test_channel_acls_06(self):
        """Test basics on group channel."""
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel_1.id)])
        self.assertFalse(channel_partners)

        # user 1 is in the group, he can join the channel
        self.group_channel_1.with_user(self.user_1).action_follow()
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # user 3 is not in the group, he can not join
        with self.assertRaises(AccessError):
            self.group_channel_1.with_user(self.user_3).action_follow()

        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel_1.id)])
        with self.assertRaises(AccessError):
            channel_partners.with_user(self.user_3).partner_id = self.user_3.partner_id

        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # user 1 can not invite user 3 because he's not in the group
        with self.assertRaises(AccessError):
            self.group_channel_1.with_user(self.user_1).channel_invite([self.user_3.partner_id.id])
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # but user 2 is in the group and can be invited by user 1
        self.group_channel_1.with_user(self.user_1).channel_invite([self.user_2.partner_id.id])
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

    ##################
    # PUBLIC CHANNEL #
    ##################
    def test_channel_acls_07(self):
        """Test basics on public channel."""
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel_1.id)])
        self.assertFalse(channel_partners)

        self.public_channel_1.with_user(self.user_1).action_follow()
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        self.public_channel_1.with_user(self.user_2).action_follow()
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel_1.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)
