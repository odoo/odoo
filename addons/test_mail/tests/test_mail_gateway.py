# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import socket

from unittest.mock import DEFAULT
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.data import test_mail_data
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_mail.models.test_mail_models import MailTestGateway
from odoo.addons.test_mail.tests.common import TestMailCommon
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import email_split_and_format, formataddr, mute_logger


@tagged('mail_gateway')
class TestEmailParsing(TestMailCommon):

    def test_message_parse_and_replace_binary_octetstream(self):
        """ Incoming email containing a wrong Content-Type as described in RFC2046/section-3 """
        received_mail = self.from_string(test_mail_data.MAIL_MULTIPART_BINARY_OCTET_STREAM)
        with self.assertLogs('odoo.addons.mail.models.mail_thread', level="WARNING") as capture:
            extracted_mail = self.env['mail.thread']._message_parse_extract_payload(received_mail)

        self.assertEqual(len(extracted_mail['attachments']), 1)
        attachment = extracted_mail['attachments'][0]
        self.assertEqual(attachment.fname, 'hello_world.dat')
        self.assertEqual(attachment.content, b'Hello world\n')
        self.assertEqual(capture.output, [
            ("WARNING:odoo.addons.mail.models.mail_thread:Message containing an unexpected "
             "Content-Type 'binary/octet-stream', assuming 'application/octet-stream'"),
        ])

    def test_message_parse_body(self):
        # test pure plaintext
        plaintext = self.format(test_mail_data.MAIL_TEMPLATE_PLAINTEXT, email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>')
        res = self.env['mail.thread'].message_parse(self.from_string(plaintext))
        self.assertIn('Please call me as soon as possible this afternoon!', res['body'])

        # test multipart / text and html -> html has priority
        multipart = self.format(MAIL_TEMPLATE, email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>')
        res = self.env['mail.thread'].message_parse(self.from_string(multipart))
        self.assertIn('<p>Please call me as soon as possible this afternoon!</p>', res['body'])

        # test multipart / mixed
        res = self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_MULTIPART_MIXED))
        self.assertNotIn(
            'Should create a multipart/mixed: from gmail, *bold*, with attachment', res['body'],
            'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn(
            '<div dir="ltr">Should create a multipart/mixed: from gmail, <b>bold</b>, with attachment.<br clear="all"><div><br></div>', res['body'],
            'message_parse: html version should be in body after parsing multipart/mixed')

        res = self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_MULTIPART_MIXED_TWO))
        self.assertNotIn('First and second part', res['body'],
                         'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn('First part', res['body'],
                      'message_parse: first part of the html version should be in body after parsing multipart/mixed')
        self.assertIn('Second part', res['body'],
                      'message_parse: second part of the html version should be in body after parsing multipart/mixed')

        res = self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_SINGLE_BINARY))
        self.assertEqual(res['body'], '')
        self.assertEqual(res['attachments'][0][0], 'thetruth.pdf')

        res = self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_FORWARDED))
        self.assertIn(res['recipients'], ['lucie@petitebedaine.fr,raoul@grosbedon.fr', 'raoul@grosbedon.fr,lucie@petitebedaine.fr'])

        res = self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_MULTIPART_WEIRD_FILENAME))
        self.assertEqual(res['attachments'][0][0], '62_@;,][)=.(ÇÀÉ.txt')

    def test_message_parse_bugs(self):
        """ Various corner cases or message parsing """
        # message without Final-Recipient
        self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_NO_FINAL_RECIPIENT))

        # message with empty body (including only void characters)
        res = self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_NO_BODY))
        self.assertEqual(res['body'], '\n \n', 'Gateway should not crash with void content')

    def test_message_parse_eml(self):
        # Test that the parsing of mail with embedded emails as eml(msg) which generates empty attachments, can be processed.
        mail = self.format(test_mail_data.MAIL_EML_ATTACHMENT, email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>', to='generic@test.com')
        self.env['mail.thread'].message_parse(self.from_string(mail))

    def test_message_parse_eml_bounce_headers(self):
        # Test Text/RFC822-Headers MIME content-type
        msg_id = '<861878175823148.1577183525.736005783081055-openerp-19177-account.invoice@mycompany.example.com>'
        mail = self.format(
            test_mail_data.MAIL_EML_ATTACHMENT_BOUNCE_HEADERS,
            email_from='MAILER-DAEMON@example.com (Mail Delivery System)',
            to='test_bounce+82240-account.invoice-19177@mycompany.example.com',
            # msg_id goes to the attachment's Message-Id header
            msg_id=msg_id,
        )
        res = self.env['mail.thread'].message_parse(self.from_string(mail))

        self.assertEqual(res['bounced_msg_id'], [msg_id], "Message-Id is not extracted from Text/RFC822-Headers attachment")

    def test_message_parse_plaintext(self):
        """ Incoming email in plaintext should be stored as html """
        mail = self.format(test_mail_data.MAIL_TEMPLATE_PLAINTEXT, email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>', to='generic@test.com')
        res = self.env['mail.thread'].message_parse(self.from_string(mail))
        self.assertIn('<pre>\nPlease call me as soon as possible this afternoon!\n\n--\nSylvie\n</pre>', res['body'])

    def test_message_parse_xhtml(self):
        # Test that the parsing of XHTML mails does not fail
        self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_XHTML))

