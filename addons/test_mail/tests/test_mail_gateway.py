# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import socket

from email.utils import formataddr

from odoo.addons.test_mail.data.test_mail_data import \
    MAIL_TEMPLATE, MAIL_TEMPLATE_PLAINTEXT, MAIL_MULTIPART_MIXED, MAIL_MULTIPART_MIXED_TWO, \
    MAIL_MULTIPART_IMAGE, MAIL_SINGLE_BINARY, MAIL_EML_ATTACHMENT, MAIL_XHTML
from odoo.addons.test_mail.tests.common import BaseFunctionalTest, MockEmails
from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.tools import mute_logger


class TestEmailParsing(BaseFunctionalTest, MockEmails):

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_parse(self):
        pass

    def test_message_parse_body(self):
        # test pure plaintext
        plaintext = self.format(MAIL_TEMPLATE_PLAINTEXT, email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>')
        res = self.env['mail.thread'].message_parse(plaintext)
        self.assertIn('Please call me as soon as possible this afternoon!', res['body'])

        # test multipart / text and html -> html has priority
        multipart = self.format(MAIL_TEMPLATE, email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>')
        res = self.env['mail.thread'].message_parse(multipart)
        self.assertIn('<p>Please call me as soon as possible this afternoon!</p>', res['body'])

        # test multipart / mixed
        res = self.env['mail.thread'].message_parse(MAIL_MULTIPART_MIXED)
        self.assertNotIn(
            'Should create a multipart/mixed: from gmail, *bold*, with attachment', res['body'],
            'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn(
            '<div dir="ltr">Should create a multipart/mixed: from gmail, <b>bold</b>, with attachment.<br clear="all"><div><br></div>', res['body'],
            'message_parse: html version should be in body after parsing multipart/mixed')

        res = self.env['mail.thread'].message_parse(MAIL_MULTIPART_MIXED_TWO)
        self.assertNotIn('First and second part', res['body'],
                         'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn('First part', res['body'],
                      'message_parse: first part of the html version should be in body after parsing multipart/mixed')
        self.assertIn('Second part', res['body'],
                      'message_parse: second part of the html version should be in body after parsing multipart/mixed')

        res = self.env['mail.thread'].message_parse(MAIL_SINGLE_BINARY)
        self.assertEqual(res['body'], '')
        self.assertEqual(res['attachments'][0][0], 'thetruth.pdf')


class TestMailgateway(BaseFunctionalTest, MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMailgateway, cls).setUpClass()
        mail_test_simple_model = cls.env['ir.model']._get('mail.test.simple')

        cls.bounce_alias = 'test_bounce'
        cls.catchall_alias = 'test_catchall'
        cls.catchall_domain = 'example.com'
        cls.env['ir.config_parameter'].set_param('mail.bounce.alias', cls.bounce_alias)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.catchall_alias)
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.catchall_domain)

        cls.partner_1 = cls.env['res.partner'].with_context(BaseFunctionalTest._test_context).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })
        # groups@.. will cause the creation of new mail.test.simple
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': mail_test_simple_model.id,
            'alias_contact': 'everyone'})

        # Set a first message on public group to test update and hierarchy
        cls.fake_email = cls.env['mail.message'].create({
            'model': 'mail.test.simple',
            'res_id': cls.test_record.id,
            'subject': 'Public Discussion',
            'message_type': 'email',
            'author_id': cls.partner_1.id,
            'message_id': '<123456-openerp-%s-mail.test.simple@%s>' % (cls.test_record.id, socket.gethostname()),
        })

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_parse_eml(self):
        """ Test that the parsing of mail with embedded emails as eml(msg) which generates empty attachments, can be processed.
        """
        self.env['mail.thread'].message_process('mail.channel', MAIL_EML_ATTACHMENT)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_parse_xhtml(self):
        """ Test that the parsing of mail with embedded emails as eml(msg) which generates empty attachments, can be processed.
        """
        self.env['mail.thread'].message_process('mail.channel', MAIL_XHTML)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_cid(self):
        record = self.format_and_process(MAIL_MULTIPART_IMAGE, to='groups@example.com')
        message = record.message_ids[0]
        for attachment in message.attachment_ids:
            self.assertIn('/web/image/%s' % attachment.id, message.body)

    def test_message_process_followers(self):
        pass
        # TODO : the author of a message post should be added as follower
        # currently it is not the case as otherwise Administrator would be follower of a lot of stuff
        # this is a bug with mail_create_nosubscribe -> should be changed in master
        # self.assertEqual(record.message_partner_ids, self.partner_1,
        #                  'message_process: recognized email -> added as follower')

        # TODO : the author of a message post on mail.test should not be added as follower
        # Test: author (and not recipient) added as follower
        # self.assertEqual(self.test_public.message_partner_ids, self.partner_1 | self.partner_2,
        #                  'message_process: after reply, group should have 2 followers')
        # self.assertEqual(self.test_public.message_channel_ids, self.env['mail.test'],
        #                  'message_process: after reply, group should have 2 followers (0 channels)')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_basic(self):
        """ Test details of created message going through mailgateway """
        record = self.format_and_process(MAIL_TEMPLATE, subject='Specific')

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

    # --------------------------------------------------
    # Author recognition
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_email_from(self):
        """ Incoming email: not recognized author: email_from, no author_id, no followers """
        email_from = 'Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>'

        record = self.format_and_process(MAIL_TEMPLATE, email_from=email_from)
        self.assertFalse(record.message_ids[0].author_id, 'message_process: unrecognized email -> no author_id')
        self.assertEqual(record.message_ids[0].email_from, email_from)
        self.assertEqual(len(record.message_partner_ids), 0,
                         'message_process: newly create group should not have any follower')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_author(self):
        """ Incoming email: recognized author: email_from, author_id, added as follower """
        record = self.format_and_process(MAIL_TEMPLATE, email_from=formataddr((self.partner_1.name, self.partner_1.email)))

        self.assertEqual(record.message_ids[0].author_id, self.partner_1,
                         'message_process: recognized email -> author_id')
        self.assertEqual(record.message_ids[0].email_from, formataddr((self.partner_1.name, self.partner_1.email)))
        self.assertEqual(len(self._mails), 0, 'No notification / bounce should be sent')

    # --------------------------------------------------
    # Alias configuration
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_user_id(self):
        """ Test alias ownership """
        self.alias.write({'alias_user_id': self.user_employee.id})

        record = self.format_and_process(MAIL_TEMPLATE)
        self.assertEqual(len(record), 1)
        res = record.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_everyone(self):
        """ Incoming email: everyone: new record + message_new """
        self.alias.write({'alias_contact': 'everyone'})

        record = self.format_and_process(MAIL_TEMPLATE, subject='Specific')
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.message_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_partners_bounce(self):
        """ Incoming email from an unknown partner on a Partners only alias -> bounce + test bounce email """
        self.env['ir.config_parameter'].set_param('mail.bounce.alias', 'bounce.test')
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'test.com')
        self.alias.write({'alias_contact': 'partners'})

        # Test: no group created, email bounced
        record = self.format_and_process(MAIL_TEMPLATE, to='groups@test.com, other@gmail.com', subject='Should Bounce')
        self.assertTrue(len(record) == 0)
        self.assertEqual(len(self._mails), 1,
                         'message_process: incoming email on Partners alias should send a bounce email')
        # Test bounce email
        self.assertEqual(self._mails[0].get('subject'), 'Re: Should Bounce')
        self.assertEqual(self._mails[0].get('email_to')[0], 'whatever-2a840@postmaster.twitter.com')
        self.assertEqual(self._mails[0].get('email_from'), formataddr(('MAILER-DAEMON', 'bounce.test@test.com')))

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_followers_bounce(self):
        """ Incoming email from unknown partner / not follower partner on a Followers only alias -> bounce """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.env['ir.model']._get('mail.test.simple').id,
            'alias_parent_thread_id': self.test_record.id,
        })

        # Test: unknown on followers alias -> bounce
        record = self.format_and_process(MAIL_TEMPLATE, to='groups@example.com, other@gmail.com')
        self.assertEqual(len(record), 0, 'message_process: should have bounced')
        self.assertEqual(len(self._mails), 1,
                         'message_process: incoming email on Followers alias should send a bounce email')

        # Test: partner on followers alias -> bounce
        self._init_mock_build_email()
        record = self.format_and_process(MAIL_TEMPLATE, email_from=formataddr((self.partner_1.name, self.partner_1.email)))
        self.assertTrue(len(record) == 0, 'message_process: should have bounced')
        self.assertEqual(len(self._mails), 1,
                         'message_process: incoming email on Followers alias should send a bounce email')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_partner(self):
        """ Incoming email from a known partner on a Partners alias -> ok (+ test on alias.user_id) """
        self.alias.write({'alias_contact': 'partners'})
        record = self.format_and_process(MAIL_TEMPLATE, email_from=formataddr((self.partner_1.name, self.partner_1.email)))

        # Test: one group created by alias user
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.message_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_followers(self):
        """ Incoming email from a parent document follower on a Followers only alias -> ok """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.env['ir.model']._get('mail.test.simple').id,
            'alias_parent_thread_id': self.test_record.id,
        })
        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        record = self.format_and_process(MAIL_TEMPLATE, email_from=formataddr((self.partner_1.name, self.partner_1.email)))

        # Test: one group created by Raoul (or Sylvie maybe, if we implement it)
        self.assertEqual(len(record), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_update(self):
        """ Incoming email update discussion + notification email """
        self.alias.write({'alias_force_thread_id': self.test_record.id})

        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        record = self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com',
            msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>',
            to='groups@example.com>', subject='Re: cats')

        # Test: no new group + new message
        self.assertEqual(len(record), 0, 'message_process: alias update should not create new records')
        self.assertEqual(len(self.test_record.message_ids), 2)
        # Test: sent emails: 1 (Sylvie copy of the incoming email)
        self.assertEqual(len(self._mails), 1,
                         'message_process: one email should have been generated')
        self.assertEqual(formataddr((self.partner_1.name, self.partner_1.email)), self._mails[0].get('email_to')[0],
                         'message_process: email should be sent to Sylvie')

    # --------------------------------------------------
    # Alias + Domain management
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_domain_confusion_no_domain(self):
        """ Incoming email: write to alias even if no domain set: considered as valid alias """
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', '')

        new_groups = self.format_and_process(
            MAIL_TEMPLATE,
            subject='Test Subject',
            email_from='valid.other@gmail.com',
            to='groups@another.domain.com',
            msg_id='<whatever.JavaMail.diff1@agrolait.com>'
        )
        # Test: one group created
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.test should have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_forward_domain_confusion(self):
        """ Incoming email: write to alias of another model: forward to new alias """
        new_alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test').id,
            'alias_contact': 'everyone',
        })
        new_rec = self.format_and_process(
            MAIL_TEMPLATE,
            subject='Test Subject',
            email_from='valid.other@gmail.com',
            to='%s@%s, %s@%s' % (self.alias.alias_name, self.catchall_domain, new_alias_2.alias_name, self.catchall_domain),
            msg_id='<whatever.JavaMail.diff1@agrolait.com>',
            target_model=new_alias_2.alias_model_id.model
        )
        # Test: one channel (alias 2) created
        self.assertEqual(len(new_rec), 1, 'message_process: a new mail.channel should have been created')
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_forward_domain_confusion_no_domain(self):
        """ Incoming email: write to alias of another model: forward to new alias even if no catchall domain """
        new_alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test').id,
            'alias_contact': 'everyone',
        })
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', '')

        new_rec = self.format_and_process(
            MAIL_TEMPLATE,
            subject='Test Subject',
            email_from='valid.other@gmail.com',
            to='%s@%s, %s@%s' % (self.alias.alias_name, self.catchall_domain, new_alias_2.alias_name, 'another.domain.com'),
            msg_id='<whatever.JavaMail.diff1@agrolait.com>',
            target_model=new_alias_2.alias_model_id.model
        )
        # Test: one channel (alias 2) created
        self.assertEqual(len(new_rec), 1, 'message_process: a new mail.channel should have been created')
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)

    # --------------------------------------------------
    # Email Management
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_bounce(self):
        """Incoming email: bounce processing: no group created, message_bounce increased """
        new_groups = self.format_and_process(
            MAIL_TEMPLATE,
            email_from='Valid Lelitre <valid.lelitre@agrolait.com>',
            to='%s+%s-%s-%s@%s' % (
                self.bounce_alias, self.fake_email.id,
                self.fake_email.model, self.fake_email.res_id,
                self.catchall_domain
            ),
            subject='Should bounce',
        )
        self.assertFalse(new_groups)
        self.assertEqual(len(self._mails), 0, 'message_process: incoming bounce produces no mails')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_bounce_other_recipients(self):
        """Incoming email: bounce processing: bounce should be computed even if not first recipient """
        new_groups = self.format_and_process(
            MAIL_TEMPLATE,
            email_from='Valid Lelitre <valid.lelitre@agrolait.com>',
            to='%s@%s, %s+%s-%s-%s@%s' % (
                self.alias.alias_name, self.catchall_domain,
                self.bounce_alias, self.fake_email.id,
                self.fake_email.model, self.fake_email.res_id,
                self.catchall_domain
            ),
            subject='Should bounce',
        )
        self.assertFalse(new_groups)
        self.assertEqual(len(self._mails), 0, 'message_process: incoming bounce produces no mails')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_message_process_write_to_catchall(self):
        """ Writing directly to catchall should bounce """
        # Test: no group created, email bounced
        record = self.format_and_process(
            MAIL_TEMPLATE,
            to='%s@%s' % (self.catchall_alias, self.catchall_domain),
            subject='Should Bounce'
        )
        self.assertTrue(len(record) == 0)
        self.assertEqual(len(self._mails), 1,
                         'message_process: writing directly to catchall should bounce')
        # Test bounce email
        self.assertEqual(self._mails[0].get('subject'), 'Re: Should Bounce')
        self.assertEqual(self._mails[0].get('email_to')[0], 'whatever-2a840@postmaster.twitter.com')
        self.assertEqual(self._mails[0].get('email_from'), formataddr(('MAILER-DAEMON', '%s@%s' % (self.bounce_alias, self.catchall_domain))))

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_write_to_catchall_and_alias(self):
        """ Writing directly to catchall and a valid alias should take alias """
        # Test: no group created, email bounced
        record = self.format_and_process(
            MAIL_TEMPLATE,
            to='%s@%s, %s@%s' % (self.catchall_alias, self.catchall_domain, self.alias.alias_name, self.catchall_domain),
            subject='Catchall Not Blocking'
        )
        # Test: one group created
        self.assertEqual(len(record), 1, 'message_process: a new mail.test should have been created')
        # No bounce email
        self.assertEqual(len(self._mails), 0)

    # --------------------------------------------------
    # Thread formation
    # --------------------------------------------------

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_in_reply_to(self):
        """ Incoming email using in-rely-to should go into the right destination even with a wrong destination """
        self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com',
            msg_id='<1198923581.41972151344608186800.JavaMail.diff1@agrolait.com>',
            to='erroneous@example.com>', subject='Re: news',
            extra='In-Reply-To:\r\n\t%s\n' % self.fake_email.message_id)

        self.assertEqual(len(self.test_record.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references(self):
        """ Incoming email using references should go into the right destination even with a wrong destination """
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, to='erroneous@example.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(len(self.fake_email.child_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_references_external(self):
        """ Incoming email being a reply to an external email processed by odoo should update thread accordingly """
        new_message_id = '<ThisIsTooMuchFake.MonsterEmail.789@agrolait.com>'
        self.fake_email.write({
            'message_id': new_message_id
        })
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE, to='erroneous@example.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(len(self.fake_email.child_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_references_forward(self):
        """ Incoming email using references but with alias forward should not go into references destination """
        new_alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test').id,
            'alias_contact': 'everyone',
        })
        init_msg_count = len(self.test_record.message_ids)
        res_test = self.format_and_process(
            MAIL_TEMPLATE, to='test@example.com',
            subject='My Dear Forward',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>',
            target_model='mail.test')

        self.assertEqual(len(self.test_record.message_ids), init_msg_count)
        self.assertEqual(len(self.fake_email.child_ids), 0)
        self.assertEqual(res_test.name, 'My Dear Forward')
        self.assertEqual(len(res_test.message_ids), 1)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references_forward_cc(self):
        """ Incoming email using references but with alias forward should not go into references destination """
        self.format_and_process(
            MAIL_TEMPLATE, to='erroneous@example.com', cc='test@example.com',
            subject='My Dear Forward',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>',
            target_model='mail.test.simple')

        self.assertEqual(len(self.test_record.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_model_res_id(self):
        """ Incoming email with ref holding model / res_id but that does not match any message in the thread: must raise since OpenERP saas-3 """
        self.assertRaises(ValueError,
                          self.format_and_process, MAIL_TEMPLATE,
                          email_from=formataddr((self.partner_1.name, self.partner_1.email)),
                          to='noone@example.com', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.test.simple@%s>' % (self.test_record.id, socket.gethostname()),
                          msg_id='<1198923581.41972151344608186802.JavaMail.diff1@agrolait.com>')

        # when 6.1 messages are present, compat mode is available
        # Odoo 10 update: compat mode has been removed and should not work anymore
        self.fake_email.write({'message_id': False})
        # Do: compat mode accepts partial-matching emails
        self.assertRaises(
            ValueError,
            self.format_and_process,
            MAIL_TEMPLATE, email_from=formataddr((self.partner_1.name, self.partner_1.email)),
            msg_id='<1.2.JavaMail.new@agrolait.com>',
            to='noone@example.com>', subject='spam',
            extra='In-Reply-To: <12321321-openerp-%d-mail.test.simple@%s>' % (self.test_record.id, socket.gethostname()))

        # 3''. 6.1 compat mode should not work if hostname does not match!
        # Odoo 10 update: compat mode has been removed and should not work anymore and does not depend from hostname
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, email_from=formataddr((self.partner_1.name, self.partner_1.email)),
                          msg_id='<1.3.JavaMail.new@agrolait.com>',
                          to='noone@example.com>', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.test@neighbor.com>' % self.test_record.id)

        # Test created messages
        self.assertEqual(len(self.test_record.message_ids), 1)
        self.assertEqual(len(self.test_record.message_ids[0].child_ids), 0)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_duplicate(self):
        """ Duplicate emails (same message_id) are not processed """
        self.alias.write({'alias_force_thread_id': self.test_record.id,})

        # Post a base message
        record = self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com', subject='Re: super cats',
            msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')

        # Do: due to some issue, same email goes back into the mailgateway
        record = self.format_and_process(
            MAIL_TEMPLATE, email_from='other4@gmail.com', subject='Re: news',
            msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>',
            extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>\n')

        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(record), 0)

        # Test: no new message
        self.assertEqual(len(self.test_record.message_ids), 2, 'message_process: message with already existing message_id should not have been duplicated')
        # Test: message_id is still unique
        no_of_msg = self.env['mail.message'].search_count([('message_id', 'ilike', '<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')])
        self.assertEqual(no_of_msg, 1,
                         'message_process: message with already existing message_id should not have been duplicated')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_partner_find(self):
        """ Finding the partner based on email, based on partner / user / follower """
        self.alias.write({'alias_force_thread_id': self.test_record.id})
        from_1 = self.env['res.partner'].create({'name': 'Brice Denisse', 'email': 'from.test@example.com'})

        self.format_and_process(MAIL_TEMPLATE, msg_id='<1>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_1)
        self.test_record.message_unsubscribe([from_1.id])

        from_2 = mail_new_test_user(self.env, login='B', groups='base.group_user', name='Brice Denisse', email='from.test@example.com')

        self.format_and_process(MAIL_TEMPLATE, msg_id='<2>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_2.partner_id)
        self.test_record.message_unsubscribe([from_2.partner_id.id])

        from_3 = self.env['res.partner'].create({'name': 'Brice Denisse', 'email': 'from.test@example.com'})
        self.test_record.message_subscribe([from_3.id])

        self.format_and_process(MAIL_TEMPLATE, msg_id='<3>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.test_record.message_ids[0].author_id, from_3)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_crash_wrong_model(self):
        """ Incoming email with model that does not accepts incoming emails must raise """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE,
                          to='noone@example.com', subject='spam', extra='', model='res.country',
                          msg_id='<1198923581.41972151344608186760.JavaMail.new4@agrolait.com>')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_crash_no_data(self):
        """ Incoming email without model and without alias must raise """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE,
                          to='noone@example.com', subject='spam', extra='',
                          msg_id='<1198923581.41972151344608186760.JavaMail.new5@agrolait.com>')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_fallback(self):
        """ Incoming email with model that accepting incoming emails as fallback """
        record = self.format_and_process(
            MAIL_TEMPLATE, to='noone@example.com', subject='Spammy', extra='', model='mail.test.simple',
            msg_id='<1198923581.41972151344608186760.JavaMail.new6@agrolait.com>')
        self.assertEqual(len(record), 1)
        self.assertEqual(record._name, 'mail.test.simple')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_plain_text(self):
        """ Incoming email in plaintext should be stored as html """
        record = self.format_and_process(
            MAIL_TEMPLATE_PLAINTEXT, to='groups@example.com', subject='Frogs Return', extra='',
            msg_id='<deadcafe.1337@smtp.agrolait.com>')
        self.assertEqual(len(record), 1, 'message_process: a new mail.test should have been created')
        msg = record.message_ids[0]
        # signature recognition -> Sylvie should be in a span
        self.assertIn('<pre>\nPlease call me as soon as possible this afternoon!\n<span data-o-mail-quote="1">\n--\nSylvie\n</span></pre>', msg.body,
                      'message_process: plaintext incoming email incorrectly parsed')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_private_discussion(self):
        """ Testing private discussion between partners. """
        self.partner_2 = self.env['res.partner'].with_context(BaseFunctionalTest._test_context).create({
            'name': 'Admin',
            'email': 'admin@agrolait.com',
        })
        msg1_pids = [self.partner_1.id, self.partner_2.id]

        # Do: Raoul writes to Bert and Administrator, with a model specific by parameter that should not be taken into account
        msg1 = self.env['mail.thread'].sudo(self.user_employee).message_post(partner_ids=msg1_pids, subtype='mail.mt_comment', model='mail.test')

        # Test: message recipients
        msg = self.env['mail.message'].browse(msg1.id)
        self.assertEqual(msg.partner_ids, self.partner_2 | self.partner_1,
                         'message_post: private discussion: incorrect recipients')
        self.assertEqual(msg.model, False,
                         'message_post: private discussion: parameter model not correctly ignored when having no res_id')
        # Test: message-id
        self.assertIn('openerp-private', msg.message_id.split('@')[0], 'message_post: private discussion: message-id should contain the private keyword')

        # Do: Bert replies through mailgateway (is a customer)
        self.format_and_process(
            MAIL_TEMPLATE, to='not_important@mydomain.com', email_from='valid.lelitre@agrolait.com',
            extra='In-Reply-To: %s' % msg.message_id, msg_id='<test30.JavaMail.0@agrolait.com>')

        # Test: last mail_message created
        msg2 = self.env['mail.message'].search([], limit=1)
        # Test: message recipients
        self.assertEqual(msg2.author_id, self.partner_1,
                         'message_post: private discussion: wrong author through mailgateway based on email')
        self.assertEqual(msg2.partner_ids, self.user_employee.partner_id | self.partner_2,
                         'message_post: private discussion: incorrect recipients when replying')

        # Do: Bert replies through chatter (is a customer)
        msg3 = self.env['mail.thread'].message_post(author_id=self.partner_1.id, parent_id=msg1.id, subtype='mail.mt_comment')

        # Test: message recipients
        msg = self.env['mail.message'].browse(msg3.id)
        self.assertEqual(msg.partner_ids, self.user_employee.partner_id | self.partner_2,
                         'message_post: private discussion: incorrect recipients when replying')
        self.assertEqual(msg.needaction_partner_ids, self.user_employee.partner_id | self.partner_2,
                         'message_post: private discussion: incorrect notified recipients when replying')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_forward_parent_id(self):
        msg = self.test_record.sudo(self.user_employee).message_post(no_auto_thread=True, subtype='mail.mt_comment')
        self.assertNotIn(msg.model, msg.message_id.split('@')[0])
        self.assertNotIn('-%d-' % msg.res_id, msg.message_id.split('@')[0])
        self.assertIn('reply_to', msg.message_id.split('@')[0])

        # forward it to a new thread AND an existing thread
        fw_msg_id = '<THIS.IS.A.FW.MESSAGE.1@bert.fr>'
        fw_message = MAIL_TEMPLATE.format(to='groups@example.com',
                                          cc='',
                                          subject='FW: Re: 1',
                                          email_from='b.t@example.com',
                                          extra='In-Reply-To: %s' % msg.message_id,
                                          msg_id=fw_msg_id)
        self.env['mail.thread'].message_process(None, fw_message)
        msg_fw = self.env['mail.message'].search([('message_id', '=', fw_msg_id)])
        self.assertEqual(len(msg_fw), 1)
        new_record = self.env['mail.test.simple'].search([('name', "=", msg_fw.subject)])
        self.assertEqual(len(new_record), 1)
        self.assertEqual(msg_fw.model, 'mail.test.simple')
        self.assertFalse(msg_fw.parent_id)
        self.assertTrue(msg_fw.res_id == new_record.id)
