# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from markupsafe import Markup
from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged, users
from odoo.tools import is_html_empty, mute_logger, formataddr


@tagged("mail_message", "post_install", "-at_install")
class TestMessageValues(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageValues, cls).setUpClass()

        cls.alias_record = cls.env['mail.test.container'].with_context(cls._test_context).create({
            'name': 'Pigs',
            'alias_name': 'pigs',
            'alias_contact': 'followers',
        })
        cls.Message = cls.env['mail.message'].with_user(cls.user_employee)

    @users('employee')
    def test_empty_message(self):
        """ Test that message is correctly considered as empty (see `_filter_empty()`).
        Message considered as empty if:
            - no body or empty body
            - AND no subtype or no subtype description
            - AND no tracking values
            - AND no attachment

        Check _update_content behavior when voiding messages (cleanup side
        records: stars, notifications).
        """
        note_subtype = self.env.ref('mail.mt_note')
        _attach_1 = self.env['ir.attachment'].with_user(self.user_employee).create({
            'name': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_id': 0,
            'res_model': 'mail.compose.message',
        })
        record = self.env['mail.test.track'].create({'name': 'EmptyTesting'})
        self.flush_tracking()
        record.message_subscribe(partner_ids=self.partner_admin.ids, subtype_ids=note_subtype.ids)
        message = record.message_post(
            attachment_ids=_attach_1.ids,
            body='Test',
            message_type='comment',
            subtype_id=note_subtype.id,
        )
        message.write({'starred_partner_ids': [(4, self.partner_admin.id)]})

        # check content
        self.assertEqual(len(message.attachment_ids), 1)
        self.assertFalse(is_html_empty(message.body))
        self.assertEqual(len(message.sudo().notification_ids), 1)
        self.assertEqual(message.notified_partner_ids, self.partner_admin)
        self.assertEqual(message.starred_partner_ids, self.partner_admin)
        self.assertFalse(message.sudo().tracking_value_ids)

        # Reset body case
        record._message_update_content(message, '<p><br /></p>', attachment_ids=message.attachment_ids.ids)
        self.assertTrue(is_html_empty(message.body))
        self.assertFalse(message.sudo()._filter_empty(), 'Still having attachments')

        # Subtype content
        note_subtype.sudo().write({'description': 'Very important discussions'})
        record._message_update_content(message, '', [])
        self.assertFalse(message.attachment_ids)
        self.assertEqual(message.notified_partner_ids, self.partner_admin)
        self.assertEqual(message.starred_partner_ids, self.partner_admin)
        self.assertFalse(message.sudo()._filter_empty(), 'Subtype with description')

        # Completely void now
        note_subtype.sudo().write({'description': ''})
        self.assertEqual(message.sudo()._filter_empty(), message)
        record._message_update_content(message, '', [])
        self.assertFalse(message.notified_partner_ids)
        self.assertFalse(message.starred_partner_ids)

        # test tracking values
        record.write({'user_id': self.user_admin.id})
        self.flush_tracking()
        tracking_message = record.message_ids[0]
        self.assertFalse(tracking_message.attachment_ids)
        self.assertTrue(is_html_empty(tracking_message.body))
        self.assertFalse(tracking_message.subtype_id.description)
        self.assertFalse(tracking_message.sudo()._filter_empty(), 'Has tracking values')
        with self.assertRaises(UserError, msg='Tracking values prevent from updating content'):
            record._message_update_content(tracking_message, '', [])

    @mute_logger('odoo.models.unlink')
    def test_mail_message_format(self):
        record1 = self.env['mail.test.simple'].create({'name': 'Test1'})
        record2 = self.env['mail.test.nothread'].create({'name': 'Test2'})
        messages = self.env['mail.message'].create([{
            'model': record._name,
            'res_id': record.id,
        } for record in [record1, record2]])
        for message, record in zip(messages, [record1, record2]):
            with self.subTest(record=record):
                formatted = message.message_format()[0]
                self.assertEqual(formatted['record_name'], record.name)
                record.write({'name': 'Just Test'})
                formatted = message.message_format()[0]
                self.assertEqual(formatted['record_name'], 'Just Test')

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
        self.env.flush_all()
        self.env.invalidate_all()
        res = message.with_user(self.user_employee).message_format()
        self.assertEqual(res[0].get('record_name'), 'Test1')

    def test_mail_message_values_body_base64_image(self):
        msg = self.env['mail.message'].with_user(self.user_employee).create({
            'body': 'taratata <img src="data:image/png;base64,iV/+OkI=" width="2"> <img src="data:image/png;base64,iV/+OkI=" width="2">',
        })
        self.assertEqual(len(msg.attachment_ids), 1)
        self.assertEqual(
            msg.body,
            '<p>taratata <img src="/web/image/{attachment.id}?access_token={attachment.access_token}" alt="image0" width="2"> '
            '<img src="/web/image/{attachment.id}?access_token={attachment.access_token}" alt="image0" width="2"></p>'.format(attachment=msg.attachment_ids[0])
        )

    @mute_logger('odoo.models.unlink')
    @users('employee')
    def test_mail_message_values_fromto_long_name(self):
        """ Long headers may break in python if above 78 chars as folding is not
        done correctly (see ``_notify_get_reply_to_formatted_email`` docstring
        + commit linked to this test). """
        # name would make it blow up: keep only email
        test_record = self.env['mail.test.container'].browse(self.alias_record.ids)
        test_record.write({
            'name': 'Super Long Name That People May Enter "Even with an internal quoting of stuff"'
        })
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        reply_to_email = f"{test_record.alias_name}@{self.alias_domain}"
        self.assertEqual(msg.reply_to, reply_to_email,
                         'Reply-To: use only email when formataddr > 78 chars')

        # name + company_name would make it blow up: keep record_name in formatting
        self.company_admin.name = "Company name being about 33 chars"
        test_record.write({'name': 'Name that would be more than 78 with company name'})
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, formataddr((test_record.name, reply_to_email)),
                         'Reply-To: use recordname as name in format if recordname + company > 78 chars')

        # no record_name: keep company_name in formatting if ok
        test_record.write({'name': ''})
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, formataddr((self.env.user.company_id.name, reply_to_email)),
                         'Reply-To: use company as name in format when no record name and still < 78 chars')

        # no record_name and company_name make it blow up: keep only email
        self.env.user.company_id.write({'name': 'Super Long Name That People May Enter "Even with an internal quoting of stuff"'})
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, reply_to_email,
                         'Reply-To: use only email when formataddr > 78 chars')

        # whatever the record and company names, email is too long: keep only email
        test_record.write({
            'alias_name': 'Waaaay too long alias name that should make any reply-to blow the 78 characters limit',
            'name': 'Short',
        })
        self.env.user.company_id.write({'name': 'Comp'})
        sanitized_alias_name = 'waaaay-too-long-alias-name-that-should-make-any-reply-to-blow-the-78-characters-limit'
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, f"{sanitized_alias_name}@{self.alias_domain}",
                         'Reply-To: even a long email is ok as only formataddr is problematic')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_no_document_values(self):
        msg = self.Message.create({
            'reply_to': 'test.reply@example.com',
            'email_from': 'test.from@example.com',
        })
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, 'test.reply@example.com')
        self.assertEqual(msg.email_from, 'test.from@example.com')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_no_document(self):
        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        reply_to_name = self.env.user.company_id.name
        reply_to_email = '%s@%s' % (self.alias_catchall, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain -> author
        self.env.company.alias_domain_id = False
        self.assertFalse(self.env.company.catchall_email)

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_document_alias(self):
        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        reply_to_name = '%s %s' % (self.env.user.company_id.name, self.alias_record.name)
        reply_to_email = '%s@%s' % (self.alias_record.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain, no company catchall -> author
        self.alias_record.alias_domain_id = False
        self.env.company.alias_domain_id = False
        self.assertFalse(self.env.company.catchall_email)

        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # alias wins over company, hence no catchall is not an issue
        self.alias_record.alias_domain_id = self.mail_alias_domain

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
    def test_mail_message_values_fromto_document_no_alias(self):
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
    def test_mail_message_values_fromto_document_manual_alias(self):
        test_record = self.env['mail.test.simple'].create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        alias = self.env['mail.alias'].create({
            'alias_name': 'MegaLias',
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

    def test_mail_message_values_fromto_reply_to_force_new(self):
        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id,
            'reply_to_force_new': True,
        })
        self.assertIn('reply_to', msg.message_id.split('@')[0])
        self.assertNotIn('mail.test.container', msg.message_id.split('@')[0])
        self.assertNotIn('-%d-' % self.alias_record.id, msg.message_id.split('@')[0])

    def test_mail_message_values_misc(self):
        """ Test various values on mail.message, notably default values """
        msg = self.env['mail.message'].create({'model': self.alias_record._name, 'res_id': self.alias_record.id})
        self.assertEqual(msg.message_type, 'comment', 'Message should be comments by default')

@tagged("mail_message", "post_install", "-at_install")
class TestMessageAccess(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageAccess, cls).setUpClass()

        cls.user_employee_1 = mail_new_test_user(cls.env, login='tao', groups='base.group_user', name='Tao Lee')
        cls.user_public = mail_new_test_user(cls.env, login='bert', groups='base.group_public', name='Bert Tartignole')
        cls.user_portal = mail_new_test_user(cls.env, login='chell', groups='base.group_portal', name='Chell Gladys')

        cls.group_restricted_channel = cls.env['discuss.channel'].channel_create(name='Channel for Groups', group_id=cls.env.ref('base.group_user').id)
        cls.public_channel = cls.env['discuss.channel'].channel_create(name='Public Channel', group_id=None)
        cls.private_group = cls.env['discuss.channel'].create_group(partners_to=cls.user_employee_1.partner_id.ids, name="Group")
        cls.message = cls.env['mail.message'].create({
            'body': 'My Body',
            'model': 'discuss.channel',
            'res_id': cls.private_group.id,
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
            'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id})
        msg4 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+P Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id,
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg5 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+E Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id,
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})
        msg6 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A Birds', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'discuss.channel', 'res_id': self.private_group.id})
        msg7 = self.env['mail.message'].with_user(self.user_employee).create({
            'subject': '_ZTest', 'body': 'B', 'subtype_id': self.ref('mail.mt_comment')})
        msg8 = self.env['mail.message'].with_user(self.user_employee).create({
            'subject': '_ZTest', 'body': 'B+E', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})

        # Test: Public: 2 messages (recipient)
        messages = self.env['mail.message'].with_user(self.user_public).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg2 | msg4)

        # Test: Employee: 3 messages on Channel Employee can read (employee can read group with default values)
        messages = self.env['mail.message'].with_user(self.user_employee).search([('subject', 'like', '_ZTest'), ('body', 'ilike', 'A')])
        self.assertEqual(messages, msg3 | msg4 | msg5)

        # Test: Employee: 3 messages on Channel Employee can read (employee can read group with default values), 0 on Birds (private group) + 2 messages as author
        messages = self.env['mail.message'].with_user(self.user_employee).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg3 | msg4 | msg5 | msg7 | msg8)

        # Test: Admin: all messages
        messages = self.env['mail.message'].search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg1 | msg2 | msg3 | msg4 | msg5 | msg6 | msg7 | msg8)

        # Test: Portal: 0 (no access to groups, not recipient)
        messages = self.env['mail.message'].with_user(self.user_portal).search([('subject', 'like', '_ZTest')])
        self.assertFalse(messages)

        # Test: Portal: 2 messages (public channel)
        self.group_restricted_channel.write({'group_public_id': False})
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
        self.message.write({'subtype_id': self.ref('mail.mt_comment'), 'res_id': self.public_channel.id})
        self.message.with_user(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_notification(self):
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(b'My attachment'),
            'name': 'doc.txt',
            'res_model': self.message._name,
            'res_id': self.message.id})
        # attach the attachment to the message
        self.message.write({'attachment_ids': [(4, attachment.id)]})
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.message.with_user(self.user_employee).read()
        # Test: Employee has access to attachment, ok because they can read message
        attachment.with_user(self.user_employee).read(['name', 'datas'])

    def test_mail_message_access_read_author(self):
        self.message.write({'author_id': self.user_employee.partner_id.id})
        self.message.with_user(self.user_employee).read()

    def test_mail_message_access_read_doc(self):
        self.message.write({'model': 'discuss.channel', 'res_id': self.public_channel.id})
        # Test: Employee reads the message, ok because linked to a doc they are allowed to read
        self.message.with_user(self.user_employee).read()

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_mail_message_access_create_crash_public(self):
        # Public creates a message on Channel for groups -> ko, no enter rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_public).create({'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id, 'body': 'Test'})

        # Public create a message on Public Channel -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_public).create({'model': 'discuss.channel', 'res_id': self.public_channel.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_crash(self):
        # Do: Employee create a private message -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_employee).create({'model': 'discuss.channel', 'res_id': self.private_group.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_doc(self):
        Message = self.env['mail.message'].with_user(self.user_employee)
        # Do: Employee creates a message on Public Channel -> ok, write access to the related document
        Message.create({'model': 'discuss.channel', 'res_id': self.public_channel.id, 'body': 'Test'})
        # Do: Employee creates a message on Group -> ko, no write access to the related document
        with self.assertRaises(AccessError):
            Message.create({'model': 'discuss.channel', 'res_id': self.private_group.id, 'body': 'Test'})

    def test_mail_message_access_create_private(self):
        self.env['mail.message'].with_user(self.user_employee).create({'body': 'Test'})

    def test_mail_message_access_create_reply(self):
        # TDE FIXME: should it really work ? not sure - catchall makes crash (aka, post will crash also)
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.env['mail.message'].with_user(self.user_employee).create({'model': 'discuss.channel', 'res_id': self.private_group.id, 'body': 'Test', 'parent_id': self.message.id})

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
            body=Markup('<p>This is First Message</p>'), subject='Subject',
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
            ('references', '=', f'{message.message_id} {new_msg.message_id}'),
        ])

        self.assertTrue(new_mail)
        self.assertEqual(new_msg.parent_id, message)
