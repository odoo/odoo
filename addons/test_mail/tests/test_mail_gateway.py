# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import itertools
import socket

from datetime import datetime

from unittest.mock import DEFAULT
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.mail.models.mail_thread import MailThread
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.data import test_mail_data
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_mail.models.test_mail_models import MailTestGateway
from odoo.sql_db import Cursor
from odoo.tests import tagged
from odoo.tools import email_split_and_format, formataddr, mute_logger


@tagged('mail_gateway')
class TestEmailParsing(MailCommon):

    def test_message_parse_and_replace_binary_octetstream(self):
        """ Incoming email containing a wrong Content-Type as described in RFC2046/section-3 """
        received_mail = self.from_string(test_mail_data.MAIL_MULTIPART_BINARY_OCTET_STREAM)
        with self.assertLogs('odoo.addons.mail.models.mail_thread', level="WARNING") as capture:
            extracted_mail = self.env['mail.thread']._message_parse_extract_payload(received_mail, {})

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

        # test pure html
        html = self.format(test_mail_data.MAIL_TEMPLATE_HTML, email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>')
        res = self.env['mail.thread'].message_parse(self.from_string(html))
        self.assertIn('<p>Please call me as soon as possible this afternoon!</p>', res['body'])
        self.assertNotIn('<!DOCTYPE', res['body'])

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
        mail = self.format(test_mail_data.MAIL_EML_ATTACHMENT, email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>', to=f'generic@{self.alias_domain}')
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

        self.assertEqual(res['bounced_msg_ids'], [msg_id], "Message-Id is not extracted from Text/RFC822-Headers attachment")

    def test_message_parse_extract_bounce_rfc822_headers_qp(self):
        # Incoming bounce for unexisting Outlook address
        # bounce back sometimes with a Content-Type `text/rfc822-headers`
        # and Content-Type-Encoding `quoted-printable`
        partner = self.env['res.partner'].create({
            'name':'Mitchelle Admine',
            'email':'rdesfrdgtfdrfesd@outlook.com'
        })
        message = self.env['mail.message'].create({
            'message_id' : '<368396033905967.1673346177.695352554321289-openerp-11-sale.order@eupp00>'
        })
        incoming_bounce = self.format(
            test_mail_data.MAIL_BOUNCE_QP_RFC822_HEADERS,
            email_from='MAILER-DAEMON@mailserver.odoo.com (Mail Delivery System)',
            email_to='bounce@xxx.odoo.com',
            delivered_to='bounce@xxx.odoo.com'
        )

        msg_dict = {}
        msg = self.env['mail.thread']._message_parse_extract_bounce(self.from_string(incoming_bounce), msg_dict)
        self.assertEqual(msg['bounced_email'], partner.email, "The sender email should be correctly parsed")
        self.assertEqual(msg['bounced_partner'], partner, "A partner with this email should exist")
        self.assertEqual(msg['bounced_msg_ids'][0], message.message_id, "The sender message-id should correctly parsed")
        self.assertEqual(msg['bounced_message'], message, "An existing message with this message_id should exist")

    def test_message_parse_plaintext(self):
        """ Incoming email in plaintext should be stored as html """
        mail = self.format(test_mail_data.MAIL_TEMPLATE_PLAINTEXT, email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>', to=f'generic@{self.alias_domain}')
        res = self.env['mail.thread'].message_parse(self.from_string(mail))
        self.assertIn('<pre>\nPlease call me as soon as possible this afternoon!\n\n--\nSylvie\n</pre>', res['body'])

    def test_message_parse_xhtml(self):
        # Test that the parsing of XHTML mails does not fail
        self.env['mail.thread'].message_parse(self.from_string(test_mail_data.MAIL_XHTML))


@tagged('mail_gateway')
class TestMailgateway(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailgateway, cls).setUpClass()

        cls.mail_test_gateway_model = cls.env['ir.model']._get('mail.test.gateway')
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
            'alias_contact': 'everyone',
            'alias_model_id': cls.mail_test_gateway_model.id,
            'alias_name': 'groups',
            'alias_user_id': False,
        })

        # Set a first message on public group to test update and hierarchy
        cls.fake_email = cls._create_gateway_message(cls.test_record, '123456')

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
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Specific')

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
        origin_message_parse_extract_payload = MailThread._message_parse_extract_payload

        def _message_parse_extract_payload(this, *args, **kwargs):
            res = origin_message_parse_extract_payload(this, *args, **kwargs)
            self.assertTrue(isinstance(res['body'], str), 'Body from extracted payload should still be a string.')
            return res

        with patch.object(MailThread, '_message_parse_extract_payload', _message_parse_extract_payload):
            record = self.format_and_process(test_mail_data.MAIL_MULTIPART_IMAGE, self.email_from, f'groups@{self.alias_domain}')
        message = record.message_ids[0]
        for attachment in message.attachment_ids:
            self.assertIn(f'/web/image/{attachment.id}', message.body)
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['rosaçée.gif', 'verte!µ.gif', 'orangée.gif']))

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_followers(self):
        """ Incoming email: recognized author not archived and not odoobot:
        added as follower. Also test corner cases: archived. """
        partner_archived = self.env['res.partner'].create({
            'active': False,
            'email': 'archived.customer@text.example.com',
            'phone': '0032455112233',
            'name': 'Archived Customer',
            'type': 'contact',
        })

        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, f'groups@{self.alias_domain}')

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
                MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}',
                subject='Another Email')

        self.assertEqual(record2.message_ids[0].author_id, self.env['res.partner'])
        self.assertEqual(record2.message_ids[0].email_from, self.email_from)
        self.assertEqual(record2.message_follower_ids.partner_id, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')
        self.assertEqual(record2.message_partner_ids, self.env['res.partner'],
                         'message_process: unrecognized email -> no follower')

        # archived partner -> no follower
        with self.mock_mail_gateway():
            record3 = self.format_and_process(
                MAIL_TEMPLATE, partner_archived.email_formatted, f'groups@{self.alias_domain}',
                subject='Archived Partner')

        self.assertEqual(record3.message_ids[0].author_id, self.env['res.partner'])
        self.assertEqual(record3.message_ids[0].email_from, partner_archived.email_formatted)
        self.assertEqual(record3.message_follower_ids.partner_id, self.env['res.partner'],
                         'message_process: archived partner -> no follower')
        self.assertEqual(record3.message_partner_ids, self.env['res.partner'],
                         'message_process: archived partner -> no follower')

        # partner_root -> never again
        odoobot = self.env.ref('base.partner_root')
        odoobot.active = True
        odoobot.email = 'odoobot@example.com'
        with self.mock_mail_gateway():
            record4 = self.format_and_process(
                MAIL_TEMPLATE, odoobot.email_formatted, f'groups@{self.alias_domain}',
                subject='Odoobot Automatic Answer')

        self.assertEqual(record4.message_ids[0].author_id, odoobot)
        self.assertEqual(record4.message_ids[0].email_from, odoobot.email_formatted)
        self.assertEqual(record4.message_follower_ids.partner_id, self.env['res.partner'],
                         'message_process: odoobot -> no follower')
        self.assertEqual(record4.message_partner_ids, self.env['res.partner'],
                         'message_process: odoobot -> no follower')

    # --------------------------------------------------
    # Author recognition
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_email_from(self):
        """ Incoming email: not recognized author: email_from, no author_id, no followers """
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}')
        self.assertFalse(record.message_ids[0].author_id, 'message_process: unrecognized email -> no author_id')
        self.assertEqual(record.message_ids[0].email_from, self.email_from)
        self.assertEqual(len(record.message_partner_ids), 0,
                         'message_process: newly create group should not have any follower')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_author(self):
        """ Incoming email: recognized author: email_from, author_id, added as follower """
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, f'groups@{self.alias_domain}', subject='Test1')

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: recognized email -> author_id')
        self.assertEqual(record.message_ids[0].email_from, self.partner_1.email_formatted)
        self.assertNotSentEmail()  # No notification / bounce should be sent

        # Email recognized if partner has a formatted email
        self.partner_1.write({'email': f'"Valid Lelitre" <{self.partner_1.email}>'})
        record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email, f'groups@{self.alias_domain}', subject='Test2')

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: recognized email -> author_id')
        self.assertEqual(record.message_ids[0].email_from, self.partner_1.email)
        self.assertNotSentEmail()  # No notification / bounce should be sent

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_author_multiemail(self):
        """ Incoming email: recognized author: check multi/formatted email in field """
        test_email = 'valid.lelitre@agrolait.com'
        # Email not recognized if partner has a multi-email (source = formatted email)
        self.partner_1.write({'email': f'{test_email}, "Valid Lelitre" <another.email@test.example.com>'})
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, f'"Valid Lelitre" <{test_email}>', f'groups@{self.alias_domain}', subject='Test3')

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: found author based on first found email normalized, even with multi emails')
        self.assertEqual(record.message_ids[0].email_from, f'"Valid Lelitre" <{test_email}>')
        self.assertNotSentEmail()  # No notification / bounce should be sent

        # Email not recognized if partner has a multi-email (source = std email)
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, test_email, f'groups@{self.alias_domain}', subject='Test4')

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: found author based on first found email normalized, even with multi emails')
        self.assertEqual(record.message_ids[0].email_from, test_email)
        self.assertNotSentEmail()  # No notification / bounce should be sent

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.tests')
    def test_message_process_email_partner_find(self):
        """ Finding the partner based on email, based on partner / user / follower """
        self.alias.write({'alias_force_thread_id': self.test_record.id})
        from_1 = self.env['res.partner'].create({'name': 'Brice Denisse', 'email': 'from.test@example.com'})

        self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, f'groups@{self.alias_domain}')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_1)
        self.test_record.message_unsubscribe([from_1.id])

        from_2 = mail_new_test_user(self.env, login='B', groups='base.group_user', name='User Denisse', email='from.test@example.com')

        self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, f'groups@{self.alias_domain}')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_2.partner_id)
        self.test_record.message_unsubscribe([from_2.partner_id.id])

        from_3 = self.env['res.partner'].create({'name': 'FOllower Denisse', 'email': 'from.test@example.com'})
        self.test_record.message_subscribe([from_3.id])

        self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, f'groups@{self.alias_domain}')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_3)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_author_exclude_alias(self):
        """ Do not set alias as author to avoid including aliases in discussions """
        from_1 = self.env['res.partner'].create({
            'name': 'Brice Denisse',
            'email': f'from.test@{self.alias_domain}',
        })
        self.env['mail.alias'].create({
            'alias_name': 'from.test',
            'alias_model_id': self.env['ir.model']._get('mail.test.gateway').id
        })

        record = self.format_and_process(MAIL_TEMPLATE, from_1.email_formatted, f'groups@{self.alias_domain}')
        self.assertFalse(record.message_ids[0].author_id)
        self.assertEqual(record.message_ids[0].email_from, from_1.email_formatted)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_alias_owner_author_notify(self):
        """ Make sure users are notified when a reply is sent to an alias address.
        Alias owner should impact the message creator, but not notifications. """
        test_record = self.env['mail.test.ticket'].create({})
        author_partner = self.env['res.partner'].create({
            'name': 'Author',
            'email': f'author-partner@{self.alias_domain}',
        })
        message = self.env['mail.message'].create({
            'body': '<p>test</p>',
            'email_from': f'author-partner@{self.alias_domain}',  # email sent by author who also has an alias with their email
            'message_type': 'email',
            'model': test_record._name,
            'res_id': test_record.id,
        })
        self.env['mail.alias'].create({
            'alias_model_id': self.env['ir.model']._get_id(test_record._name),
            'alias_name': 'author-partner',
            'alias_user_id': self.user_employee.id
        })

        test_record.message_subscribe((author_partner | self.user_employee.partner_id).ids)

        messages = test_record.message_ids

        self.assertFalse(self.user_root.active, 'notification logic relies on odoobot being archived')

        test_users = [self.user_employee, self.user_root]
        email_tos = [f'author-partner@{self.alias_domain}', f'some_non_aliased_email@{self.alias_domain}']
        for email_to, test_user in itertools.product(email_tos, test_users):
            with self.subTest(test_user=test_user, email_to=email_to):
                with self.mock_mail_gateway(), self.mock_mail_app():
                    self.format_and_process(
                        MAIL_TEMPLATE, self.email_from, email_to,
                        subject=message.message_id, extra=f'In-Reply-To:\r\n\t{message.message_id}\n',
                        model=None, with_user=test_user)
                new_messages = test_record.message_ids - messages

                self.assertEqual(len(new_messages), 1)
                self.assertEqual(new_messages.create_uid, self.user_root,
                                 'Odoobot should be creating the message')

                # Make sure the alias owner is notified if they are a follower
                self.assertNotified(new_messages, [{
                    'partner': self.user_employee.partner_id,
                    'is_read': False,
                    'type': 'inbox',
                }])
                # never notify the author of the incoming message
                with self.assertRaises(Exception):
                    self.assertNotified(new_messages, [{'partner': author_partner}])

            messages = test_record.message_ids

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
            record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Should Bounce')
        self.assertFalse(record, 'message_process: should have bounced')
        self.assertSentEmail(f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>', ['whatever-2a840@postmaster.twitter.com'], body_content='<p>What Is Dead May Never Die</p>')

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
                record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Should Bounce')
            self.assertFalse(record, 'message_process: should have bounced')
            # Check if default (hardcoded) value is in the mail content
            self.assertSentEmail(
                f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
                ['whatever-2a840@postmaster.twitter.com'],
                body_content=f'<p>Dear Sender,<br /><br />The message below could not be accepted by the address {self.alias.display_name.lower()}',
            )

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_message_process_alias_config_bounced_to(self):
        """ Check bounce message contains the bouncing alias, not a generic "to" """
        self.alias.write({'alias_contact': 'partners'})
        bounce_message_with_alias = f'<p>Dear Sender,<br /><br />The message below could not be accepted by the address {self.alias.display_name.lower()}'

        # Bounce is To
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}',
                cc='other@gmail.com', subject='Should Bounce')
        self.assertIn(bounce_message_with_alias, self._mails[0].get('body'))

        # Bounce is CC
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE, self.email_from, 'other@gmail.com',
                cc=f'groups@{self.alias_domain}', subject='Should Bounce')
        self.assertIn(bounce_message_with_alias, self._mails[0].get('body'))

        # Bounce is part of To
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE, self.email_from, f'other@gmail.com, groups@{self.alias_domain}',
                subject='Should Bounce')
        self.assertIn(bounce_message_with_alias, self._mails[0].get('body'))

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail.models.mail_mail', 'odoo.models', 'odoo.sql_db')
    def test_message_process_alias_config_invalid_defaults(self):
        """Sending a mail to a misconfigured alias must change its status to invalid + notify sender and responsible."""
        test_model_track = self.env['ir.model']._get('mail.test.track')
        container_custom = self.env['mail.test.container'].create({})
        alias_valid = self.env['mail.alias'].create({
            'alias_name': 'valid',
            'alias_user_id': self.user_employee.id,
            'alias_model_id': test_model_track.id,
            'alias_contact': 'everyone',
            'alias_defaults': f"{{'container_id': {container_custom.id}}}",
        })

        # Test that it works when the reference to container_id in alias default is not dangling.
        self.assertEqual(alias_valid.alias_status, 'not_tested')
        with self.mock_mail_gateway(), patch('odoo.addons.mail.models.mail_alias.Alias._set_alias_invalid',
                                             autospec=True) as _set_alias_invalid_mock:
            record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'valid@{self.alias_domain}', subject='Valid',
                                             target_model=test_model_track.model)
        _set_alias_invalid_mock.assert_not_called()
        self.assertNotSentEmail()
        self.assertEqual(record.container_id, container_custom)
        self.assertEqual(alias_valid.alias_status, 'valid')

        # Test with a dangling reference that must trigger bounce emails and set the alias status to invalid.
        container_custom.unlink()
        with self.assertRaises(Exception), patch('odoo.addons.mail.models.mail_alias.Alias._set_alias_invalid',
                                                 autospec=True) as _set_alias_invalid_mock:
            self.format_and_process(MAIL_TEMPLATE, self.email_from, f'valid@{self.alias_domain}', subject='Invalid',
                                    target_model=test_model_track.model)

        # method executed in another transaction, so we cannot test its result directly but just below
        _set_alias_invalid_mock.assert_called_once()

        # call notify_alias_invalid on the test transaction to validate its effect
        alias, message, message_dict = _set_alias_invalid_mock.call_args.args
        with self.mock_mail_gateway():
            alias = self.env['mail.alias'].browse(alias.id)  # load alias in test transaction
            alias._set_alias_invalid(message, message_dict)

        self.assertEqual(alias_valid.alias_status, 'invalid')
        self.assertSentEmail(f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
                             [alias_valid.alias_user_id.partner_id.email_formatted],
                             subject='Re: Invalid')
        # Not sent to self.email_from because a return path is present in MAIL_TEMPLATE
        self.assertSentEmail(f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
                             ['whatever-2a840@postmaster.twitter.com'],
                             subject='Re: Invalid',
                             body=alias_valid._get_alias_invalid_body(message_dict))

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    @patch('odoo.addons.mail.models.mail_alias.Alias._set_alias_invalid')
    def test_message_process_alias_defaults(self, _set_alias_invalid):
        """ Test alias defaults and inner values """
        self.alias.write({
            'alias_user_id': self.user_employee.id,
            'alias_defaults': "{'custom_field': 'defaults_custom'}"
        })

        self.assertEqual(self.alias.alias_status, 'not_tested')

        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Specific')

        _set_alias_invalid.assert_not_called()
        self.assertEqual(self.alias.alias_status, 'valid')
        self.assertEqual(len(record), 1)
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id)
        self.assertEqual(record.name, 'Specific')
        self.assertEqual(record.custom_field, 'defaults_custom')

        self.alias.write({'alias_defaults': '""'})
        self.assertEqual(self.alias.alias_status, 'not_tested', 'Updating alias_defaults must reset status')
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Specific2')

        _set_alias_invalid.assert_not_called()
        self.assertEqual(len(record), 1)
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id)
        self.assertEqual(record.name, 'Specific2')
        self.assertFalse(record.custom_field)

        self.assertEqual(self.alias.alias_status, 'valid')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_user_id(self):
        """ Test alias ownership """
        self.alias.write({'alias_user_id': self.user_employee.id})

        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}')
        self.assertEqual(len(record), 1)
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_everyone(self):
        """ Incoming email: everyone: new record + message_new """
        self.alias.write({'alias_contact': 'everyone'})

        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Specific')
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.message_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_partners_bounce(self):
        """ Incoming email from an unknown partner on a Partners only alias -> bounce + test bounce email """
        self.alias.write({'alias_contact': 'partners'})

        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Should Bounce')
        self.assertFalse(record)
        self.assertSentEmail(f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>', ['whatever-2a840@postmaster.twitter.com'], subject='Re: Should Bounce')

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
            record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Should Bounce')
        self.assertFalse(record, 'message_process: should have bounced')
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ['whatever-2a840@postmaster.twitter.com'],
            subject='Re: Should Bounce'
        )

        # Test: partner on followers alias -> bounce
        self._init_mail_mock()
        with self.mock_mail_gateway():
            record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, f'groups@{self.alias_domain}', subject='Should Bounce')
        self.assertFalse(record, 'message_process: should have bounced')
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ['whatever-2a840@postmaster.twitter.com'],
            subject='Re: Should Bounce'
        )

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_partner(self):
        """ Incoming email from a known partner on a Partners alias -> ok (+ test on alias.user_id) """
        self.alias.write({'alias_contact': 'partners'})
        record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, f'groups@{self.alias_domain}')

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
        record = self.format_and_process(MAIL_TEMPLATE, self.partner_1.email_formatted, f'groups@{self.alias_domain}')

        # Test: one group created by Raoul (or Sylvie maybe, if we implement it)
        self.assertEqual(len(record), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.tests')
    def test_message_process_alias_followers_multiemail(self):
        """ Incoming email from a parent document follower on a Followers only
        alias depends on email_from / partner recognition, to be tested when
        dealing with multi emails / formatted emails. """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.env['ir.model']._get('mail.test.gateway').id,
            'alias_parent_thread_id': self.test_record.id,
        })
        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        email_from = formataddr(("Another Name", self.partner_1.email_normalized))

        for partner_email, passed in [
            (formataddr((self.partner_1.name, self.partner_1.email_normalized)), True),
            (f'{self.partner_1.email_normalized}, "Multi Email" <multi.email@test.example.com>', True),
            (f'"Multi Email" <multi.email@test.example.com>, {self.partner_1.email_normalized}', False),
        ]:
            with self.subTest(partner_email=partner_email):
                self.partner_1.write({'email': partner_email})
                record = self.format_and_process(
                    MAIL_TEMPLATE, email_from, f'groups@{self.alias_domain}',
                    subject=f'Test for {partner_email}')

                if passed:
                    self.assertEqual(len(record), 1)
                    self.assertEqual(record.email_from, email_from)
                    self.assertEqual(record.message_partner_ids, self.partner_1)
                # multi emails not recognized (no normalized email, recognition)
                else:
                    self.assertEqual(len(record), 0,
                                     'Alias check (FIXME): multi-emails bad support for recognition')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_update(self):
        """ Incoming email update discussion + notification email """
        self.alias.write({'alias_force_thread_id': self.test_record.id})

        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}',
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
            """ If employee is test employee, consider they have no access on document """
            recordset = args[0]
            if recordset.env.uid == self.user_employee.id and not recordset.env.su:
                if kwargs.get('raise_exception', True):
                    raise exceptions.AccessError('Hop hop hop Ernest, please step back.')
                return False
            return DEFAULT

        with patch.object(MailTestGateway, 'check_access_rights', autospec=True, side_effect=_employee_crash):
            record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, f'groups@{self.alias_domain}', subject='NoEmployeeAllowed')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'NoEmployeeAllowed')
        self.assertEqual(record.message_ids[0].create_uid, self.user_root, 'Message should be created by caller of message_process.')
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_create_uid_email(self):
        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, f'groups@{self.alias_domain}', subject='Email Found')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'Email Found')
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

        record = self.format_and_process(
            MAIL_TEMPLATE, f'Another name <{self.user_employee.email}>',
            f'groups@{self.alias_domain}',
            subject='Email OtherName')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'Email OtherName')
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_normalized, f'groups@{self.alias_domain}', subject='Email SimpleEmail')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'Email SimpleEmail')
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink')
    def test_message_process_create_uid_email_follower(self):
        self.alias.write({
            'alias_parent_model_id': self.mail_test_gateway_model.id,
            'alias_parent_thread_id': self.test_record.id,
        })
        follower_user = mail_new_test_user(self.env, login='better', groups='base.group_user', name='Ernest Follower', email=self.user_employee.email)
        self.test_record.message_subscribe(follower_user.partner_id.ids)

        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, f'groups@{self.alias_domain}', subject='FollowerWinner')
        self.assertEqual(record.create_uid, follower_user)
        self.assertEqual(record.message_ids[0].subject, 'FollowerWinner')
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, follower_user.partner_id)

        # name order win
        self.test_record.message_unsubscribe(follower_user.partner_id.ids)
        self.test_record.flush_recordset()
        record = self.format_and_process(MAIL_TEMPLATE, self.user_employee.email_formatted, f'groups@{self.alias_domain}', subject='FirstFoundWinner')
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, 'FirstFoundWinner')
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
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
            f'{new_alias_2.display_name}, {self.alias.display_name}',
            subject='Test Subject',
            extra=f'In-Reply-To:\r\n\t{self.fake_email.message_id}\n',
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
            f'{self.alias.display_name}, {new_alias_2.display_name}',
            subject='Test Subject',
            extra=f'In-Reply-To:\r\n\t{self.fake_email.message_id}\n',
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
            f'{new_alias_2.display_name}, {self.alias.display_name}',
            subject='Test Subject',
            extra=f'In-Reply-To:\r\n\t{self.fake_email.message_id}\n',
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
            f'{self.alias.display_name}, {new_alias_2.display_name}',
            subject='Test Subject',
            target_model=new_alias_2.alias_model_id.model
        )
        # New record in both mail.test (new_alias_2) and mail.test.simple (self.alias)
        self.assertEqual(len(new_rec), 1, 'message_process: a new mail.test should have been created')
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        new_simple = self.env['mail.test.gateway'].search([('name', '=', 'Test Subject')])
        self.assertEqual(len(new_simple), 1, 'message_process: a new mail.test should have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_alias_with_allowed_domains(self):
        """ Incoming email: check that if domains are set in the optional system
        parameter `mail.catchall.domain.allowed` only incoming emails from these
        domains will generate records."""
        MailTestGatewayModel = self.env['mail.test.gateway']
        MailTestContainerModel = self.env['mail.test.container']

        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env['mail.alias'].create({
            'alias_contact': 'everyone',
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_name': 'test',
            'alias_user_id': False,
        })

        allowed_domain = 'hello.com'
        for (alias_right_part, allowed_domain), (gateway_created, container_created) in zip(
            [
                # Test with 'mail.catchall.domain.allowed' not set in system parameters
                # and with a domain not allowed
                ('bonjour.com', ""),
                # Test with 'mail.catchall.domain.allowed' set in system parameters
                # and with a domain not allowed
                ('bonjour.com', allowed_domain),
                # Test with 'mail.catchall.domain.allowed' set in system parameters
                # and with a domain allowed
                (allowed_domain, allowed_domain),
            ], [
                (True, True),
                (True, False),
                (True, True),
            ]
        ):
            with self.subTest(alias_right_part=alias_right_part, allowed_domain=allowed_domain):
                self.env['ir.config_parameter'].set_param('mail.catchall.domain.allowed', allowed_domain)

                subject = f'Test wigh {alias_right_part}-{allowed_domain}'
                email_to = f'{self.alias.alias_name}@{self.alias_domain}, {new_alias_2.alias_name}@{alias_right_part}'

                self.format_and_process(
                    MAIL_TEMPLATE, self.partner_1.email_formatted, email_to,
                    subject=subject,
                    target_model=self.alias.alias_model_id.model
                )

                res_alias_1 = MailTestGatewayModel.search([('name', '=', subject)])
                res_alias_2 = MailTestContainerModel.search([('name', '=', subject)])
                self.assertEqual(bool(res_alias_1), gateway_created)
                self.assertEqual(bool(res_alias_2), container_created)

    # --------------------------------------------------
    # Email Management
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_bounce(self):
        """Incoming email: bounce  using bounce alias: no record creation """
        with self.mock_mail_gateway():
            new_recs = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted,
                f'{self.alias_bounce}@{self.alias_domain}',
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
                f'{self.alias.alias_name}@{self.alias_domain}, {self.alias_bounce}@{self.alias_domain}',
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
                f'"My Super Catchall" <{self.alias_catchall}@{self.alias_domain}',
                subject='Should Bounce')
        self.assertFalse(record)
        self.assertSentEmail(
            self.mailer_daemon_email,
            ['whatever-2a840@postmaster.twitter.com'],
            subject='Re: Should Bounce'
        )

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_route_write_to_catchall_other_recipients_first(self):
        """ Writing directly to catchall and a valid alias should take alias """
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE, self.partner_1.email_formatted,
                f'{self.alias_catchall}@{self.alias_domain}, {self.alias.alias_name}@{self.alias_domain}',
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
                f'{self.alias.alias_name}@{self.alias_domain}, {self.alias_catchall}@{self.alias_domain}',
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

        bounce_email_to = f'{self.alias_bounce}@{self.alias_domain}'
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

        record = self.format_and_process(MAIL_TEMPLATE, 'MAILER-DAEMON@example.com', f'groups@{self.alias_domain}', subject='Undelivered Mail Returned to Sender')
        self.assertFalse(record)
        # No information found in bounce email -> not possible to do anything except avoiding email
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_missing_final_recipient(self):
        """The Final-Recipient header is missing, the partner must be found thanks to the original mail message."""
        email = test_mail_data.MAIL_BOUNCE.replace('Final-Recipient', 'XX')
        email = email.replace('Original-Recipient', 'XX')

        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        # no notification to find, won't be able to find the correct recipient
        extra = self.fake_email.message_id
        record = self.format_and_process(email, self.partner_1.email_formatted, f'{self.alias_bounce}@{self.alias_domain}', subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        # the partner will be found in the <mail.notification> res_partner_id
        extra = self.fake_email.message_id
        self.env['mail.notification'].create({
            "res_partner_id": self.partner_1.id,
            "mail_message_id": self.fake_email.id,
        })
        record = self.format_and_process(email, self.partner_1.email_formatted, f'{self.alias_bounce}@{self.alias_domain}', subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 1)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_multipart_alias(self):
        """ Multipart/report bounce correctly make related partner bounce """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounce_email_to = f'{self.alias_bounce}@{self.alias_domain}'
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

        notification = self.env['mail.notification'].create({
            'mail_message_id': self.fake_email.id,
            'res_partner_id': self.partner_1.id,
        })

        bounce_email_to = f'{self.alias_bounce}@{self.alias_domain}'
        extra = self.fake_email.message_id
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, self.partner_1.email_formatted, bounce_email_to, subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 1)
        self.assertIn(
            'This is the mail system at host mail2.test.ironsky.',
            notification.failure_reason,
            msg='Should store the bounce email body on the notification')
        self.assertEqual(notification.failure_type, 'mail_bounce')
        self.assertEqual(notification.notification_status, 'bounce')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_bounce_multipart_alias_whatever_from(self):
        """ Multipart/report bounce correctly make related record found in bounce email bounce """
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounce_email_to = f'{self.alias_bounce}@{self.alias_domain}'
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
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, 'Whatever <what@ever.com>', f'groups@{self.alias_domain}', subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 1)

        # The local part of the FROM is not "MAILER-DAEMON", and the Content type is slightly
        # different. Thanks to the report type, it still should be detected as a bounce email.
        email = test_mail_data.MAIL_BOUNCE.replace('multipart/report;', 'multipart/report:')
        email = email.replace('MAILER-DAEMON@mail2.test.ironsky', 'email@mail2.test.ironsky')
        self.assertIn('report-type=delivery-status', email)
        extra = self.fake_email.message_id
        record = self.format_and_process(email, 'Whatever <what@ever.com>', f'groups@{self.alias_domain}', subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 2)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink')
    def test_message_process_bounce_records_channel(self):
        """ Test blacklist allow to multi-bounce and auto update of discuss.channel """
        other_record = self.env['mail.test.gateway'].create({
            'email_from': f'Another name <{self.partner_1.email}>'
        })
        yet_other_record = self.env['mail.test.gateway'].create({
            'email_from': f'Yet Another name <{self.partner_1.email.upper()}>'
        })
        test_channel = self.env['discuss.channel'].create({
            'name': 'Test',
            'channel_partner_ids': [(4, self.partner_1.id)],
        })
        self.fake_email.write({
            'model': 'discuss.channel',
            'res_id': test_channel.id,
        })
        self.assertIn(self.partner_1, test_channel.channel_partner_ids)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(other_record.message_bounce, 0)
        self.assertEqual(yet_other_record.message_bounce, 0)

        extra = self.fake_email.message_id
        for i in range(10):
            record = self.format_and_process(
                test_mail_data.MAIL_BOUNCE, f'A third name <{self.partner_1.email}>',
                f'groups@{self.alias_domain}',
                subject='Undelivered Mail Returned to Sender',
                extra=extra)
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
        record = self.format_and_process(test_mail_data.MAIL_BOUNCE, self.partner_1.email_formatted, f'groups@{self.alias_domain}', subject='Undelivered Mail Returned to Sender', extra=extra)
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 0)

    # --------------------------------------------------
    # Thread formation
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_message_process_external_notification_reply(self):
        """Ensure responses bot messages are discussions."""
        bot_notification_message = self._create_gateway_message(
            self.test_record,
            'bot_notif_message',
            author_id=self.env.ref('base.partner_root').id,
            message_type='auto_comment',
            is_internal=True,
            subtype_id=self.env.ref('mail.mt_note').id,
        )

        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, '',
            subject='Reply to bot notif',
            extra=f'References: {bot_notification_message.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertFalse(new_msg.is_internal, "Responses to messages sent by odoobot should always be public.")
        self.assertEqual(new_msg.parent_id, bot_notification_message)
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'))

        # Also check the regular case
        some_notification_message = self._create_gateway_message(
            self.test_record,
            'some_notif_message',
            message_type='notification',
            is_internal=True,
            subtype_id=self.env.ref('mail.mt_note').id,
        )

        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, '',
            subject='Reply to some notif',
            extra=f'References: {some_notification_message.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertTrue(new_msg.is_internal, "Responses to messages sent by anyone but odoobot should keep"
                        "the 'is_internal' value of the parent.")
        self.assertEqual(new_msg.parent_id, some_notification_message)
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_note'))

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_in_reply_to(self):
        """ Incoming email using in-rely-to should go into the right destination even with a wrong destination """
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, 'valid.other@gmail.com', f'erroneous@{self.alias_domain}',
            subject='Re: news', extra=f'In-Reply-To:\r\n\t{self.fake_email.message_id}\n')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references(self):
        """ Incoming email using references should go into the right destination even with a wrong destination """
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'erroneous@{self.alias_domain}',
            extra=f'References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail', 'odoo.tests')
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
            MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}',
            subject='Reply to reply1',
            extra=f'References: {reply1.message_id} {self.fake_email.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: reply to a comment should be a comment')

        # ordering should not impact
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}',
            subject='Reply to reply1 (order issue)',
            extra=f'References: {self.fake_email.message_id} {reply1.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: reply to a comment should be a comment')

        # history with last one being a note
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}',
            subject='Reply to reply1_1',
            extra=f'References: {reply1_1.message_id} {self.fake_email.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_note'), 'Mail: reply to a note should be a note')

        # messed up history (two child branches): gateway initial parent is newest one
        # (then may change with flattening when posting on record)
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}',
            subject='Reply to reply2_1 (with noise)',
            extra=f'References: {reply1_1.message_id} {reply2_1.message_id}'
        )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, self.fake_email, 'Mail: flattening attach to original message')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment (before flattening)')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_message_process_references_multi_parent_notflat(self):
        """ Incoming email with multiple references with ``_mail_flat_thread``
        being False (mail.group/discuss.channel behavior like). """
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
            MAIL_TEMPLATE, self.email_from, f'test.gateway@{self.alias_domain}',
            subject='Reply to reply1',
            extra=f'References: {reply1.message_id}'
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, first_msg, 'Mail: pseudo no flattening: getting up one level (reply1 parent)')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment')

        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'test.gateway@{self.alias_domain}',
            subject='Reply to reply1_1 (with noise)',
            extra=f'References: {reply1_1.message_id} {reply1.message_id} {reply1.message_id}'
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, reply1, 'Mail: pseudo no flattening: getting up one level (reply1_1 parent)')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_note'), 'Mail: reply to a note should be a note')

        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'test.gateway@{self.alias_domain}',
            subject='Reply to reply2_1 (with noise)',
            extra=f'References: {reply2_1.message_id} {reply1_1.message_id}'
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(new_msg.parent_id, reply2, 'Mail: pseudo no flattening: getting up one level (reply2_1 parent')
        self.assertEqual(new_msg.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment')

        # no references: new discussion thread started
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'test.gateway@{self.alias_domain}',
            subject='New thread',
            extra='References:'
        )
        new_thread = test_record.message_ids[0]
        self.assertFalse(new_thread.parent_id, 'Mail: pseudo no flattening: no parent means new thread')
        self.assertEqual(new_thread.subject, 'New thread')
        self.assertEqual(new_thread.subtype_id, self.env.ref('mail.mt_comment'), 'Mail: parent should be a comment')

        # mixed up references: newer message wins
        self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'test.gateway@{self.alias_domain}',
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
            MAIL_TEMPLATE, self.email_from, f'erroneous@{self.alias_domain}',
            extra=f'References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}')

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
            MAIL_TEMPLATE, self.email_from, f'erroneous@{self.alias_domain}',
            extra=f'References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {buggy_message_id}')

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
            MAIL_TEMPLATE, self.email_from, f'test.alias@{self.alias_domain}',
            subject='My Dear Forward',
            extra=f'References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}',
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
            MAIL_TEMPLATE, self.email_from, f'test.alias@{self.alias_domain}',
            subject='My Dear Forward',
            extra=f'References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}',
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
            MAIL_TEMPLATE, self.email_from,
            f'{self.alias_catchall}@{self.alias_domain}',
            cc=f'test.alias@{self.alias_domain}',
            subject='My Dear Forward',
            extra=f'References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}',
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
        self.assertEqual(
            record_msg.reply_to,
            formataddr((f'{self.user_employee.company_id.name} {first_record.name}',
                        f'{self.alias_catchall}@{self.alias_domain}'))
        )
        mail_msg = first_record.message_post(
            subject='Replies to Record',
            reply_to=f'groups@{self.alias_domain}',
            reply_to_force_new=True,
            subtype_xmlid='mail.mt_comment',
        )
        self.assertEqual(mail_msg.reply_to, f'groups@{self.alias_domain}')

        # reply to mail but should be considered as a new mail for alias
        msgID = '<this.is.duplicate.test@iron.sky>'
        res_test = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, record_msg.reply_to, cc='',
            subject='Re: Replies to Record', extra=f'In-Reply-To: {record_msg.message_id}',
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
            subject='Re: Replies to Record', extra=f'In-Reply-To: {mail_msg.message_id}',
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
            f'{alias.alias_name}@{self.alias_domain}',
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
            f'{alias.alias_name}@{self.alias_domain}',
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
                          self.partner_1.email_formatted, f'noone@{self.alias_domain}', subject='spam',
                          extra=f'In-Reply-To: <12321321-openerp-{self.test_record.id}-{self.test_record._name}@{socket.gethostname()}>')

        # when 6.1 messages are present, compat mode is available
        # Odoo 10 update: compat mode has been removed and should not work anymore
        self.fake_email.write({'message_id': False})
        # Do: compat mode accepts partial-matching emails
        self.assertRaises(
            ValueError,
            self.format_and_process, MAIL_TEMPLATE,
            self.partner_1.email_formatted, f'noone@{self.alias_domain}>', subject='spam',
            extra=f'In-Reply-To: <12321321-openerp-{self.test_record.id}-mail.test.gateway@{socket.gethostname()}>')

        # Test created messages
        self.assertEqual(len(self.test_record.message_ids), 1)
        self.assertEqual(len(self.test_record.message_ids[0].child_ids), 0)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_duplicate(self):
        """ Duplicate emails (same message_id) are not processed """
        self.alias.write({'alias_force_thread_id': self.test_record.id,})

        # Post a base message
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Re: super cats', msg_id='<123.456.diff1@agrolait.com>')
        self.assertFalse(record)
        self.assertEqual(len(self.test_record.message_ids), 2)

        # Do: due to some issue, same email goes back into the mailgateway
        record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'groups@{self.alias_domain}', subject='Re: news',
            msg_id='<123.456.diff1@agrolait.com>', extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>\n')
        self.assertFalse(record)
        self.assertEqual(len(self.test_record.message_ids), 2)

        # Test: message_id is still unique
        no_of_msg = self.env['mail.message'].search_count([('message_id', 'ilike', '<123.456.diff1@agrolait.com>')])
        self.assertEqual(no_of_msg, 1,
                         'message_process: message with already existing message_id should not have been duplicated')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_crash_wrong_model(self):
        """ Incoming email with model that does not accepts incoming emails must raise """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, self.email_from, f'noone@{self.alias_domain}',
                          subject='spam', extra='', model='res.country')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_crash_no_data(self):
        """ Incoming email without model and without alias must raise """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, self.email_from, f'noone@{self.alias_domain}',
                          subject='spam', extra='')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_fallback(self):
        """ Incoming email with model that accepting incoming emails as fallback """
        record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'noone@{self.alias_domain}',
            subject='Spammy', extra='', model='mail.test.gateway')
        self.assertEqual(len(record), 1)
        self.assertEqual(record.name, 'Spammy')
        self.assertEqual(record._name, 'mail.test.gateway')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_file_encoding(self):
        """ Incoming email with file encoding """
        file_content = 'Hello World'
        for encoding in ['', 'UTF-8', 'UTF-16LE', 'UTF-32BE']:
            file_content_b64 = base64.b64encode(file_content.encode(encoding or 'utf-8')).decode()
            record = self.format_and_process(test_mail_data.MAIL_FILE_ENCODING,
                self.email_from, f'groups@{self.alias_domain}',
                subject=f'Test Charset {encoding or "Unset"}',
                charset=f'; charset="{encoding}"' if encoding else '',
                content=file_content_b64
            )
            attachment = record.message_ids.attachment_ids
            self.assertEqual(file_content, attachment.raw.decode(encoding or 'utf-8'))
            if encoding not in ['', 'UTF-8']:
                self.assertNotEqual(file_content, attachment.raw.decode('utf-8'))

    # --------------------------------------------------
    # Emails loop detection
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail.models.mail_mail')
    @patch.object(Cursor, 'now', lambda *args, **kwargs: datetime(2022, 1, 1, 10, 0, 0))
    def test_routing_loop_alias(self):
        """Test the limit on the number of record we can create by alias."""
        self.env['ir.config_parameter'].sudo().set_param('mail.gateway.loop.minutes', 30)
        self.env['ir.config_parameter'].sudo().set_param('mail.gateway.loop.threshold', 5)

        self.env['mail.gateway.allowed'].create([
            {'email': 'Bob@EXAMPLE.com'},
            {'email': '"Alice From Example" <alice@EXAMPLE.com>'},
            {'email': '"Eve From Example" <eve@EXAMPLE.com>'},
        ])

        alias = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_contact': 'everyone',
        })

        # Send an email 2 hours ago, should not have an impact on more recent emails
        with patch.object(Cursor, 'now', lambda *args, **kwargs: datetime(2022, 1, 1, 8, 0, 0)):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f'{self.alias.alias_name}@{self.alias_domain}',
                subject='Test alias loop old',
                target_model=alias.alias_model_id.model,
            )

        for i in range(5):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f'{self.alias.alias_name}@{self.alias_domain}',
                subject=f'Test alias loop {i}',
                target_model=alias.alias_model_id.model,
            )

        records = self.env['mail.test.gateway'].search([('name', 'ilike', 'Test alias loop %')])
        self.assertEqual(len(records), 6, 'Should have created 6 <mail.test.gateway>')
        self.assertEqual(set(records.mapped('email_from')), set([self.email_from]),
            msg='Should have automatically filled the email field')

        self.assertEqual(set(records.mapped('email_from')), {self.email_from})

        for email_from in (self.email_from, self.email_from.upper()):
            with self.mock_mail_gateway():
                self.format_and_process(
                    MAIL_TEMPLATE,
                    email_from,
                    f'{self.alias.alias_name}@{self.alias_domain}',
                    subject='Test alias loop X',
                    target_model=alias.alias_model_id.model,
                    return_path=email_from,
                )

            new_record = self.env['mail.test.gateway'].search([('name', '=', 'Test alias loop X')])
            self.assertFalse(
                new_record,
                msg='The loop should have been detected and the record should not have been created')

            self.assertSentEmail(f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>', [email_from])
            self.assertIn('-loop-detection-bounce-email@', self._mails[0]['references'],
                msg='The "bounce email" tag must be in the reference')

        # The reply to the bounce email must be ignored
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f'{self.alias.alias_name}@{self.alias_domain}',
                subject='Test alias loop X',
                target_model=alias.alias_model_id.model,
                return_path=self.email_from,
                extra='References: <test-1337-loop-detection-bounce-email@odoo.com>',
            )

        self.assertNotSentEmail()

        # Email address in the whitelist should not have the restriction
        for i in range(10):
            self.format_and_process(
                MAIL_TEMPLATE,
                'alice@example.com',
                f'{self.alias.alias_name}@{self.alias_domain}',
                subject=f'Whitelist test alias loop {i}',
                target_model=alias.alias_model_id.model,
            )

        records = self.env['mail.test.gateway'].search([('name', 'ilike', 'Whitelist test alias loop %')])
        self.assertEqual(len(records), 10, msg='Email whitelisted should not have the restriction')

    # --------------------------------------------------
    # Corner cases / Bugs during message process
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_file_encoding_ascii(self):
        """ Incoming email containing an xml attachment with unknown characters (�) but an ASCII charset should not
        raise an Exception. UTF-8 is used as a safe fallback.
        """
        record = self.format_and_process(test_mail_data.MAIL_MULTIPART_INVALID_ENCODING, self.email_from, f'groups@{self.alias_domain}')

        self.assertEqual(record.message_ids.attachment_ids.name, 'bis3_with_error_encoding_address.xml')
        # NB: the xml received by email contains b"Chauss\xef\xbf\xbd\xef\xbf\xbde" with "\xef\xbf\xbd" being the
        # replacement character � in UTF-8.
        # When calling `_message_parse_extract_payload`, `part.get_content()` will be called on the attachment part of
        # the email, triggering the decoding of the base64 attachment, so b"Chauss\xef\xbf\xbd\xef\xbf\xbde" is
        # first retrieved. Then, `get_text_content` in `email` tries to decode this using the charset of the email
        # part, i.e: `content.decode('us-ascii', errors='replace')`. So the errors are replaced using the Unicode
        # replacement marker and the string "Chauss������e" is used to create the attachment.
        # This explains the multiple "�" in the attachment.
        self.assertIn("Chauss������e de Bruxelles", record.message_ids.attachment_ids.raw.decode())

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_file_omitted_charset(self):
        """ For incoming email containing an xml attachment with omitted charset and containing an UTF8 payload we
        should parse the attachment using UTF-8.
        """
        record = self.format_and_process(test_mail_data.MAIL_MULTIPART_OMITTED_CHARSET, self.email_from, f'groups@{self.alias_domain}')
        self.assertEqual(record.message_ids.attachment_ids.name, 'bis3.xml')
        self.assertEqual("<Invoice>Chaussée de Bruxelles</Invoice>", record.message_ids.attachment_ids.raw.decode())

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_route_reply_model_none(self):
        """
        Test the message routing and reply functionality when the model is None.

        This test case verifies the behavior of the message routing and reply process
        when the 'model' field of a mail.message is set to None. It checks that the
        message is correctly processed and associated with the appropriate record.
        The code invokes function `format_and_process` to automatically test rounting
        and then makes checks on created record.

        """
        message = self.env['mail.message'].create({
            'body': '<p>test</p>',
            'email_from': self.email_from,
            'message_type': 'email',
            'model': None,
            'res_id': None,
        })

        self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_model_id': self.env['ir.model']._get('mail.test.gateway').id,
        })
        record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f'test@{self.alias_domain}',
            subject=message.message_id, extra=f'In-Reply-To:\r\n\t{message.message_id}\n',
            model=None)

        self.assertTrue(record)
        self.assertEqual(record._name, 'mail.test.gateway')
        self.assertEqual(record.message_ids.subject, message.message_id)
        self.assertFalse(record.message_ids.parent_id)


