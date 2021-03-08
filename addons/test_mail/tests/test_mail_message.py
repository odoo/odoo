# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.common import TestMailCommon
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.exceptions import AccessError
from odoo.tools import mute_logger, formataddr
from odoo.tests import tagged


class TestMessageValues(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageValues, cls).setUpClass()

        cls._init_mail_gateway()
        cls.alias_record = cls.env['mail.test.container'].with_context(cls._test_context).create({
            'name': 'Pigs',
            'alias_name': 'pigs',
            'alias_contact': 'followers',
        })
        cls.Message = cls.env['mail.message'].with_user(cls.user_employee)

    @mute_logger('odoo.models.unlink')
    def test_mail_message_format(self):
        record1 = self.env['mail.test.simple'].create({'name': 'Test1'})
        message = self.env['mail.message'].create([{
            'model': 'mail.test.simple',
            'res_id': record1.id,
        }])
        res = message.message_format()
        self.assertEqual(res[0].get('record_name'), 'Test1')

        record1.write({"name": "Test2"})
        res = message.message_format()
        self.assertEqual(res[0].get('record_name'), 'Test2')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_format_access(self):
        """
        User that doesn't have access to a record should still be able to fetch
        the record_name inside message_format.
        """
        company_2 = self.env['res.company'].create({'name': 'Second Test Company'})
        record1 = self.env['mail.test.multi.company'].create({
            'name': 'Test1',
            'company_id': company_2.id,
        })
        message = record1.message_post(body='', partner_ids=[self.user_employee.partner_id.id])
        # We need to flush and invalidate the ORM cache since the record_name
        # is already cached from the creation. Otherwise it will leak inside
        # message_format.
        message.flush()
        message.invalidate_cache()
        res = message.with_user(self.user_employee).message_format()
        self.assertEqual(res[0].get('record_name'), 'Test1')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_no_document_values(self):
        msg = self.Message.create({
            'reply_to': 'test.reply@example.com',
            'email_from': 'test.from@example.com',
        })
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, 'test.reply@example.com')
        self.assertEqual(msg.email_from, 'test.from@example.com')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_no_document(self):
        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        reply_to_name = self.env.user.company_id.name
        reply_to_email = '%s@%s' % (self.alias_catchall, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain -> author
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias catchall, no alias -> author
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', self.alias_domain)
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.alias')]).unlink()

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_document_alias(self):
        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        reply_to_name = '%s %s' % (self.env.user.company_id.name, self.alias_record.name)
        reply_to_email = '%s@%s' % (self.alias_record.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain -> author
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no catchall -> don't care, alias
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', self.alias_domain)
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.alias')]).unlink()

        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        reply_to_name = '%s %s' % (self.env.company.name, self.alias_record.name)
        reply_to_email = '%s@%s' % (self.alias_record.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_document_no_alias(self):
        test_record = self.env['mail.test.simple'].create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        msg = self.Message.create({
            'model': 'mail.test.simple',
            'res_id': test_record.id
        })
        self.assertIn('-openerp-%d-mail.test.simple' % test_record.id, msg.message_id.split('@')[0])
        reply_to_name = '%s %s' % (self.env.user.company_id.name, test_record.name)
        reply_to_email = '%s@%s' % (self.alias_catchall, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_document_manual_alias(self):
        test_record = self.env['mail.test.simple'].create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        alias = self.env['mail.alias'].create({
            'alias_name': 'MegaLias',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.simple').id,
            'alias_parent_model_id': self.env['ir.model']._get('mail.test.simple').id,
            'alias_parent_thread_id': test_record.id,
        })

        msg = self.Message.create({
            'model': 'mail.test.simple',
            'res_id': test_record.id
        })

        self.assertIn('-openerp-%d-mail.test.simple' % test_record.id, msg.message_id.split('@')[0])
        reply_to_name = '%s %s' % (self.env.user.company_id.name, test_record.name)
        reply_to_email = '%s@%s' % (alias.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    def test_mail_message_values_no_auto_thread(self):
        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id,
            'no_auto_thread': True,
        })
        self.assertIn('reply_to', msg.message_id.split('@')[0])
        self.assertNotIn('mail.test.container', msg.message_id.split('@')[0])
        self.assertNotIn('-%d-' % self.alias_record.id, msg.message_id.split('@')[0])

    def test_mail_message_base64_image(self):
        msg = self.env['mail.message'].with_user(self.user_employee).create({
            'body': 'taratata <img src="data:image/png;base64,iV/+OkI=" width="2"> <img src="data:image/png;base64,iV/+OkI=" width="2">',
        })
        self.assertEqual(len(msg.attachment_ids), 1)
        body = '<p>taratata <img src="/web/image/%s?access_token=%s" alt="image0" width="2"> <img src="/web/image/%s?access_token=%s" alt="image0" width="2"></p>'
        body = body % (msg.attachment_ids[0].id, msg.attachment_ids[0].access_token, msg.attachment_ids[0].id, msg.attachment_ids[0].access_token)
        self.assertEqual(msg.body, body)


class TestMessageAccess(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageAccess, cls).setUpClass()

        cls.user_public = mail_new_test_user(cls.env, login='bert', groups='base.group_public', name='Bert Tartignole')
        cls.user_portal = mail_new_test_user(cls.env, login='chell', groups='base.group_portal', name='Chell Gladys')

        Channel = cls.env['mail.channel'].with_context(cls._test_context)
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
            'subject': '_ZTest', 'body': 'A', 'subtype_id': self.ref('mail.mt_comment')})
        msg2 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+B', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg3 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A Pigs', 'subtype_id': False,
            'model': 'mail.channel', 'res_id': self.group_pigs.id})
        msg4 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+P Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_pigs.id,
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg5 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+E Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_pigs.id,
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})
        msg6 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A Birds', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_private.id})
        msg7 = self.env['mail.message'].with_user(self.user_employee).create({
            'subject': '_ZTest', 'body': 'B', 'subtype_id': self.ref('mail.mt_comment')})
        msg8 = self.env['mail.message'].with_user(self.user_employee).create({
            'subject': '_ZTest', 'body': 'B+E', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})

        # Test: Public: 2 messages (recipient)
        messages = self.env['mail.message'].with_user(self.user_public).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg2 | msg4)

        # Test: Employee: 3 messages on Pigs Raoul can read (employee can read group with default values)
        messages = self.env['mail.message'].with_user(self.user_employee).search([('subject', 'like', '_ZTest'), ('body', 'ilike', 'A')])
        self.assertEqual(messages, msg3 | msg4 | msg5)

        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group) + 2 messages as author
        messages = self.env['mail.message'].with_user(self.user_employee).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg3 | msg4 | msg5 | msg7 | msg8)

        # Test: Admin: all messages
        messages = self.env['mail.message'].search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg1 | msg2 | msg3 | msg4 | msg5 | msg6 | msg7 | msg8)

        # Test: Portal: 0 (no access to groups, not recipient)
        messages = self.env['mail.message'].with_user(self.user_portal).search([('subject', 'like', '_ZTest')])
        self.assertFalse(messages)

        # Test: Portal: 2 messages (public group with a subtype)
        self.group_pigs.write({'public': 'public'})
        messages = self.env['mail.message'].with_user(self.user_portal).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg4 | msg5)

    # --------------------------------------------------
    # READ
    # --------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_mail_message_access_read_crash(self):
        with self.assertRaises(AccessError):
            self.message.with_user(self.user_employee).read()

    @mute_logger('odoo.models')
    def test_mail_message_access_read_crash_portal(self):
        with self.assertRaises(AccessError):
            self.message.with_user(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_ok_portal(self):
        self.message.write({'subtype_id': self.ref('mail.mt_comment'), 'res_id': self.group_public.id})
        self.message.with_user(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_notification(self):
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(b'My attachment'),
            'name': 'doc.txt'})
        # attach the attachment to the message
        self.message.write({'attachment_ids': [(4, attachment.id)]})
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.message.with_user(self.user_employee).read()
        # Test: Bert has access to attachment, ok because he can read message
        attachment.with_user(self.user_employee).read(['name', 'datas'])

    def test_mail_message_access_read_author(self):
        self.message.write({'author_id': self.user_employee.partner_id.id})
        self.message.with_user(self.user_employee).read()

    def test_mail_message_access_read_doc(self):
        self.message.write({'model': 'mail.channel', 'res_id': self.group_public.id})
        # Test: Bert reads the message, ok because linked to a doc he is allowed to read
        self.message.with_user(self.user_employee).read()

    def test_mail_message_access_read_crash_moderation(self):
        # with self.assertRaises(AccessError):
        self.message.write({'model': 'mail.channel', 'res_id': self.group_public.id, 'moderation_status': 'pending_moderation'})
        # Test: Bert reads the message, ok because linked to a doc he is allowed to read
        self.message.with_user(self.user_employee).read()

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_mail_message_access_create_crash_public(self):
        # Do: Bert creates a message on Pigs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_public).create({'model': 'mail.channel', 'res_id': self.group_pigs.id, 'body': 'Test'})

        # Do: Bert create a message on Jobs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_public).create({'model': 'mail.channel', 'res_id': self.group_public.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_crash(self):
        # Do: Bert create a private message -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_employee).create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_doc(self):
        Message = self.env['mail.message'].with_user(self.user_employee)
        # Do: Raoul creates a message on Jobs -> ok, write access to the related document
        Message.create({'model': 'mail.channel', 'res_id': self.group_public.id, 'body': 'Test'})
        # Do: Raoul creates a message on Priv -> ko, no write access to the related document
        with self.assertRaises(AccessError):
            Message.create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test'})

    def test_mail_message_access_create_private(self):
        self.env['mail.message'].with_user(self.user_employee).create({'body': 'Test'})

    def test_mail_message_access_create_reply(self):
        # TDE FIXME: should it really work ? not sure - catchall makes crash (aka, post will crash also)
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', False)
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.env['mail.message'].with_user(self.user_employee).create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test', 'parent_id': self.message.id})

    def test_mail_message_access_create_wo_parent_access(self):
        """ Purpose is to test posting a message on a record whose first message / parent
        is not accessible by current user. """
        test_record = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        partner_1 = self.env['res.partner'].create({
            'name': 'Jitendra Prajapati (jpr-odoo)',
            'email': 'jpr@odoo.com',
        })
        test_record.message_subscribe((partner_1 | self.user_admin.partner_id).ids)

        message = test_record.message_post(
            body='<p>This is First Message</p>', subject='Subject',
            message_type='comment', subtype_xmlid='mail.mt_note')
        # portal user have no rights to read the message
        with self.assertRaises(AccessError):
            message.with_user(self.user_portal).read(['subject, body'])

        with patch.object(MailTestSimple, 'check_access_rights', return_value=True):
            with self.assertRaises(AccessError):
                message.with_user(self.user_portal).read(['subject, body'])

            # parent message is accessible to references notification mail values
            # for _notify method and portal user have no rights to send the message for this model
            new_msg = test_record.with_user(self.user_portal).message_post(
                body='<p>This is Second Message</p>',
                subject='Subject',
                parent_id=message.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                mail_auto_delete=False)

        new_mail = self.env['mail.mail'].sudo().search([
            ('mail_message_id', '=', new_msg.id),
            ('references', '=', message.message_id),
        ])

        self.assertTrue(new_mail)
        self.assertEqual(new_msg.parent_id, message)

    # --------------------------------------------------
    # WRITE
    # --------------------------------------------------

    def test_mail_message_access_write_moderation(self):
        """ Only moderators can modify pending messages """
        self.group_public.write({
            'email_send': True,
            'moderation': True,
            'channel_partner_ids': [(4, self.partner_employee.id)],
            'moderator_ids': [(4, self.user_employee.id)],
        })
        self.message.write({'model': 'mail.channel', 'res_id': self.group_public.id, 'moderation_status': 'pending_moderation'})
        self.message.with_user(self.user_employee).write({'moderation_status': 'accepted'})

    def test_mail_message_access_write_crash_moderation(self):
        self.message.write({'model': 'mail.channel', 'res_id': self.group_public.id, 'moderation_status': 'pending_moderation'})
        with self.assertRaises(AccessError):
            self.message.with_user(self.user_employee).write({'moderation_status': 'accepted'})

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_mark_all_as_read(self):
        self.user_employee.notification_type = 'inbox'
        emp_partner = self.user_employee.partner_id.with_user(self.user_employee)

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
        msg1 = group_private.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[emp_partner.id])
        self._reset_bus()
        emp_partner.env['mail.message'].mark_all_as_read(domain=[])
        self.assertBusNotifications([(self.cr.dbname, 'res.partner', emp_partner.id)], [{ 'type': 'mark_as_read', 'message_ids': [msg1.id], 'needaction_inbox_counter': 0 }])
        na_count = emp_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all as read should conclude all needactions")

        # mark all as read also clear inaccessible needactions
        msg2 = group_private.message_post(body='Zest', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[emp_partner.id])
        needaction_accessible = len(emp_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_accessible, 1, "a new message to a partner is readable to that partner")

        msg2.sudo().partner_ids = self.env['res.partner']
        emp_partner.env['mail.message'].search([['needaction', '=', True]])
        needaction_length = len(emp_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_length, 1, "message should still be readable when notified")

        na_count = emp_partner.get_needaction_count()
        self.assertEqual(na_count, 1, "message not accessible is currently still counted")

        self._reset_bus()
        emp_partner.env['mail.message'].mark_all_as_read(domain=[])
        self.assertBusNotifications([(self.cr.dbname, 'res.partner', emp_partner.id)], [{ 'type': 'mark_as_read', 'message_ids': [msg2.id], 'needaction_inbox_counter': 0 }])
        na_count = emp_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all read should conclude all needactions even inacessible ones")

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_mark_all_as_read_share(self):
        self.user_portal.notification_type = 'inbox'
        portal_partner = self.user_portal.partner_id.with_user(self.user_portal)

        # mark all as read clear needactions
        self.group_pigs.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[portal_partner.id])
        portal_partner.env['mail.message'].mark_all_as_read(domain=[])
        na_count = portal_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all as read should conclude all needactions")

        # mark all as read also clear inaccessible needactions
        new_msg = self.group_pigs.message_post(body='Zest', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[portal_partner.id])
        needaction_accessible = len(portal_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_accessible, 1, "a new message to a partner is readable to that partner")

        new_msg.sudo().partner_ids = self.env['res.partner']
        needaction_length = len(portal_partner.env['mail.message'].search([['needaction', '=', True]]))
        self.assertEqual(needaction_length, 1, "message should still be readable when notified")

        na_count = portal_partner.get_needaction_count()
        self.assertEqual(na_count, 1, "message not accessible is currently still counted")

        portal_partner.env['mail.message'].mark_all_as_read(domain=[])
        na_count = portal_partner.get_needaction_count()
        self.assertEqual(na_count, 0, "mark all read should conclude all needactions even inacessible ones")


