# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from unittest.mock import patch

from odoo.addons.test_mail.tests.common import BaseFunctionalTest, MockEmails, TestRecipients
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE_PLAINTEXT
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.exceptions import AccessError
from odoo.tools import mute_logger, formataddr


class TestMessagePost(BaseFunctionalTest, TestRecipients, MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMessagePost, cls).setUpClass()
        cls._create_portal_user()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        # configure mailing
        cls.alias_domain = 'schlouby.fr'
        cls.alias_catchall = 'test+catchall'
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.alias_catchall)

        cls.user_admin.write({'notification_type': 'email'})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_needaction(self):
        (self.user_employee | self.user_admin).write({'notification_type': 'inbox'})
        with self.assertNotifications(partner_employee=(1, 'inbox', 'unread'), partner_admin=(0, '', '')):
            self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])

        self.test_record.message_subscribe([self.partner_1.id])
        with self.assertNotifications(partner_employee=(1, 'inbox', 'unread'), partner_admin=(0, '', ''), partner_1=(1, 'email', 'read')):
            self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])

        with self.assertNotifications(partner_admin=(0, '', ''), partner_1=(1, 'email', 'read'), partner_portal=(1, 'email', 'read')):
            self.test_record.message_post(
                body='Test', message_type='comment', subtype='mail.mt_comment',
                partner_ids=[self.partner_portal.id])

    def test_post_inactive_follower(self):
        # In some case odoobot is follower of a record.
        # Even if it shouldn't be the case, we want to be sure that odoobot is not notified
        (self.user_employee | self.user_admin).write({'notification_type': 'inbox'})
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

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_notifications(self):
        _body, _body_alt, _subject = '<p>Test Body</p>', 'Test Body', 'Test Subject'

        # subscribe second employee to the group to test notifications
        self.test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id])

        msg = self.test_record.with_user(self.user_employee).message_post(
            body=_body, subject=_subject,
            message_type='comment', subtype='mt_comment',
            partner_ids=[self.partner_1.id, self.partner_2.id]
        )

        # message content
        self.assertEqual(msg.subject, _subject)
        self.assertEqual(msg.body, _body)
        self.assertEqual(msg.partner_ids, self.partner_1 | self.partner_2)
        self.assertEqual(msg.notified_partner_ids, self.user_admin.partner_id | self.partner_1 | self.partner_2)
        self.assertEqual(msg.channel_ids, self.env['mail.channel'])

        # notifications emails should have been deleted
        self.assertFalse(self.env['mail.mail'].search([('mail_message_id', '=', msg.id)]),
                         'message_post: mail.mail notifications should have been auto-deleted')

        # notification emails
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [self.user_admin.partner_id]],
            reply_to=msg.reply_to, subject=_subject,
            body_content=_body, body_alt_content=_body_alt,
            references=False)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_notifications_keep_emails(self):
        self.test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id])

        msg = self.test_record.with_user(self.user_employee).message_post(
            body='Test', subject='Test',
            message_type='comment', subtype='mt_comment',
            partner_ids=[self.partner_1.id, self.partner_2.id],
            mail_auto_delete=False
        )

        # notifications emails should not have been deleted: one for customers, one for user
        self.assertEqual(len(self.env['mail.mail'].search([('mail_message_id', '=', msg.id)])), 2)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_notifications_emails_tweak(self):
        pass
        # we should check _notification_groups behavior, for emails and buttons

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_attachments(self):
        _attachments = [
            ('List1', b'My first attachment'),
            ('List2', b'My second attachment')
        ]
        _attach_1 = self.env['ir.attachment'].with_user(self.user_employee).create({
            'name': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        _attach_2 = self.env['ir.attachment'].with_user(self.user_employee).create({
            'name': 'Attach2',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})

        msg = self.test_record.with_user(self.user_employee).message_post(
            body='Test', subject='Test',
            message_type='comment', subtype='mt_comment',
            attachment_ids=[_attach_1.id, _attach_2.id],
            partner_ids=[self.partner_1.id],
            attachments=_attachments,
        )

        # message attachments
        self.assertEqual(len(msg.attachment_ids), 4)
        self.assertEqual(set(msg.attachment_ids.mapped('res_model')), set([self.test_record._name]))
        self.assertEqual(set(msg.attachment_ids.mapped('res_id')), set([self.test_record.id]))
        self.assertEqual(set([base64.b64decode(x) for x in msg.attachment_ids.mapped('datas')]),
                         set([b'migration test', _attachments[0][1], _attachments[1][1]]))
        self.assertTrue(set([_attach_1.id, _attach_2.id]).issubset(msg.attachment_ids.ids),
                        'message_post: mail.message attachments duplicated')

        # notification email attachments
        self.assertEmails(self.user_employee.partner_id, [[self.partner_1]])
        # self.assertEqual(len(self._mails), 1)
        self.assertEqual(len(self._mails[0]['attachments']), 4)
        self.assertIn(('List1', b'My first attachment', 'application/octet-stream'), self._mails[0]['attachments'])
        self.assertIn(('List2', b'My second attachment', 'application/octet-stream'), self._mails[0]['attachments'])
        self.assertIn(('Attach1', b'migration test', 'application/octet-stream'),  self._mails[0]['attachments'])
        self.assertIn(('Attach2', b'migration test', 'application/octet-stream'), self._mails[0]['attachments'])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_answer(self):
        parent_msg = self.test_record.with_user(self.user_employee).message_post(
            body='<p>Test</p>', subject='Test Subject',
            message_type='comment', subtype='mt_comment')

        self.assertEqual(parent_msg.partner_ids, self.env['res.partner'])
        self.assertEmails(self.user_employee.partner_id, [])

        msg = self.test_record.with_user(self.user_employee).message_post(
            body='<p>Test Answer</p>',
            message_type='comment', subtype='mt_comment',
            partner_ids=[self.partner_1.id],
            parent_id=parent_msg.id)

        self.assertEqual(msg.parent_id.id, parent_msg.id)
        self.assertEqual(msg.partner_ids, self.partner_1)
        self.assertEqual(parent_msg.partner_ids, self.env['res.partner'])

        # check notification emails: references
        self.assertEmails(self.user_employee.partner_id, [[self.partner_1]], ref_content='openerp-%d-mail.test.simple' % self.test_record.id)
        # self.assertTrue(all('openerp-%d-mail.test.simple' % self.test_record.id in m['references'] for m in self._mails))

        new_msg = self.test_record.with_user(self.user_employee).message_post(
            body='<p>Test Answer Bis</p>',
            message_type='comment', subtype='mt_comment',
            parent_id=msg.id)

        self.assertEqual(new_msg.parent_id.id, parent_msg.id, 'message_post: flatten error')
        self.assertEqual(new_msg.partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_portal_ok(self):
        with patch.object(MailTestSimple, 'check_access_rights', return_value=True):
            self.test_record.message_subscribe((self.partner_1 | self.user_employee.partner_id).ids)
            new_msg = self.test_record.with_user(self.user_portal).message_post(
                body='<p>Test</p>', subject='Subject',
                message_type='comment', subtype='mt_comment')

        self.assertEqual(new_msg.sudo().notified_partner_ids, (self.partner_1 | self.user_employee.partner_id))
        self.assertEmails(self.user_portal.partner_id, [[self.partner_1], [self.user_employee.partner_id]])

    def test_post_portal_crash(self):
        with self.assertRaises(AccessError):
            self.test_record.with_user(self.user_portal).message_post(
                body='<p>Test</p>', subject='Subject',
                message_type='comment', subtype='mt_comment')

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread')
    def test_post_internal(self):
        self.test_record.message_subscribe([self.user_admin.partner_id.id])
        msg = self.test_record.with_user(self.user_employee).message_post(
            body='My Body', subject='My Subject',
            message_type='comment', subtype='mt_note')
        self.assertEqual(msg.partner_ids, self.env['res.partner'])
        self.assertEqual(msg.notified_partner_ids, self.env['res.partner'])

        self.format_and_process(
            MAIL_TEMPLATE_PLAINTEXT, self.user_admin.email, 'not_my_businesss@example.com',
            msg_id='<1198923581.41972151344608186800.JavaMail.diff1@agrolait.com>',
            extra='In-Reply-To:\r\n\t%s\n' % msg.message_id,
            target_model='mail.test.simple')
        reply = self.test_record.message_ids - msg
        self.assertTrue(reply)
        self.assertEqual(reply.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(reply.notified_partner_ids, self.user_employee.partner_id)
        self.assertEqual(reply.parent_id, msg)

    def test_post_log(self):
        new_note = self.test_record.with_user(self.user_employee)._message_log(
            body='<p>Labrador</p>',
        )

        self.assertEqual(new_note.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(new_note.body, '<p>Labrador</p>')
        self.assertEqual(new_note.author_id, self.user_employee.partner_id)
        self.assertEqual(new_note.email_from, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(new_note.notified_partner_ids, self.env['res.partner'])

    def test_post_notify(self):
        self.user_employee.write({'notification_type': 'inbox'})
        new_notification = self.test_record.message_notify(
            subject='This should be a subject',
            body='<p>You have received a notification</p>',
            partner_ids=[self.partner_1.id, self.user_employee.partner_id.id],
        )

        self.assertEqual(new_notification.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(new_notification.message_type, 'user_notification')
        self.assertEqual(new_notification.body, '<p>You have received a notification</p>')
        self.assertEqual(new_notification.author_id, self.env.user.partner_id)
        self.assertEqual(new_notification.email_from, formataddr((self.env.user.name, self.env.user.email)))
        self.assertEqual(new_notification.notified_partner_ids, self.partner_1 | self.user_employee.partner_id)
        self.assertNotIn(new_notification, self.test_record.message_ids)
        # todo xdo add test message_notify on thread with followers and stuff

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_post_w_template(self):
        test_record = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        self.user_employee.write({
            'groups_id': [(4, self.env.ref('base.group_partner_manager').id)],
        })
        _attachments = [{
            'name': 'first.txt',
            'datas': base64.b64encode(b'My first attachment'),
            'res_model': 'res.partner',
            'res_id': self.user_admin.partner_id.id
        }, {
            'name': 'second.txt',
            'datas': base64.b64encode(b'My second attachment'),
            'res_model': 'res.partner',
            'res_id': self.user_admin.partner_id.id
        }]
        email_1 = 'test1@example.com'
        email_2 = 'test2@example.com'
        email_3 = self.partner_1.email
        self._create_template('mail.test.simple', {
            'attachment_ids': [(0, 0, _attachments[0]), (0, 0, _attachments[1])],
            'partner_to': '%s,%s' % (self.partner_2.id, self.user_admin.partner_id.id),
            'email_to': '%s, %s' % (email_1, email_2),
            'email_cc': '%s' % email_3,
        })
        # admin should receive emails
        self.user_admin.write({'notification_type': 'email'})
        # Force the attachments of the template to be in the natural order.
        self.email_template.invalidate_cache(['attachment_ids'], ids=self.email_template.ids)

        test_record.with_user(self.user_employee).message_post_with_template(self.email_template.id, composition_mode='comment')

        new_partners = self.env['res.partner'].search([('email', 'in', [email_1, email_2])])
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject='About %s' % test_record.name,
            body_content=test_record.name,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])
