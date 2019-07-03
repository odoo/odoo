# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.common import BaseFunctionalTest, TestRecipients, MockEmails
from odoo.addons.test_mail.tests.common import mail_new_test_user


class TestChatterTweaks(BaseFunctionalTest, TestRecipients):

    def test_post_no_subscribe_author(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment')
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    def test_post_no_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    def test_post_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_1 | self.partner_2)
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    def test_chatter_mail_create_nolog(self):
        """ Test disable of automatic chatter message at create """
        rec = self.env['mail.test.simple'].with_user(self.user_employee).with_context({'mail_create_nolog': True}).create({'name': 'Test'})
        self.assertEqual(rec.message_ids, self.env['mail.message'])

        rec = self.env['mail.test.simple'].with_user(self.user_employee).with_context({'mail_create_nolog': False}).create({'name': 'Test'})
        self.assertEqual(len(rec.message_ids), 1)

    def test_chatter_mail_notrack(self):
        """ Test disable of automatic value tracking at create and write """
        rec = self.env['mail.test.track'].with_user(self.user_employee).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.assertEqual(len(rec.message_ids), 1,
                         "A creation message without tracking values should have been posted")
        self.assertEqual(len(rec.message_ids.sudo().tracking_value_ids), 0,
                         "A creation message without tracking values should have been posted")

        rec.with_context({'mail_notrack': True}).write({'user_id': self.user_admin.id})
        self.assertEqual(len(rec.message_ids), 1,
                         "No new message should have been posted with mail_notrack key")

        rec.with_context({'mail_notrack': False}).write({'user_id': self.user_employee.id})
        self.assertEqual(len(rec.message_ids), 2,
                         "A tracking message should have been posted")
        self.assertEqual(len(rec.message_ids.sudo().mapped('tracking_value_ids')), 1,
                         "New tracking message should have tracking values")

    def test_chatter_tracking_disable(self):
        """ Test disable of all chatter features at create and write """
        rec = self.env['mail.test.track'].with_user(self.user_employee).with_context({'tracking_disable': True}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.assertEqual(rec.sudo().message_ids, self.env['mail.message'])
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.write({'user_id': self.user_admin.id})
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.with_context({'tracking_disable': False}).write({'user_id': self.user_employee.id})
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 1)

        rec = self.env['mail.test.track'].with_user(self.user_employee).with_context({'tracking_disable': False}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.assertEqual(len(rec.sudo().message_ids), 1,
                         "Creation message without tracking values should have been posted")
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 0,
                         "Creation message without tracking values should have been posted")


class TestNotifications(BaseFunctionalTest, MockEmails):

    def setUp(self):
        self.partner_1 = self.env['res.partner'].with_context(BaseFunctionalTest._test_context).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})

        (self.user_employee | self.user_admin).write({'notification_type': 'inbox'})
        # DLE P108: Needs to call setup after, as the flush is done in the setup, and the above requirements were not flushed
        # `test_inactive_follower`
        super(TestNotifications, self).setUp()

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

    def test_inactive_follower(self):
        # In some case odoobot is follower of a record.
        # Even if it shouldn't be the case, we want to be sure that odoobot is not notified
        self.test_record._message_subscribe(self.user_employee.partner_id.ids)
        with self.assertNotifications(partner_employee=(1, 'inbox', 'unread')):
            self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment')
        self.user_employee.active = False
        # at this point, partner is still active and would receive an email notification
        self.user_employee.partner_id._write({'active': False})
        with self.assertNotifications(partner_employee=(0, '', '')):
            self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment')

    def test_set_message_done_user(self):
        with self.assertNotifications(partner_employee=(0, '', '')):
            message = self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])
            message.with_user(self.user_employee).set_message_done()

    def test_set_message_done_portal(self):
        user_portal = mail_new_test_user(self.env, login='chell', groups='base.group_portal', name='Chell Gladys', notification_type='inbox')
        self.partner_portal = user_portal.partner_id

        with self.assertNotifications(partner_employee=(1, 'inbox', 'unread'), partner_portal=(1, 'inbox', 'read')):
            message = self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id, user_portal.partner_id.id])
            message.with_user(user_portal).set_message_done()

    def test_set_star(self):
        msg = self.test_record.with_user(self.user_admin).message_post(body='My Body', subject='1')
        msg_emp = self.env['mail.message'].with_user(self.user_employee).browse(msg.id)

        # Admin set as starred
        # DLE P109: This is a tricky one.
        # `starred` depends on `starred_partner_ids`,
        # `starred_partner_ids` is written as sudo in `toggle_message_starred`
        # therefore, the modified is called as sudo, and the `add_todo` as well.
        # It therefore adds in the todo list the field `starred` for the msg - as sudo -
        # When reading msg.starred, the field is in the todo list, and it therefore use it,
        # with the records from the todo list, as sudo, to compute the `starred` field.
        # The `starred` field is therefore computed as sudo (uid 1) while we asked it for user_admin (uid 2)
        # Besides, the cache no longer depends on the uid.
        # Not sure if we add a api.depends_uid for this case or not.
        # This is straightforward to do but this increase the complexity for developers.
        msg.invalidate_cache()
        msg.toggle_message_starred()
        msg.flush()
        msg.invalidate_cache()
        self.assertTrue(msg.starred)

        # Employee set as starred
        msg_emp.invalidate_cache()
        msg_emp.toggle_message_starred()
        msg_emp.flush()
        msg_emp.invalidate_cache()
        self.assertTrue(msg_emp.starred)

        # Do: Admin unstars msg
        msg.invalidate_cache()
        msg.toggle_message_starred()
        msg.invalidate_cache()
        self.assertFalse(msg.starred)
        msg_emp.invalidate_cache()
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