@tagged('moderation')
class TestMessageModeration(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageModeration, cls).setUpClass()

        cls.channel_1 = cls.env['mail.channel'].create({
            'name': 'Moderation_1',
            'email_send': True,
            'moderation': True
        })
        cls.user_employee.write({'moderation_channel_ids': [(6, 0, [cls.channel_1.id])]})
        cls.user_portal = cls._create_portal_user()

        # A pending moderation message needs to have field channel_ids empty. Moderators
        # need to be able to notify a pending moderation message (in a channel they moderate).
        cls.msg_c1_admin1 = cls._add_messages(cls.channel_1, 'Body11', author=cls.partner_admin, moderation_status='pending_moderation')
        cls.msg_c1_admin2 = cls._add_messages(cls.channel_1, 'Body12', author=cls.partner_admin, moderation_status='pending_moderation')
        cls.msg_c1_portal = cls._add_messages(cls.channel_1, 'Body21', author=cls.partner_portal, moderation_status='pending_moderation')

    @mute_logger('odoo.models.unlink')
    def test_moderate_accept(self):
        self._reset_bus()
        self.assertFalse(self.msg_c1_admin1.channel_ids | self.msg_c1_admin2.channel_ids | self.msg_c1_portal.channel_ids)

        self.msg_c1_admin1.with_user(self.user_employee)._moderate('accept')
        self.assertEqual(self.msg_c1_admin1.channel_ids, self.channel_1)
        self.assertEqual(self.msg_c1_admin1.moderation_status, 'accepted')
        self.assertEqual(self.msg_c1_admin2.moderation_status, 'pending_moderation')
        self.assertBusNotifications([(self.cr.dbname, 'mail.channel', self.channel_1.id)])

    @mute_logger('odoo.models.unlink')
    def test_moderate_allow(self):
        self._reset_bus()

        self.msg_c1_admin1.with_user(self.user_employee)._moderate('allow')
        self.assertEqual(self.msg_c1_admin1.channel_ids, self.channel_1)
        self.assertEqual(self.msg_c1_admin2.channel_ids, self.channel_1)
        self.assertEqual(self.msg_c1_admin1.moderation_status, 'accepted')
        self.assertEqual(self.msg_c1_admin2.moderation_status, 'accepted')
        self.assertBusNotifications([
            (self.cr.dbname, 'mail.channel', self.channel_1.id),
            (self.cr.dbname, 'mail.channel', self.channel_1.id)])

    @mute_logger('odoo.models.unlink')
    def test_moderate_reject(self):
        with self.mock_mail_gateway():
            (self.msg_c1_admin1 | self.msg_c1_portal).with_user(self.user_employee)._moderate_send_reject_email('Title', 'Message to author')
            self.assertEqual(len(self._new_mails), 2)
        for mail in self._new_mails:
            self.assertEqual(mail.author_id, self.partner_employee)
            self.assertEqual(mail.subject, 'Title')
            self.assertEqual(mail.state, 'outgoing')
        self.assertEqual(
            set(self._new_mails.mapped('email_to')),
            set([self.msg_c1_admin1.email_from, self.msg_c1_portal.email_from])
        )
        self.assertEqual(
            set(self._new_mails.mapped('body_html')),
            set(['<div>Message to author</div>\n%s\n' % self.msg_c1_admin1.body, '<div>Message to author</div>\n%s\n' % self.msg_c1_portal.body])
        )  # TDE note: \n are added by append content to html, because why not

    @mute_logger('odoo.models.unlink')
    def test_moderate_discard(self):
        self._reset_bus()
        id1, id2, id3 = self.msg_c1_admin1.id, self.msg_c1_admin2.id, self.msg_c1_portal.id  # save ids because unlink will discard them
        (self.msg_c1_admin1 | self.msg_c1_admin2 | self.msg_c1_portal).with_user(self.user_employee)._moderate_discard()

        self.assertBusNotifications(
            [(self.cr.dbname, 'res.partner', self.partner_admin.id),
             (self.cr.dbname, 'res.partner', self.partner_employee.id),
             (self.cr.dbname, 'res.partner', self.partner_portal.id)],
            [{'type': 'deletion', 'message_ids': [id1, id2]},  # author of 2 messages
             {'type': 'deletion', 'message_ids': [id1, id2, id3]},  # moderator
             {'type': 'deletion', 'message_ids': [id3]}]  # author of 1 message
        )

    @mute_logger('odoo.models.unlink')
    def test_notify_moderators(self):
        # create pending messages in another channel to have two notification to push
        channel_2 = self.env['mail.channel'].create({
            'name': 'Moderation_1',
            'email_send': True,
            'moderation': True
        })
        self.user_admin.write({'moderation_channel_ids': [(6, 0, [channel_2.id])]})
        self.msg_c2_portal = self._add_messages(channel_2, 'Body31', author=self.partner_portal, moderation_status='pending_moderation')

        # one notification for each moderator: employee (channel1), admin (channel2)
        with self.assertPostNotifications([{
            'content': 'Hello %s' % self.partner_employee.name,
            'message_type': 'user_notification', 'subtype': 'mail.mt_note',
            'notif': [{
                'partner': self.partner_employee,
                'type': 'inbox'}]
        }, {
            'content': 'Hello %s' % self.partner_admin.name,
            'message_type': 'user_notification', 'subtype': 'mail.mt_note',
            'notif': [{
                'partner': self.partner_admin,
                'type': 'inbox'}]
        }]):
            self.env['mail.message']._notify_moderators()
