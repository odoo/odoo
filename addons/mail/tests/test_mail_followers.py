# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail


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

    def test_message_follower_ids_commands(self):
        # Create some dummy data on other groups to ensure they are not altered
        group_dummy = self.env['mail.channel'].with_context({'mail_create_nolog': True}).create({'name': 'Dummy group'})
        self.env['mail.followers'].create({'res_model': 'mail.thread', 'res_id': group_dummy.id, 'partner_id': self.partner_1.id})

        # Add 2 followers through the (4, ID) command
        self.group_pigs.write({'message_follower_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]})
        self.assertEqual(self.group_pigs.message_follower_ids, self.partner_1 | self.partner_2)

        # Remove 1 follower through the (3, ID) command
        self.group_pigs.write({'message_follower_ids': [(3, self.partner_2.id)]})
        self.assertEqual(self.group_pigs.message_follower_ids, self.partner_1)

        # Set followers through the (6, 0, IDs) command
        self.group_pigs.write({'message_follower_ids': [(6, 0, [self.partner_2.id, self.user_employee_2.partner_id.id])]})
        self.assertEqual(self.group_pigs.message_follower_ids,
                         self.partner_2 | self.user_employee_2.partner_id)

        # Add 1 follower through the (0, 0, values) command
        self.group_pigs.write({'message_follower_ids': [(0, 0, {'name': 'Patrick Fiori'})]})
        partner_patrick = self.env['res.partner'].search([('name', '=', 'Patrick Fiori')], limit=1)
        self.assertEqual(self.group_pigs.message_follower_ids,
                         self.partner_2 | self.user_employee_2.partner_id | partner_patrick)

        # Remove all followers through a (5, 0) command
        self.group_pigs.write({'message_follower_ids': [(5, 0)]})
        self.assertFalse(self.group_pigs.message_follower_ids)

        # Test dummy data has not been altered
        followers = self.env['mail.followers'].search([('res_model', '=', 'mail.thread'), ('res_id', '=', group_dummy.id)])
        self.assertEqual(followers.mapped('partner_id'), self.partner_1, 'dummy data altered')

    def test_followers_subtypes_default(self):
        self.group_pigs.message_subscribe_users(user_ids=[self.user_employee.id])
        self.assertEqual(self.group_pigs.message_follower_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes)

    def test_followers_subtypes_specified(self):
        self.group_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(self.group_pigs.message_follower_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

    def test_followers_multiple_subscription(self):
        self.group_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(self.group_pigs.message_follower_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

        self.group_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id])
        self.assertEqual(self.group_pigs.message_follower_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', '=', self.group_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)