@tagged('mail_gateway', 'mail_thread')
class TestMailThreadCC(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailThreadCC, cls).setUpClass()

        cls.email_from = 'Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>'
        cls.alias = cls.env['mail.alias'].create({
            'alias_contact': 'everyone',
            'alias_model_id': cls.env['ir.model']._get('mail.test.cc').id,
            'alias_name': 'cc_record',
            'alias_user_id': False,
        })

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_new(self):
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, f'cc_record@{self.alias_domain}',
                                         cc='cc1@example.com, cc2@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['cc1@example.com', 'cc2@example.com'])

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_with_old(self):
        record = self.env['mail.test.cc'].create({'email_cc': 'cc1 <cc1@example.com>, cc2@example.com'})
        self.alias.write({'alias_force_thread_id': record.id})

        self.format_and_process(MAIL_TEMPLATE, self.email_from, f'cc_record@{self.alias_domain}',
                                cc='cc2 <cc2@example.com>, cc3@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['"cc1" <cc1@example.com>', 'cc2@example.com', 'cc3@example.com'], 'new cc should have been added on record (unique)')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_no_old(self):
        record = self.env['mail.test.cc'].create({})
        self.alias.write({'alias_force_thread_id': record.id})

        self.format_and_process(MAIL_TEMPLATE, self.email_from, f'cc_record@{self.alias_domain}',
                                cc='cc2 <cc2@example.com>, cc3@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['"cc2" <cc2@example.com>', 'cc3@example.com'], 'new cc should have been added on record (unique)')
