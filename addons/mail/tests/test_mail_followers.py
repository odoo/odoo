# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.addons.mail.tests.common import TestMail


class TestMailFollowers(TestMail):

    def setUp(self):
        super(TestMailFollowers, self).setUp()
        Subtype = self.env['mail.message.subtype']
        self.mt_mg_def = Subtype.create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.channel'})
        self.mt_cl_def = Subtype.create({'name': 'mt_cl_def', 'default': True, 'res_model': 'crm.lead'})
        self.mt_al_def = Subtype.create({'name': 'mt_al_def', 'default': True, 'res_model': False})
        self.mt_mg_nodef = Subtype.create({'name': 'mt_mg_nodef', 'default': False, 'res_model': 'mail.channel'})
        self.mt_al_nodef = Subtype.create({'name': 'mt_al_nodef', 'default': False, 'res_model': False})
        self.default_group_subtypes = Subtype.search([('default', '=', True), '|', ('res_model', '=', 'mail.channel'), ('res_model', '=', False)])

    def test_m2o_command_new(self):
        test_channel = self.env['mail.channel'].create({'name': 'Test'})
        groups = self.group_pigs | self.group_public
        generic, specific = self.env['mail.followers']._add_follower_command(
            'mail.channel', groups.ids,
            {self.user_employee.partner_id.id: [self.mt_mg_nodef.id]},
            {test_channel.id: [self.mt_al_nodef.id]})
        self.assertFalse(specific)
        self.assertEqual(len(generic), 2)

        self.assertEqual(set([generic[0][2]['res_model'], generic[1][2]['res_model']]),
                         set(['mail.channel']))
        self.assertEqual(set(filter(None, [generic[0][2].get('channel_id'), generic[1][2].get('channel_id')])),
                         set([test_channel.id]))
        self.assertEqual(set(filter(None, [generic[0][2].get('partner_id'), generic[1][2].get('partner_id')])),
                         set([self.user_employee.partner_id.id]))
        self.assertEqual(set(generic[0][2]['subtype_ids'][0][2] + generic[1][2]['subtype_ids'][0][2]),
                         set([self.mt_mg_nodef.id, self.mt_al_nodef.id]))

    def test_m2o_command_update_selective(self):
        test_channel = self.env['mail.channel'].create({'name': 'Test'})
        groups = self.group_pigs | self.group_public
        self.env['mail.followers'].create({'partner_id': self.user_employee.partner_id.id, 'res_model': 'mail.channel', 'res_id': self.group_pigs.id})
        generic, specific = self.env['mail.followers']._add_follower_command(
            'mail.channel', groups.ids,
            {self.user_employee.partner_id.id: [self.mt_mg_nodef.id]},
            {test_channel.id: False},
            force=False)
        self.assertEqual(len(generic), 1)
        self.assertEqual(len(specific), 1)

        self.assertEqual(generic[0][2]['res_model'], 'mail.channel')
        self.assertEqual(generic[0][2]['channel_id'], test_channel.id)
        self.assertEqual(set(generic[0][2]['subtype_ids'][0][2]), set(self.default_group_subtypes.ids))

        self.assertEqual(specific.keys(), [self.group_public.id])
        self.assertEqual(specific[self.group_public.id][0][2]['res_model'], 'mail.channel')
        self.assertEqual(specific[self.group_public.id][0][2]['partner_id'], self.user_employee.partner_id.id)
        self.assertEqual(set(specific[self.group_public.id][0][2]['subtype_ids'][0][2]), set([self.mt_mg_nodef.id]))

    def test_message_is_follower(self):
        qty_followed_before = len(self.group_pigs.sudo(self.user_employee).search([('message_is_follower', '=', True)]))
        self.assertFalse(self.group_pigs.sudo(self.user_employee).message_is_follower)
        self.group_pigs.message_subscribe_users(user_ids=[self.user_employee.id])
        qty_followed_after = len(self.group_pigs.sudo(self.user_employee).search([('message_is_follower', '=', True)]))
        self.assertTrue(self.group_pigs.sudo(self.user_employee).message_is_follower)
        self.assertEqual(qty_followed_before + 1, qty_followed_after)

    def test_followers_subtypes_default(self):
        self.group_pigs.message_subscribe_users(user_ids=[self.user_employee.id])
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes)

    def test_followers_subtypes_specified(self):
        self.group_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

    def test_followers_multiple_subscription(self):
        self.group_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

        self.group_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id])
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)

    def test_no_DID(self):
        """Test that a follower cannot suffer from dissociative identity disorder.
           It cannot be both a partner and a channel.
        """
        test_channel = self.env['mail.channel'].create({
            'name': 'I used to be schizo, but now we are alright.'
        })
        with self.assertRaises(IntegrityError):
            self.env['mail.followers'].create({
                'res_model': 'mail.channel',
                'res_id': test_channel.id,
                'partner_id': self.user_employee.partner_id.id,
                'channel_id': self.group_pigs.id,
            })
