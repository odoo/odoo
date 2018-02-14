# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import itertools

from odoo.addons.mail.tests.common import TestMail
from odoo.exceptions import AccessError, except_orm
from odoo.tools import mute_logger


class TestMailMessage(TestMail):

    def test_mail_message_values_basic(self):
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.env['mail.message'].sudo(self.user_employee).create({
            'reply_to': 'test.reply@example.com',
            'email_from': 'test.from@example.com',
        })
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, 'test.reply@example.com')
        self.assertEqual(msg.email_from, 'test.from@example.com')

    def test_mail_message_values_default(self):
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.env['mail.message'].sudo(self.user_employee).create({})
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s <%s>' % (self.user_employee.name, self.user_employee.email))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_alias(self):
        alias_domain = 'example.com'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.alias')]).unlink()

        msg = self.env['mail.message'].sudo(self.user_employee).create({})
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s <%s>' % (self.user_employee.name, self.user_employee.email))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_alias_catchall(self):
        alias_domain = 'example.com'
        alias_catchall = 'pokemon'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', alias_catchall)

        msg = self.env['mail.message'].sudo(self.user_employee).create({})
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s <%s@%s>' % (self.env.user.company_id.name, alias_catchall, alias_domain))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_document_no_alias(self):
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.env['mail.message'].sudo(self.user_employee).create({
            'model': 'mail.test',
            'res_id': self.test_pigs.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.test_pigs.id, msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s <%s>' % (self.user_employee.name, self.user_employee.email))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_document_alias(self):
        alias_domain = 'example.com'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.alias')]).unlink()

        msg = self.env['mail.message'].sudo(self.user_employee).create({
            'model': 'mail.test',
            'res_id': self.test_pigs.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.test_pigs.id, msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s %s <%s@%s>' % (self.env.user.company_id.name, self.test_pigs.name, self.test_pigs.alias_name, alias_domain))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_document_alias_catchall(self):
        alias_domain = 'example.com'
        alias_catchall = 'pokemon'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', alias_catchall)

        msg = self.env['mail.message'].sudo(self.user_employee).create({
            'model': 'mail.test',
            'res_id': self.test_pigs.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.test_pigs.id, msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s %s <%s@%s>' % (self.env.user.company_id.name, self.test_pigs.name, self.test_pigs.alias_name, alias_domain))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_no_auto_thread(self):
        msg = self.env['mail.message'].sudo(self.user_employee).create({
            'model': 'mail.test',
            'res_id': self.test_pigs.id,
            'no_auto_thread': True,
        })
        self.assertIn('reply_to', msg.message_id)
        self.assertNotIn('mail.test', msg.message_id)
        self.assertNotIn('-%d-' % self.test_pigs.id, msg.message_id)

    def test_mail_message_notify_from_mail_mail(self):
        # Due ot post-commit hooks, store send emails in every step
        self.email_to_list = []
        mail = self.env['mail.mail'].create({
            'body_html': '<p>Test</p>',
            'email_to': 'test@example.com',
            'partner_ids': [(4, self.user_employee.partner_id.id)]
        })
        self.email_to_list.extend(itertools.chain.from_iterable(sent_email['email_to'] for sent_email in self._mails if sent_email.get('email_to')))
        self.assertNotIn(u'Ernest Employee <e.e@example.com>', self.email_to_list)
        mail.send()
        self.email_to_list.extend(itertools.chain.from_iterable(sent_email['email_to'] for sent_email in self._mails if sent_email.get('email_to')))
        self.assertNotIn(u'Ernest Employee <e.e@example.com>', self.email_to_list)
        self.assertIn(u'test@example.com', self.email_to_list)

    def test_mail_message_base64_image(self):
        msg = self.env['mail.message'].sudo(self.user_employee).create({
            'body': 'taratata <img src="data:image/png;base64,iV/+OkI=" width="2"> <img src="data:image/png;base64,iV/+OkI=" width="2">',
        })
        self.assertEqual(len(msg.attachment_ids), 1)
        body = '<p>taratata <img src="/web/image/%s?access_token=%s" alt="image0" width="2"> <img src="/web/image/%s?access_token=%s" alt="image0" width="2"></p>'
        body = body % (msg.attachment_ids[0].id, msg.attachment_ids[0].access_token, msg.attachment_ids[0].id, msg.attachment_ids[0].access_token)
        self.assertEqual(msg.body, body)


class TestMailMessageAccess(TestMail):

    @classmethod
    def setUpClass(cls):
        super(TestMailMessageAccess, cls).setUpClass()
        Channel = cls.env['mail.channel'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True
        })
        # Pigs: base group for tests
        cls.group_pigs = Channel.create({
            'name': 'Pigs',
            'public': 'groups',
            'group_public_id': cls.env.ref('base.group_user').id})
        # Jobs: public group
        cls.group_public = Channel.create({
            'name': 'Jobs',
            'description': 'NotFalse',
            'public': 'public'})
        # Private: private gtroup
        cls.group_private = Channel.create({
            'name': 'Private',
            'public': 'private'})
        cls.message = cls.env['mail.message'].create({
            'body': 'My Body',
            'model': 'mail.channel',
            'res_id': cls.group_private.id,
        })

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_message_access_search(self):
        # Data: various author_ids, partner_ids, documents
        msg1 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A', 'subtype_id': self.ref('mail.mt_comment')})
        msg2 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A+B', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg3 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A Pigs', 'subtype_id': False,
            'model': 'mail.channel', 'res_id': self.group_pigs.id})
        msg4 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A+P Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_pigs.id,
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg5 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A+E Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_pigs.id,
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})
        msg6 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A Birds', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_private.id})
        msg7 = self.env['mail.message'].sudo(self.user_employee).create({
            'subject': '_Test', 'body': 'B', 'subtype_id': self.ref('mail.mt_comment')})
        msg8 = self.env['mail.message'].sudo(self.user_employee).create({
            'subject': '_Test', 'body': 'B+E', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})

        # Test: Public: 2 messages (recipient)
        messages = self.env['mail.message'].sudo(self.user_public).search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg2 | msg4)

        # Test: Employee: 3 messages on Pigs Raoul can read (employee can read group with default values)
        messages = self.env['mail.message'].sudo(self.user_employee).search([('subject', 'like', '_Test'), ('body', 'ilike', 'A')])
        self.assertEqual(messages, msg3 | msg4 | msg5)

        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group) + 2 messages as author
        messages = self.env['mail.message'].sudo(self.user_employee).search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg3 | msg4 | msg5 | msg7 | msg8)

        # Test: Admin: all messages
        messages = self.env['mail.message'].search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg1 | msg2 | msg3 | msg4 | msg5 | msg6 | msg7 | msg8)

        # Test: Portal: 0 (no access to groups, not recipient)
        messages = self.env['mail.message'].sudo(self.user_portal).search([('subject', 'like', '_Test')])
        self.assertFalse(messages)

        # Test: Portal: 2 messages (public group with a subtype)
        self.group_pigs.write({'public': 'public'})
        messages = self.env['mail.message'].sudo(self.user_portal).search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg4 | msg5)

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_mail_message_access_read_crash(self):
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.So we need to change all
        # except_orm to warning in mail module.)
        with self.assertRaises(except_orm):
            self.message.sudo(self.user_employee).read()

    @mute_logger('odoo.models')
    def test_mail_message_access_read_crash_portal(self):
        with self.assertRaises(except_orm):
            self.message.sudo(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_ok_portal(self):
        self.message.write({'subtype_id': self.ref('mail.mt_comment'), 'res_id': self.group_public.id})
        self.message.sudo(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_notification(self):
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(b'My attachment'),
            'name': 'doc.txt',
            'datas_fname': 'doc.txt'})
        # attach the attachment to the message
        self.message.write({'attachment_ids': [(4, attachment.id)]})
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.message.sudo(self.user_employee).read()
        # Test: Bert has access to attachment, ok because he can read message
        attachment.sudo(self.user_employee).read(['name', 'datas'])

    def test_mail_message_access_read_author(self):
        self.message.write({'author_id': self.user_employee.partner_id.id})
        self.message.sudo(self.user_employee).read()

    def test_mail_message_access_read_doc(self):
        self.message.write({'model': 'mail.channel', 'res_id': self.group_public.id})
        # Test: Bert reads the message, ok because linked to a doc he is allowed to read
        self.message.sudo(self.user_employee).read()

    @mute_logger('odoo.addons.base.ir.ir_model')
    def test_mail_message_access_create_crash_public(self):
        # Do: Bert creates a message on Pigs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].sudo(self.user_public).create({'model': 'mail.channel', 'res_id': self.group_pigs.id, 'body': 'Test'})

        # Do: Bert create a message on Jobs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].sudo(self.user_public).create({'model': 'mail.channel', 'res_id': self.group_public.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_crash(self):
        # Do: Bert create a private message -> ko, no creation rights
        with self.assertRaises(except_orm):
            self.env['mail.message'].sudo(self.user_employee).create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_doc(self):
        # TODO Change the except_orm to Warning
        Message = self.env['mail.message'].sudo(self.user_employee)
        # Do: Raoul creates a message on Jobs -> ok, write access to the related document
        Message.create({'model': 'mail.channel', 'res_id': self.group_public.id, 'body': 'Test'})
        # Do: Raoul creates a message on Priv -> ko, no write access to the related document
        with self.assertRaises(except_orm):
            Message.create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test'})

    def test_mail_message_access_create_private(self):
        self.env['mail.message'].sudo(self.user_employee).create({'body': 'Test'})

    def test_mail_message_access_create_reply(self):
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.env['mail.message'].sudo(self.user_employee).create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test', 'parent_id': self.message.id})

    def test_message_set_star(self):
        msg = self.test_pigs.message_post(body='My Body', subject='1')
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

    def test_60_cache_invalidation(self):
        msg_cnt = len(self.test_pigs.message_ids)
        self.test_pigs.message_post(body='Hi!', subject='test')
        self.assertEqual(len(self.test_pigs.message_ids), msg_cnt + 1)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_mark_all_as_read(self):
        self.user_employee.notification_type = 'inbox'
        emp_partner = self.user_employee.partner_id.sudo(self.user_employee.id)

        group_private = self.env['mail.channel'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_channel_noautofollow': True,
        }).create({
            'name': 'Private',
            'description': 'Private James R.',
            'public': 'private',
            'alias_name': 'private',
            'alias_contact': 'followers'}
        ).with_context({'mail_create_nosubscribe': False})

        # mark all as read clear needactions
        group_private.message_post(body='Test', message_type='comment', subtype='mail.mt_comment', partner_ids=[emp_partner.id])
        emp_partner.env['mail.message'].mark_all_as_read(channel_ids=[], domain=[])
        na_count = emp_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all as read should conclude all needactions")

        # mark all as read also clear inaccessible needactions
        new_msg = group_private.message_post(body='Zest', message_type='comment', subtype='mail.mt_comment', partner_ids=[emp_partner.id])
        needaction_accessible = len(emp_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_accessible, 1, "a new message to a partner is readable to that partner")

        new_msg.sudo().partner_ids = self.env['res.partner']
        emp_partner.env['mail.message'].search([['needaction', '=', True]])
        needaction_length = len(emp_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_length, 1, "message should still be readable when notified")

        na_count = emp_partner.get_needaction_count()
        self.assertEqual(na_count, 1, "message not accessible is currently still counted")

        emp_partner.env['mail.message'].mark_all_as_read(channel_ids=[], domain=[])
        na_count = emp_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all read should conclude all needactions even inacessible ones")

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_mark_all_as_read_share(self):
        self.user_portal.notification_type = 'inbox'
        portal_partner = self.user_portal.partner_id.sudo(self.user_portal.id)

        # mark all as read clear needactions
        self.group_pigs.message_post(body='Test', message_type='comment', subtype='mail.mt_comment', partner_ids=[portal_partner.id])
        portal_partner.env['mail.message'].mark_all_as_read(channel_ids=[], domain=[])
        na_count = portal_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all as read should conclude all needactions")

        # mark all as read also clear inaccessible needactions
        new_msg = self.group_pigs.message_post(body='Zest', message_type='comment', subtype='mail.mt_comment', partner_ids=[portal_partner.id])
        needaction_accessible = len(portal_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_accessible, 1, "a new message to a partner is readable to that partner")

        new_msg.sudo().partner_ids = self.env['res.partner']
        needaction_length = len(portal_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_length, 1, "message should still be readable when notified")

        na_count = portal_partner.get_needaction_count()
        self.assertEqual(na_count, 1, "message not accessible is currently still counted")

        portal_partner.env['mail.message'].mark_all_as_read(channel_ids=[], domain=[])
        na_count = portal_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all read should conclude all needactions even inacessible ones")