@tagged('mail_gateway')
class TestMailAlias(TestMailCommon):

    @users('employee')
    def test_alias_creation(self):
        record = self.env['mail.test.container'].create({
            'name': 'Test Record',
            'alias_name': 'alias.test',
            'alias_contact': 'followers',
        })
        self.assertEqual(record.alias_id.alias_model_id, self.env['ir.model']._get('mail.test.container'))
        self.assertEqual(record.alias_id.alias_force_thread_id, record.id)
        self.assertEqual(record.alias_id.alias_parent_model_id, self.env['ir.model']._get('mail.test.container'))
        self.assertEqual(record.alias_id.alias_parent_thread_id, record.id)
        self.assertEqual(record.alias_id.alias_name, 'alias.test')
        self.assertEqual(record.alias_id.alias_contact, 'followers')

        record.write({
            'alias_name': 'better.alias.test',
            'alias_defaults': "{'default_name': 'defaults'}"
        })
        self.assertEqual(record.alias_id.alias_name, 'better.alias.test')
        self.assertEqual(record.alias_id.alias_defaults, "{'default_name': 'defaults'}")

        with self.assertRaises(exceptions.AccessError):
            record.write({
                'alias_force_thread_id': 0,
            })

        with self.assertRaises(exceptions.AccessError):
            record.write({
                'alias_model_id': self.env['ir.model']._get('mail.test.gateway').id,
            })

        with self.assertRaises(exceptions.ValidationError):
            record.write({'alias_defaults': "{'custom_field': brokendict"})

    def test_alias_sanitize(self):
        alias = self.env['mail.alias'].create({
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_name': 'bidule...inc.',
        })
        self.assertEqual(alias.alias_name, 'bidule.inc', 'Emails cannot start or end with a dot, there cannot be a sequence of dots.')

    def test_alias_setup(self):
        alias = self.env['mail.alias'].create({
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_name': 'b4r+_#_R3wl$$',
        })
        self.assertEqual(alias.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

        with self.assertRaises(exceptions.ValidationError):
            alias.write({'alias_defaults': "{'custom_field': brokendict"})

    def test_alias_name_unique(self):
        alias_model_id = self.env['ir.model']._get('mail.test.gateway').id
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.alias')
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param('mail.bounce.alias')

        # test you cannot create aliases matching bounce / catchall
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create({'alias_model_id': alias_model_id, 'alias_name': catchall_alias})
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create({'alias_model_id': alias_model_id, 'alias_name': bounce_alias})

        new_mail_alias = self.env['mail.alias'].create({
            'alias_model_id': alias_model_id,
            'alias_name': 'unused.test.alias'
        })

        # test that re-using catchall and bounce alias raises UserError
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            new_mail_alias.write({
                'alias_name': catchall_alias
            })
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            new_mail_alias.write({
                'alias_name': bounce_alias
            })

        new_mail_alias.write({'alias_name': 'another.unused.test.alias'})

        # test that duplicating an alias should have blank name
        copy_new_mail_alias = new_mail_alias.copy()
        self.assertFalse(copy_new_mail_alias.alias_name)

        # cannot set catchall / bounce to used alias
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['ir.config_parameter'].sudo().set_param('mail.catchall.alias', new_mail_alias.alias_name)
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['ir.config_parameter'].sudo().set_param('mail.bounce.alias', new_mail_alias.alias_name)


@tagged('mail_gateway')
class TestMailAliasMixin(TestMailCommon):

    @users('employee')
    def test_alias_mixin_copy_content(self):
        self.assertFalse(self.env.user.has_group('base.group_system'), 'Test user should not have Administrator access')

        record = self.env['mail.test.container'].create({
            'name': 'Test Record',
            'alias_name': 'test.record',
            'alias_contact': 'followers',
            'alias_bounced_content': False,
        })
        self.assertFalse(record.alias_bounced_content)
        record_copy = record.copy()
        self.assertFalse(record_copy.alias_bounced_content)

        new_content = '<p>Bounced Content</p>'
        record_copy.write({'alias_bounced_content': new_content})
        self.assertEqual(record_copy.alias_bounced_content, new_content)
        record_copy2 = record_copy.copy()
        self.assertEqual(record_copy2.alias_bounced_content, new_content)


@tagged('mail_gateway')
class TestMailgateway(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailgateway, cls).setUpClass()
        cls.test_model = cls.env['ir.model']._get('mail.test.gateway')
        cls.email_from = '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>'

        cls.test_record = cls.env['mail.test.gateway'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        }).with_context({})

        cls.partner_1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })
        # groups@.. will cause the creation of new mail.test.gateway
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': cls.test_model.id,
            'alias_contact': 'everyone'})

        # Set a first message on public group to test update and hierarchy
        cls.fake_email = cls._create_gateway_message(cls.test_record, '123456')

        cls._init_mail_gateway()

    @classmethod
    def _create_gateway_message(cls, record, msg_id_prefix, **values):
        msg_values = {
            'author_id': cls.partner_1.id,
            'email_from': cls.partner_1.email_formatted,
            'body': '<p>Generic body</p>',
            'message_id': f'<{msg_id_prefix}-openerp-{record.id}-{record._name}@{socket.gethostname()}>',
            'message_type': 'email',
            'model': record._name,
            'res_id': record.id,
            'subject': 'Generic Message',
            'subtype_id': cls.env.ref('mail.mt_comment').id,
        }
        msg_values.update(**values)
        return cls.env['mail.message'].create(msg_values)

    # --------------------------------------------------
    # Base low-level tests
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_basic(self):
        """ Test details of created message going through mailgateway """
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Specific')

        # Test: one group created by mailgateway administrator as user_id is not set
        self.assertEqual(len(record), 1, 'message_process: a new mail.test should have been created')
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.env.uid)

        # Test: one message that is the incoming email
        self.assertEqual(len(record.message_ids), 1)
        msg = record.message_ids[0]
        self.assertEqual(msg.subject, 'Specific')
        self.assertIn('Please call me as soon as possible this afternoon!', msg.body)
        self.assertEqual(msg.message_type, 'email')
        self.assertEqual(msg.subtype_id, self.env.ref('mail.mt_comment'))

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_cid(self):
        record = self.format_and_process(test_mail_data.MAIL_MULTIPART_IMAGE, self.email_from, 'groups@test.com')
        message = record.message_ids[0]
        for attachment in message.attachment_ids:
            self.assertIn('/web/image/%s' % attachment.id, message.body)
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['rosaçée.gif', 'verte!µ.gif', 'orangée.gif']))

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_followers(self):
        """ Incoming email: recognized author not archived and not odoobot: added as follower """
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, 'groups@test.com')

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: recognized email -> author_id')
        self.assertEqual(record.message_ids[0].email_from, self.partner_1.email_formatted)
        self.assertEqual(record.message_follower_ids.partner_id, self.partner_1,
                         'message_process: recognized email -> added as follower')
        self.assertEqual(record.message_partner_ids, self.partner_1,
                         'message_process: recognized email -> added as follower')

        # just an email -> no follower
        with self.mock_mail_gateway():
            record2 = self.format_and_process(
                MAIL_TEMPLATE, self.email_from, 'groups@test.com',
                subject='Another Email')

        self.assertEqual(record2.message_ids[0].author_id, self.env['res.partner'])
        self.assertEqual(record2.message_ids[0].email_from, self.email_from)
        self.assertEqual(record2.message_follower_ids.partner_id, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')
        self.assertEqual(record2.message_partner_ids, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')

        # archived partner -> no follower
        self.partner_1.active = False
        self.partner_1.flush()
        with self.mock_mail_gateway():
            record3 = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted, 'groups@test.com',
                subject='Yet Another Email')

        self.assertEqual(record3.message_ids[0].author_id, self.env['res.partner'])
        self.assertEqual(record3.message_ids[0].email_from, self.partner_1.email_formatted)
        self.assertEqual(record3.message_follower_ids.partner_id, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')
        self.assertEqual(record3.message_partner_ids, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')


        # partner_root -> never again
        odoobot = self.env.ref('base.partner_root')
        odoobot.active = True
        odoobot.email = 'odoobot@example.com'
        with self.mock_mail_gateway():
            record4 = self.format_and_process(
                MAIL_TEMPLATE, odoobot.email_formatted, 'groups@test.com',
                subject='Odoobot Automatic Answer')

        self.assertEqual(record4.message_ids[0].author_id, odoobot)
        self.assertEqual(record4.message_ids[0].email_from, odoobot.email_formatted)
        self.assertEqual(record4.message_follower_ids.partner_id, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')
        self.assertEqual(record4.message_partner_ids, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')

    # --------------------------------------------------
    # Author recognition
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_email_from(self):
        """ Incoming email: not recognized author: email_from, no author_id, no followers """
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com')
        self.assertFalse(record.message_ids[0].author_id, 'message_process: unrecognized email -> no author_id')
        self.assertEqual(record.message_ids[0].email_from, self.email_from)
        self.assertEqual(len(record.message_partner_ids), 0,
                         'message_process: newly create group should not have any follower')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_author(self):
        """ Incoming email: recognized author: email_from, author_id, added as follower """
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, 'groups@test.com', subject='Test1')

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: recognized email -> author_id')
        self.assertEqual(record.message_ids[0].email_from, self.partner_1.email_formatted)
        self.assertNotSentEmail()  # No notification / bounce should be sent

        # Email recognized if partner has a formatted email
        self.partner_1.write({'email': '"Valid Lelitre" <%s>' % self.partner_1.email})
        record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email, 'groups@test.com', subject='Test2')

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: recognized email -> author_id')
        self.assertEqual(record.message_ids[0].email_from, self.partner_1.email)
        self.assertNotSentEmail()  # No notification / bounce should be sent

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_partner_find(self):
        """ Finding the partner based on email, based on partner / user / follower """
        self.alias.write({'alias_force_thread_id': self.test_record.id})
        from_1 = self.env['res.partner'].create({'name': 'Brice Denisse', 'email': 'from.test@example.com'})

        self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, 'groups@test.com')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_1)
        self.test_record.message_unsubscribe([from_1.id])

        from_2 = mail_new_test_user(self.env, login='B', groups='base.group_user', name='User Denisse', email='from.test@example.com')

        self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, 'groups@test.com')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_2.partner_id)
        self.test_record.message_unsubscribe([from_2.partner_id.id])

        from_3 = self.env['res.partner'].create({'name': 'FOllower Denisse', 'email': 'from.test@example.com'})
        self.test_record.message_subscribe([from_3.id])

        self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, 'groups@test.com')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_3)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_author_exclude_alias(self):
        """ Do not set alias as author to avoid including aliases in discussions """
        from_1 = self.env['res.partner'].create({'name': 'Brice Denisse', 'email': 'from.test@test.com'})
        self.env['mail.alias'].create({
            'alias_name': 'from.test',
            'alias_model_id': self.env['ir.model']._get('mail.test.gateway').id
        })

        record = self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, 'groups@test.com')
        self.assertFalse(record.message_ids[0].author_id)
        self.assertEqual(record.message_ids[0].email_from, from_1.email_formatted)

    # --------------------------------------------------
    # Alias configuration
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_config_bounced_content(self):
        """ Custom bounced message for the alias => Received this custom message """
        self.alias.write({
            'alias_contact': 'partners',
            'alias_bounced_content': '<p>What Is Dead May Never Die</p>'
        })

        # Test: custom bounced content
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Should Bounce')
        self.assertFalse(record, 'message_process: should have bounced')
        self.assertSentEmail('"MAILER-DAEMON" <bounce.test@test.com>', ['whatever-2a840@postmaster.twitter.com'], body_content='<p>What Is Dead May Never Die</p>')

        for empty_content in [
                '<p><br></p>', '<p><br> </p>', '<p><br /></p >',
                '<p style="margin: 4px"></p>',
                '<div style="margin: 4px"></div>',
                '<p class="oe_testing"><br></p>',
                '<p><span style="font-weight: bolder;"><font style="color: rgb(255, 0, 0);" class=" "></font></span><br></p>',
            ]:
            self.alias.write({
                'alias_contact': 'partners',
                'alias_bounced_content': empty_content,
            })

            # Test: with "empty" bounced content (simulate view, putting always '<p></br></p>' in html field)
            with self.mock_mail_gateway():
                record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Should Bounce')
            self.assertFalse(record, 'message_process: should have bounced')
            # Check if default (hardcoded) value is in the mail content
            self.assertSentEmail(
                '"MAILER-DAEMON" <bounce.test@test.com>', ['whatever-2a840@postmaster.twitter.com'],
                body_content='<p>Dear Sender,<br /><br />\nThe message below could not be accepted by the address %s' % self.alias.display_name.lower()
            )

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_message_process_alias_config_bounced_to(self):
        """ Check bounce message contains the bouncing alias, not a generic "to" """
        self.alias.write({'alias_contact': 'partners'})
        bounce_message_with_alias = '<p>Dear Sender,<br /><br />\nThe message below could not be accepted by the address %s' % self.alias.display_name.lower()

        # Bounce is To
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE, self.email_from, 'groups@example.com',
                cc='other@gmail.com', subject='Should Bounce')
        self.assertIn(bounce_message_with_alias, self._mails[0].get('body'))

        # Bounce is CC
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE, self.email_from, 'other@gmail.com',
                cc='groups@example.com', subject='Should Bounce')
        self.assertIn(bounce_message_with_alias, self._mails[0].get('body'))

        # Bounce is part of To
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE, self.email_from, 'other@gmail.com, groups@example.com',
                subject='Should Bounce')
        self.assertIn(bounce_message_with_alias, self._mails[0].get('body'))

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_defaults(self):
        """ Test alias defaults and inner values """
        self.alias.write({
            'alias_user_id': self.user_employee.id,
            'alias_defaults': "{'custom_field': 'defaults_custom'}"
        })

        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Specific')
        self.assertEqual(len(record), 1)
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id)
        self.assertEqual(record.name, 'Specific')
        self.assertEqual(record.custom_field, 'defaults_custom')

        self.alias.write({'alias_defaults': '""'})
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Specific2')
        self.assertEqual(len(record), 1)
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id)
        self.assertEqual(record.name, 'Specific2')
        self.assertFalse(record.custom_field)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_user_id(self):
        """ Test alias ownership """
        self.alias.write({'alias_user_id': self.user_employee.id})

        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com')
        self.assertEqual(len(record), 1)
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_everyone(self):
        """ Incoming email: everyone: new record + message_new """
        self.alias.write({'alias_contact': 'everyone'})

        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Specific')
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.message_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_partners_bounce(self):
        """ Incoming email from an unknown partner on a Partners only alias -> bounce + test bounce email """
        self.alias.write({'alias_contact': 'partners'})

        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Should Bounce')
        self.assertFalse(record)
        self.assertSentEmail('"MAILER-DAEMON" <bounce.test@test.com>', ['whatever-2a840@postmaster.twitter.com'], subject='Re: Should Bounce')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_followers_bounce(self):
        """ Incoming email from unknown partner / not follower partner on a Followers only alias -> bounce """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.env['ir.model']._get('mail.test.gateway').id,
            'alias_parent_thread_id': self.test_record.id,
        })

        # Test: unknown on followers alias -> bounce
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Should Bounce')
        self.assertFalse(record, 'message_process: should have bounced')
        self.assertSentEmail('"MAILER-DAEMON" <bounce.test@test.com>', ['whatever-2a840@postmaster.twitter.com'], subject='Re: Should Bounce')

        # Test: partner on followers alias -> bounce
        self._init_mail_mock()
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, 'groups@test.com', subject='Should Bounce')
        self.assertFalse(record, 'message_process: should have bounced')
        self.assertSentEmail('"MAILER-DAEMON" <bounce.test@test.com>', ['whatever-2a840@postmaster.twitter.com'], subject='Re: Should Bounce')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_partner(self):
        """ Incoming email from a known partner on a Partners alias -> ok (+ test on alias.user_id) """
        self.alias.write({'alias_contact': 'partners'})
        record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, 'groups@test.com')

        # Test: one group created by alias user
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.message_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_followers(self):
        """ Incoming email from a parent document follower on a Followers only alias -> ok """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.env['ir.model']._get('mail.test.gateway').id,
            'alias_parent_thread_id': self.test_record.id,
        })
        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, 'groups@test.com')

        # Test: one group created by Raoul (or Sylvie maybe, if we implement it)
        self.assertEqual(len(record), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_update(self):
        """ Incoming email update discussion + notification email """
        self.alias.write({'alias_force_thread_id': self.test_record.id})

        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, self.email_from, 'groups@test.com>',
                msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>', subject='Re: cats')

        # Test: no new group + new message
        self.assertFalse(record, 'message_process: alias update should not create new records')
        self.assertEqual(len(self.test_record.message_ids), 2)
        # Test: sent emails: 1 (Sylvie copy of the incoming email)
        self.assertSentEmail(self.email_from, [self.partner_1], subject='Re: cats')

    # --------------------------------------------------
    # Creator recognition
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_create_uid_crash(self):
        def _employee_crash(*args, **kwargs):
            """ If employee is test employee, consider he has no access on document """
            recordset = args[0]
            if recordset.env.uid == self.user_employee.id and not recordset.env.su:
                if kwargs.get('raise_exception', True):
                    raise exceptions.AccessError('Hop hop hop Ernest, please step back.')
                return False
            return DEFAULT

        with patch.object(MailTestGateway, 'check_access_rights', autospec=True, side_effect=_employee_crash):
            record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, 'groups@test.com', subject='NoEmployeeAllowed')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'NoEmployeeAllowed')
        self.assertEqual(record.message_ids[0].create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_create_uid_email(self):
        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, 'groups@test.com', subject='Email Found')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'Email Found')
        self.assertEqual(record.message_ids[0].create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

        record = self.format_and_process(MAIL_TEMPLATE, 'Another name <%s>' % self.user_employee.email, 'groups@test.com', subject='Email OtherName')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'Email OtherName')
        self.assertEqual(record.message_ids[0].create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_normalized, 'groups@test.com', subject='Email SimpleEmail')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'Email SimpleEmail')
        self.assertEqual(record.message_ids[0].create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_create_uid_email_follower(self):
        self.alias.write({
            'alias_parent_model_id': self.test_model.id,
            'alias_parent_thread_id': self.test_record.id,
        })
        follower_user = mail_new_test_user(self.env, login='better', groups='base.group_user', name='Ernest Follower', email=self.user_employee.email)
        self.test_record.message_subscribe(follower_user.partner_id.ids)

        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, 'groups@test.com', subject='FollowerWinner')
        self.assertEqual(record.create_uid, follower_user)
        self.assertEqual(record.message_ids[0].subject, 'FollowerWinner')
        self.assertEqual(record.message_ids[0].create_uid, follower_user)
        self.assertEqual(record.message_ids[0].author_id, follower_user.partner_id)

        # name order win
        self.test_record.message_unsubscribe(follower_user.partner_id.ids)
        self.test_record.flush()
        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, 'groups@test.com', subject='FirstFoundWinner')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'FirstFoundWinner')
        self.assertEqual(record.message_ids[0].create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    # --------------------------------------------------
    # Alias routing management
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_alias_no_domain(self):
        """ Incoming email: write to alias even if no domain set: considered as valid alias """
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', '')

        new_record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, 'groups@another.domain.com', subject='Test Subject')
        # Test: one group created
        self.assertEqual(len(new_record), 1, 'message_process: a new mail.test.simple should have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_alias_forward_bypass_reply_first(self):
        """ Incoming email: write to two "new thread" alias, one as a reply, one being another model -> consider as a forward """
        self.assertEqual(len(self.test_record.message_ids), 1)

        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_contact': 'everyone',
        })
        new_rec = self.format_and_process(
            MAIL_TEMPLATE, self.partner_1.email_formatted,
            '%s@%s, %s@%s' % (new_alias_2.alias_name, self.alias_domain, self.alias.alias_name, self.alias_domain),
            subject='Test Subject',
            extra='In-Reply-To:\r\n\t%s\n' % self.fake_email.message_id,
            target_model=new_alias_2.alias_model_id.model
        )
        # Forward created a new record in mail.test
        self.assertEqual(len(new_rec), 1, 'message_process: a new mail.test should have been created')
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        # No new post on test_record, no new record in mail.test.simple either
        self.assertEqual(len(self.test_record.message_ids), 1, 'message_process: should not post on replied record as forward should bypass it')
        new_simple = self.env['mail.test.simple'].search([('name', '=', 'Test Subject')])
        self.assertEqual(len(new_simple), 0, 'message_process: a new mail.test should not have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_alias_forward_bypass_reply_second(self):
        """ Incoming email: write to two "new thread" alias, one as a reply, one being another model -> consider as a forward """
        self.assertEqual(len(self.test_record.message_ids), 1)

        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_contact': 'everyone',
        })
        new_rec = self.format_and_process(
            MAIL_TEMPLATE, self.partner_1.email_formatted,
            '%s@%s, %s@%s' % (self.alias.alias_name, self.alias_domain, new_alias_2.alias_name, self.alias_domain),
            subject='Test Subject',
            extra='In-Reply-To:\r\n\t%s\n' % self.fake_email.message_id,
            target_model=new_alias_2.alias_model_id.model
        )
        # Forward created a new record in mail.test
        self.assertEqual(len(new_rec), 1, 'message_process: a new mail.test should have been created')
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        # No new post on test_record, no new record in mail.test.simple either
        self.assertEqual(len(self.test_record.message_ids), 1, 'message_process: should not post on replied record as forward should bypass it')
        new_simple = self.env['mail.test.simple'].search([('name', '=', 'Test Subject')])
        self.assertEqual(len(new_simple), 0, 'message_process: a new mail.test should not have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_alias_forward_bypass_update_alias(self):
        """ Incoming email: write to one "update", one "new thread" alias, one as a reply, one being another model -> consider as a forward """
        self.assertEqual(len(self.test_record.message_ids), 1)
        self.alias.write({
            'alias_force_thread_id': self.test_record.id,
        })

        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_contact': 'everyone',
        })
        new_rec = self.format_and_process(
            MAIL_TEMPLATE, self.partner_1.email_formatted,
            '%s@%s, %s@%s' % (new_alias_2.alias_name, self.alias_domain, self.alias.alias_name, self.alias_domain),
            subject='Test Subject',
            extra='In-Reply-To:\r\n\t%s\n' % self.fake_email.message_id,
            target_model=new_alias_2.alias_model_id.model
        )
        # Forward created a new record in mail.test
        self.assertEqual(len(new_rec), 1, 'message_process: a new mail.test should have been created')
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        # No new post on test_record, no new record in mail.test.simple either
        self.assertEqual(len(self.test_record.message_ids), 1, 'message_process: should not post on replied record as forward should bypass it')
        # No new record on first alias model
        new_simple = self.env['mail.test.gateway'].search([('name', '=', 'Test Subject')])
        self.assertEqual(len(new_simple), 0, 'message_process: a new mail.test should not have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_alias_multiple_new(self):
        """ Incoming email: write to two aliases creating records: both should be activated """
        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_contact': 'everyone',
        })
        new_rec = self.format_and_process(
            MAIL_TEMPLATE, self.partner_1.email_formatted,
            '%s@%s, %s@%s' % (self.alias.alias_name, self.alias_domain, new_alias_2.alias_name, self.alias_domain),
            subject='Test Subject',
            target_model=new_alias_2.alias_model_id.model
        )
        # New record in both mail.test (new_alias_2) and mail.test.simple (self.alias)
        self.assertEqual(len(new_rec), 1, 'message_process: a new mail.test should have been created')
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        new_simple = self.env['mail.test.gateway'].search([('name', '=', 'Test Subject')])
        self.assertEqual(len(new_simple), 1, 'message_process: a new mail.test should have been created')

    # --------------------------------------------------
    # Email Management
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_bounce(self):
        """Incoming email: bounce  using bounce alias: no record creation """
        with self.mock_mail_gateway():
            new_recs = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted,
                '%s@%s' % (self.alias_bounce, self.alias_domain),
                subject='Should bounce',
            )
        self.assertFalse(new_recs)
        self.assertNotSentEmail()

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_bounce_other_recipients(self):
        """Incoming email: bounce processing: bounce should be computed even if not first recipient """
        with self.mock_mail_gateway():
            new_recs = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted,
                '%s@%s, %s@%s' % (
                    self.alias.alias_name, self.alias_domain,
                    self.alias_bounce, self.alias_domain
                ),
                subject='Should bounce',
            )
        self.assertFalse(new_recs)
        self.assertNotSentEmail()

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_message_route_write_to_catchall(self):
        """ Writing directly to catchall should bounce """
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted,
                '"My Super Catchall" <%s@%s>' % (self.alias_catchall, self.alias_domain),
                subject='Should Bounce')
        self.assertFalse(record)
        self.assertSentEmail('"MAILER-DAEMON" <bounce.test@test.com>', ['whatever-2a840@postmaster.twitter.com'], subject='Re: Should Bounce')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_write_to_catchall_other_recipients_first(self):
        """ Writing directly to catchall and a valid alias should take alias """
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted,
                '%s@%s, %s@%s' % (self.alias_catchall, self.alias_domain, self.alias.alias_name, self.alias_domain),
                subject='Catchall Not Blocking'
            )
        # Test: one group created
        self.assertEqual(len(record), 1, 'message_process: a new mail.test should have been created')
        # No bounce email
        self.assertNotSentEmail()

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_write_to_catchall_other_recipients_second(self):
        """ Writing directly to catchall and a valid alias should take alias """
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted,
                '%s@%s, %s@%s' % (self.alias.alias_name, self.alias_domain, self.alias_catchall, self.alias_domain),
                subject='Catchall Not Blocking'
            )
        # Test: one group created
        self.assertEqual(len(record), 1, 'message_process: a new mail.test should have been created')
        # No bounce email
        self.assertNotSentEmail()

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_alias(self):
        """ Writing to bounce alias is considered as a bounce even if not multipart/report bounce structure """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounced_mail_id = 4442
        bounce_email_to = '%s@%s' % ('bounce.test', 'test.com')
        record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, bounce_email_to, subject='Undelivered Mail Returned to Sender')
        self.assertFalse(record)
        # No information found in bounce email -> not possible to do anything except avoiding email
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_from_mailer_demon(self):
        """ MAILER_DAEMON emails are considered as bounce """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        record = self.format_and_process(MAIL_TEMPLATE, 'MAILER-DAEMON@example.com', 'groups@test.com', subject='Undelivered Mail Returned to Sender')
        self.assertFalse(record)
        # No information found in bounce email -> not possible to do anything except avoiding email
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_multipart_alias(self):
        """ Multipart/report bounce correctly make related partner bounce """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounced_mail_id = 4442
        bounce_email_to = '%s@%s' % ('bounce.test', 'test.com')
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, self.partner_1.email_formatted, bounce_email_to, subject='Undelivered Mail Returned to Sender')
        self.assertFalse(record)
        # Missing in reply to message_id -> cannot find original record
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_multipart_alias_reply(self):
        """ Multipart/report bounce correctly make related partner and record found in bounce email bounce """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounced_mail_id = 4442
        bounce_email_to = '%s@%s' % ('bounce.test', 'test.com')
        extra = self.fake_email.message_id
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, self.partner_1.email_formatted, bounce_email_to, subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 1)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_multipart_alias_whatever_from(self):
        """ Multipart/report bounce correctly make related record found in bounce email bounce """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounced_mail_id = 4442
        bounce_email_to = '%s@%s' % ('bounce.test', 'test.com')
        extra = self.fake_email.message_id
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, 'Whatever <what@ever.com>', bounce_email_to, subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 1)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_multipart_whatever_to_and_from(self):
        """ Multipart/report bounce correctly make related record found in bounce email bounce """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        extra = self.fake_email.message_id
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, 'Whatever <what@ever.com>', 'groups@test.com', subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 1)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_records_channel(self):
        """ Test blacklist allow to multi-bounce and auto update of mail.channel """
        other_record = self.env['mail.test.gateway'].create({
            'email_from': 'Another name <%s>' % self.partner_1.email
        })
        yet_other_record = self.env['mail.test.gateway'].create({
            'email_from': 'Yet Another name <%s>' % self.partner_1.email.upper()
        })
        test_channel = self.env['mail.channel'].create({
            'name': 'Test',
            'channel_partner_ids': [(4, self.partner_1.id)],
        })
        self.fake_email.write({
            'model': 'mail.channel',
            'res_id': test_channel.id,
        })
        self.assertIn(self.partner_1, test_channel.channel_partner_ids)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(other_record.message_bounce, 0)
        self.assertEqual(yet_other_record.message_bounce, 0)

        extra = self.fake_email.message_id
        for i in range(10):
            record = self.format_and_process(test_mail_data.MAIL_BOUNCE, 'A third name <%s>' % self.partner_1.email, 'groups@test.com', subject='Undelivered Mail Returned to Sender', extra=extra)
            self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 10)
        self.assertEqual(self.test_record.message_bounce, 0)
        self.assertEqual(other_record.message_bounce, 10)
        self.assertEqual(yet_other_record.message_bounce, 10)
        self.assertNotIn(self.partner_1, test_channel.channel_partner_ids)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_records_partner(self):
        """ Test blacklist + bounce on ``res.partner`` model """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.fake_email.write({
            'model': 'res.partner',
            'res_id': self.partner_1.id,
        })

        extra = self.fake_email.message_id
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, self.partner_1.email_formatted, 'groups@test.com', subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 0)

    # --------------------------------------------------
    # Thread formation
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_in_reply_to(self):
        """ Incoming email using in-rely-to should go into the right destination even with a wrong destination """
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, 'valid.other@gmail.com', 'erroneous@test.com>',
            subject='Re: news', extra='In-Reply-To:\r\n\t%s\n' % self.fake_email.message_id)

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references(self):
        """ Incoming email using references should go into the right destination even with a wrong destination """
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'erroneous@test.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id)

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_references_multi_parent(self):
        """ Incoming email with multiple references  """
        reply1 = self._create_gateway_message(
            self.test_record, 'reply1', parent_id=self.fake_email.id,
        )
        reply2 = self._create_gateway_message(
            self.test_record, 'reply2', parent_id=self.fake_email.id,
            subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
        )
        reply1_1 = self._create_gateway_message(
            self.test_record, 'reply1_1', parent_id=reply1.id,
            subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
        )
        reply2_1 = self._create_gateway_message(
            self.test_record, 'reply2_1', parent_id=reply2.id,
        )

        # reply to reply1 using multiple references
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'groups@test.com',
            subject='Reply to reply1',
            extra=f'References: {reply1.message_id} {self.fake_email.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: reply to a comment should be a comment')

        # ordering should not impact
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'groups@test.com',
            subject='Reply to reply1 (order issue)',
            extra=f'References: {self.fake_email.message_id} {reply1.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: reply to a comment should be a comment')

        # history with last one being a note
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'groups@test.com',
            subject='Reply to reply1_1',
            extra=f'References: {reply1_1.message_id} {self.fake_email.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_note'), 'Mail: reply to a note should be a note')

        # messed up history (two child branches): gateway initial parent is newest one
        # (then may change with flattening when posting on record)
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'groups@test.com',
            subject='Reply to reply2_1 (with noise)',
            extra=f'References: {reply1_1.message_id} {reply2_1.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment (before flattening)')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_references_multi_parent_notflat(self):
        """ Incoming email with multiple references with ``_mail_flat_thread``
        being False (mail.group/mail.channel behavior like). """
        test_record = self.env['mail.test.gateway.groups'].create({
            'alias_name': 'test.gateway',
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        })

        # Set a first message on public group to test update and hierarchy
        first_msg = self._create_gateway_message(test_record, 'first_msg')
        reply1 = self._create_gateway_message(
            test_record, 'reply1', parent_id=first_msg.id,
        )
        reply2 = self._create_gateway_message(
            test_record, 'reply2', parent_id=first_msg.id,
            subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
        )
        reply1_1 = self._create_gateway_message(
            test_record, 'reply1_1', parent_id=reply1.id,
            subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
        )
        reply2_1 = self._create_gateway_message(
            test_record, 'reply2_1', parent_id=reply2.id,
        )

        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.gateway@test.com',
            subject='Reply to reply1',
            extra=f'References: {reply1.message_id}'
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, first_msg, 'Mail: pseudo no flattening: getting up one level (reply1 parent)')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment')

        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.gateway@test.com',
            subject='Reply to reply1_1 (with noise)',
            extra=f'References: {reply1_1.message_id} {reply1.message_id} {reply1.message_id}'
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, reply1, 'Mail: pseudo no flattening: getting up one level (reply1_1 parent)')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_note'), 'Mail: reply to a note should be a note')

        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.gateway@test.com',
            subject='Reply to reply2_1 (with noise)',
            extra=f'References: {reply2_1.message_id} {reply1_1.message_id}'
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, reply2, 'Mail: pseudo no flattening: getting up one level (reply2_1 parent')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment')

        # no references: new discussion thread started
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.gateway@test.com',
            subject='New thread',
            extra='References:'
        )
        new_thread = test_record.message_ids[0]
        self.assertFalse(new_thread.parent_id, 'Mail: pseudo no flattening: no parent means new thread')
        self.assertEqual(new_thread.subject, 'New thread')
        self.assertEqual(new_thread.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment')

        # mixed up references: newer message wins
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.gateway@test.com',
            subject='New thread',
            extra=f'References: {new_thread.message_id} {reply1_1.message_id}'
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, new_thread)
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_references_external(self):
        """ Incoming email being a reply to an external email processed by odoo should update thread accordingly """
        new_message_id = '<ThisIsTooMuchFake.MonsterEmail.789@agrolait.com>'
        self.fake_email.write({
            'message_id': new_message_id
        })
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'erroneous@test.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id)

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_references_external_buggy_message_id(self):
        """
        Incoming email being a reply to an external email processed by
        odoo should update thread accordingly. Special case when the
        external mail service wrongly folds the message_id on several
        lines.
        """
        new_message_id = '<ThisIsTooMuchFake.MonsterEmail.789@agrolait.com>'
        buggy_message_id = new_message_id.replace('MonsterEmail', 'Monster\r\n  Email')
        self.fake_email.write({
            'message_id': new_message_id
        })
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'erroneous@test.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % buggy_message_id)

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_references_forward(self):
        """ Incoming email using references but with alias forward should not go into references destination """
        self.env['mail.alias'].create({
            'alias_name': 'test.alias',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_contact': 'everyone',
        })
        init_msg_count = len(self.test_record.message_ids)
        res_test = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.alias@test.com',
            subject='My Dear Forward', extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            target_model='mail.test.container')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count)
        self.assertEqual(len(self.fake_email.child_ids), 0)
        self.assertEqual(res_test.name, 'My Dear Forward')
        self.assertEqual(len(res_test.message_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references_forward_same_model(self):
        """ Incoming email using references but with alias forward on same model should be considered as a reply """
        self.env['mail.alias'].create({
            'alias_name': 'test.alias',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.gateway').id,
            'alias_contact': 'everyone',
        })
        init_msg_count = len(self.test_record.message_ids)
        res_test = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.alias@test.com',
            subject='My Dear Forward', extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            target_model='mail.test.container')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(len(self.fake_email.child_ids), 1)
        self.assertFalse(res_test)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references_forward_cc(self):
        """ Incoming email using references but with alias forward in CC should be considered as a repy (To > Cc) """
        self.env['mail.alias'].create({
            'alias_name': 'test.alias',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_contact': 'everyone',
        })
        init_msg_count = len(self.test_record.message_ids)
        res_test = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'catchall.test@test.com', cc='test.alias@test.com',
            subject='My Dear Forward', extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            target_model='mail.test.container')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(len(self.fake_email.child_ids), 1)
        self.assertFalse(res_test)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_reply_to_new_thread(self):
        """ Test replies not being considered as replies but use destination information instead (aka, mass post + specific reply to using aliases) """
        first_record = self.env['mail.test.simple'].with_user(self.user_employee).create({'name': 'Replies to Record'})
        record_msg = first_record.message_post(
            subject='Discussion',
            reply_to_force_new=False,
            subtype_xmlid='mail.mt_comment',
        )
        self.assertEqual(record_msg.reply_to, formataddr(('%s %s' % (self.user_employee.company_id.name, first_record.name), '%s@%s' % ('catchall.test', 'test.com'))))
        mail_msg = first_record.message_post(
            subject='Replies to Record',
            reply_to='groups@test.com',
            reply_to_force_new=True,
            subtype_xmlid='mail.mt_comment',
        )
        self.assertEqual(mail_msg.reply_to, 'groups@test.com')

        # reply to mail but should be considered as a new mail for alias
        msgID = '<this.is.duplicate.test@iron.sky>'
        res_test = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, record_msg.reply_to, cc='',
            subject='Re: Replies to Record', extra='In-Reply-To: %s' % record_msg.message_id,
            msg_id=msgID, target_model='mail.test.simple')
        incoming_msg = self.env['mail.message'].search([('message_id', '=', msgID)])
        self.assertFalse(res_test)
        self.assertEqual(incoming_msg.model, 'mail.test.simple')
        self.assertEqual(incoming_msg.parent_id, first_record.message_ids[-1])
        self.assertTrue(incoming_msg.res_id == first_record.id)

        # reply to mail but should be considered as a new mail for alias
        msgID = '<this.is.for.testing@iron.sky>'
        res_test = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, mail_msg.reply_to, cc='',
            subject='Re: Replies to Record', extra='In-Reply-To: %s' % mail_msg.message_id,
            msg_id=msgID, target_model='mail.test.gateway')
        incoming_msg = self.env['mail.message'].search([('message_id', '=', msgID)])
        self.assertEqual(len(res_test), 1)
        self.assertEqual(res_test.name, 'Re: Replies to Record')
        self.assertEqual(incoming_msg.model, 'mail.test.gateway')
        self.assertFalse(incoming_msg.parent_id)
        self.assertTrue(incoming_msg.res_id == res_test.id)

    # --------------------------------------------------
    # Gateway / Record synchronization
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_gateway_values_base64_image(self):
        """New record with mail that contains base64 inline image."""
        target_model = "mail.test.field.type"
        alias = self.env["mail.alias"].create({
            "alias_name": "base64-lover",
            "alias_model_id": self.env["ir.model"]._get(target_model).id,
            "alias_defaults": "{}",
            "alias_contact": "everyone",
        })
        record = self.format_and_process(
            test_mail_data.MAIL_TEMPLATE_EXTRA_HTML, self.email_from,
            '%s@%s' % (alias.alias_name, self.alias_catchall),
            subject='base64 image to alias',
            target_model=target_model,
            extra_html='<img src="data:image/png;base64,iV/+OkI=">',
        )
        self.assertEqual(record.type, "first")
        self.assertEqual(len(record.message_ids[0].attachment_ids), 1)
        self.assertEqual(record.message_ids[0].attachment_ids[0].name, "image0")
        self.assertEqual(record.message_ids[0].attachment_ids[0].type, "binary")

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_gateway_values_base64_image_walias(self):
        """New record with mail that contains base64 inline image + default values
        coming from alias."""
        target_model = "mail.test.field.type"
        alias = self.env["mail.alias"].create({
            "alias_name": "base64-lover",
            "alias_model_id": self.env["ir.model"]._get(target_model).id,
            "alias_defaults": "{'type': 'second'}",
            "alias_contact": "everyone",
        })
        record = self.format_and_process(
            test_mail_data.MAIL_TEMPLATE_EXTRA_HTML, self.email_from,
            '%s@%s' % (alias.alias_name, self.alias_catchall),
            subject='base64 image to alias',
            target_model=target_model,
            extra_html='<img src="data:image/png;base64,iV/+OkI=">',
        )
        self.assertEqual(record.type, "second")
        self.assertEqual(len(record.message_ids[0].attachment_ids), 1)
        self.assertEqual(record.message_ids[0].attachment_ids[0].name, "image0")
        self.assertEqual(record.message_ids[0].attachment_ids[0].type, "binary")

    # --------------------------------------------------
    # Thread formation: mail gateway corner cases
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_extra_model_res_id(self):
        """ Incoming email with ref holding model / res_id but that does not match any message in the thread: must raise since OpenERP saas-3 """
        self.assertRaises(ValueError,
                          self.format_and_process, MAIL_TEMPLATE,
                          self.partner_1.email_formatted, 'noone@test.com', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.test.gateway@%s>' % (self.test_record.id, socket.gethostname()))

        # when 6.1 messages are present, compat mode is available
        # Odoo 10 update: compat mode has been removed and should not work anymore
        self.fake_email.write({'message_id': False})
        # Do: compat mode accepts partial-matching emails
        self.assertRaises(
            ValueError,
            self.format_and_process, MAIL_TEMPLATE,
            self.partner_1.email_formatted, 'noone@test.com>', subject='spam',
            extra='In-Reply-To: <12321321-openerp-%d-mail.test.gateway@%s>' % (self.test_record.id, socket.gethostname()))

        # Test created messages
        self.assertEqual(len(self.test_record.message_ids), 1)
        self.assertEqual(len(self.test_record.message_ids[0].child_ids), 0)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_duplicate(self):
        """ Duplicate emails (same message_id) are not processed """
        self.alias.write({'alias_force_thread_id': self.test_record.id,})

        # Post a base message
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Re: super cats', msg_id='<123?456.diff1@agrolait.com>')
        self.assertFalse(record)
        self.assertEqual(len(self.test_record.message_ids), 2)

        # Do: due to some issue, same email goes back into the mailgateway
        record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'groups@test.com', subject='Re: news',
            msg_id='<123?456.diff1@agrolait.com>', extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>\n')
        self.assertFalse(record)
        self.assertEqual(len(self.test_record.message_ids), 2)

        # Test: message_id is still unique
        no_of_msg = self.env['mail.message'].search_count([('message_id', 'ilike', '<123?456.diff1@agrolait.com>')])
        self.assertEqual(no_of_msg, 1,
                         'message_process: message with already existing message_id should not have been duplicated')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_crash_wrong_model(self):
        """ Incoming email with model that does not accepts incoming emails must raise """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, self.email_from, 'noone@test.com',
                          subject='spam', extra='', model='res.country')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_crash_no_data(self):
        """ Incoming email without model and without alias must raise """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, self.email_from, 'noone@test.com',
                          subject='spam', extra='')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_fallback(self):
        """ Incoming email with model that accepting incoming emails as fallback """
        record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'noone@test.com',
            subject='Spammy', extra='', model='mail.test.gateway')
        self.assertEqual(len(record), 1)
        self.assertEqual(record.name, 'Spammy')
        self.assertEqual(record._name, 'mail.test.gateway')


