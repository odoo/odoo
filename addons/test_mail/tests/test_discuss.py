# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.common import BaseFunctionalTest, TestRecipients, MockEmails


class TestChatterTweaks(BaseFunctionalTest, TestRecipients):

    def test_post_no_subscribe_author(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment')
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    def test_post_no_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    def test_post_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_1 | self.partner_2)
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    def test_post_subscribe_recipients_partial(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True, 'mail_post_autofollow_partner_ids': [self.partner_2.id]}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_2)
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    def test_chatter_mail_create_nolog(self):
        """ Test disable of automatic chatter message at create """
        rec = self.env['mail.test.simple'].sudo(self.user_employee).with_context({'mail_create_nolog': True}).create({'name': 'Test'})
        self.assertEqual(rec.message_ids, self.env['mail.message'])

        rec = self.env['mail.test.simple'].sudo(self.user_employee).with_context({'mail_create_nolog': False}).create({'name': 'Test'})
        self.assertEqual(len(rec.message_ids), 1)

    def test_chatter_mail_notrack(self):
        """ Test disable of automatic value tracking at create and write """
        rec = self.env['mail.test.track'].sudo(self.user_employee).with_context({'mail_notrack': False}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 1)

        rec = self.env['mail.test.track'].sudo(self.user_employee).with_context({'mail_notrack': True}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.write({'user_id': self.user_admin.id})
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.with_context({'mail_notrack': False}).write({'user_id': self.user_employee.id})
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 1)

    def test_chatter_tracking_disable(self):
        """ Test disable of all chatter features at create and write """
        rec = self.env['mail.test.track'].sudo(self.user_employee).with_context({'tracking_disable': True}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.assertEqual(rec.sudo().message_ids, self.env['mail.message'])
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.write({'user_id': self.user_admin.id})
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.with_context({'tracking_disable': False}).write({'user_id': self.user_employee.id})
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 1)

        rec = self.env['mail.test.track'].sudo(self.user_employee).with_context({'tracking_disable': False}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.assertEqual(len(rec.sudo().message_ids), 2)
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 1)


class TestNotifications(BaseFunctionalTest, MockEmails):

    def setUp(self):
        super(TestNotifications, self).setUp()
        self.partner_1 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})

        (self.user_employee | self.user_admin).write({'notification_type': 'inbox'})

    def test_needaction(self):
        with self.assertNotifications(partner_employee=(1, 'inbox', 'unread'), partner_admin=(0, '', '')):
            self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])

        self.test_record.message_subscribe([self.partner_1.id])
        with self.assertNotifications(partner_employee=(1, 'inbox', 'unread'), partner_admin=(0, '', ''), partner_1=(1, 'email', 'read')):
            self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])

    def test_set_message_done_user(self):
        with self.assertNotifications(partner_employee=(0, '', '')):
            message = self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])
            message.sudo(self.user_employee).set_message_done()

    def test_set_message_done_portal(self):
        user_portal = self.env['res.users'].with_context(self._quick_create_user_ctx).create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        self.partner_portal = user_portal.partner_id

        with self.assertNotifications(partner_employee=(1, 'inbox', 'unread'), partner_portal=(1, 'inbox', 'read')):
            message = self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id, user_portal.partner_id.id])
            message.sudo(user_portal).set_message_done()

    def test_set_star(self):
        msg = self.test_record.message_post(body='My Body', subject='1')
        msg_emp = self.env['mail.message'].sudo(self.user_employee).browse(msg.id)

        # Admin set as starred
        msg.toggle_message_starred()
        self.assertTrue(msg.starred)

        # Employee set as starred
        msg_emp.toggle_message_starred()
        self.assertTrue(msg_emp.starred)

        # Do: Admin unstars msg
        msg.toggle_message_starred()
        self.assertFalse(msg.starred)
        self.assertTrue(msg_emp.starred)


class TestChatterMisc(BaseFunctionalTest):

    def test_alias_setup(self):
        alias = self.env['mail.alias'].with_context(alias_model_name='mail.test').create({'alias_name': 'b4r+_#_R3wl$$'})
        self.assertEqual(alias.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

    def test_cache_invalidation(self):
        """ Test that creating a mail-thread record does not invalidate the whole cache. """
        # make a new record in cache
        record = self.env['res.partner'].new({'name': 'Brave New Partner'})
        self.assertTrue(record.name)

        # creating a mail-thread record should not invalidate the whole cache
        self.env['res.partner'].create({'name': 'Actual Partner'})
        self.assertTrue(record.name)