class TestMailThreadCC(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailThreadCC, cls).setUpClass()

        cls.email_from = 'Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>'
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'cc_record',
            'alias_user_id': False,
            'alias_model_id': cls.env['ir.model']._get('mail.test.cc').id,
            'alias_contact': 'everyone'})

        cls._init_mail_gateway()

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_new(self):
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'cc_record@test.com',
                                         cc='cc1@example.com, cc2@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['cc1@example.com', 'cc2@example.com'])

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_with_old(self):
        record = self.env['mail.test.cc'].create({'email_cc': 'cc1 <cc1@example.com>, cc2@example.com'})
        self.alias.write({'alias_force_thread_id': record.id})

        self.format_and_process(MAIL_TEMPLATE, self.email_from, 'cc_record@test.com',
                                cc='cc2 <cc2@example.com>, cc3@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['"cc1" <cc1@example.com>', 'cc2@example.com', 'cc3@example.com'], 'new cc should have been added on record (unique)')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_no_old(self):
        record = self.env['mail.test.cc'].create({})
        self.alias.write({'alias_force_thread_id': record.id})

        self.format_and_process(MAIL_TEMPLATE, self.email_from, 'cc_record@test.com',
                                cc='cc2 <cc2@example.com>, cc3@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['"cc2" <cc2@example.com>', 'cc3@example.com'], 'new cc should have been added on record (unique)')
