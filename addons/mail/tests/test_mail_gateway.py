# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import socket

from odoo.addons.mail.tests.data.test_mail_data import MAIL_TEMPLATE, MAIL_TEMPLATE_PLAINTEXT, MAIL_MULTIPART_MIXED, MAIL_MULTIPART_MIXED_TWO, MAIL_MULTIPART_IMAGE
from odoo.addons.mail.tests.common import TestMail
from odoo.tools import mute_logger


class TestMailgateway(TestMail):

    def setUp(self):
        super(TestMailgateway, self).setUp()
        mail_test_model = self.env['ir.model']._get('mail.test')
        mail_channel_model = self.env['ir.model']._get('mail.channel')

        # groups@.. will cause the creation of new mail.test
        self.alias = self.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': mail_test_model.id,
            'alias_contact': 'everyone'})

        # test@.. will cause the creation of new mail.test
        self.alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': mail_channel_model.id,
            'alias_contact': 'everyone'})

        # Set a first message on public group to test update and hierarchy
        self.fake_email = self.env['mail.message'].create({
            'model': 'mail.test',
            'res_id': self.test_public.id,
            'subject': 'Public Discussion',
            'message_type': 'email',
            'author_id': self.partner_1.id,
            'message_id': '<123456-openerp-%s-mail.test@%s>' % (self.test_public.id, socket.gethostname()),
        })

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_parse(self):
        """ Test parsing of various scenarios of incoming emails """
        res = self.env['mail.thread'].message_parse(MAIL_TEMPLATE_PLAINTEXT)
        self.assertIn('Please call me as soon as possible this afternoon!',
                      res.get('body', ''),
                      'message_parse: missing text in text/plain body after parsing')

        res = self.env['mail.thread'].message_parse(MAIL_TEMPLATE)
        self.assertIn('<p>Please call me as soon as possible this afternoon!</p>',
                      res.get('body', ''),
                      'message_parse: missing html in multipart/alternative body after parsing')

        res = self.env['mail.thread'].message_parse(MAIL_MULTIPART_MIXED)
        self.assertNotIn('Should create a multipart/mixed: from gmail, *bold*, with attachment',
                         res.get('body', ''),
                         'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn('<div dir="ltr">Should create a multipart/mixed: from gmail, <b>bold</b>, with attachment.<br clear="all"><div><br></div>',
                      res.get('body', ''),
                      'message_parse: html version should be in body after parsing multipart/mixed')

        res = self.env['mail.thread'].message_parse(MAIL_MULTIPART_MIXED_TWO)
        self.assertNotIn('First and second part',
                         res.get('body', ''),
                         'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn('First part',
                      res.get('body', ''),
                      'message_parse: first part of the html version should be in body after parsing multipart/mixed')
        self.assertIn('Second part',
                      res.get('body', ''),
                      'message_parse: second part of the html version should be in body after parsing multipart/mixed')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_process_cid(self):
        new_groups = self.format_and_process(MAIL_MULTIPART_IMAGE, subject='My Frogs', to='groups@example.com')
        message = new_groups.message_ids[0]
        for attachment in message.attachment_ids:
            self.assertIn('/web/image/%s' % attachment.id, message.body)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_basic(self):
        """ Incoming email on an alias creating a new record + message_new + message details """
        new_groups = self.format_and_process(MAIL_TEMPLATE, subject='My Frogs', to='groups@example.com, other@gmail.com')

        # Test: one group created by mailgateway administrator
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.test should have been created')
        res = new_groups.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.env.uid,
                         'message_process: group should have been created by uid as alias_user_id is False on the alias')

        # Test: one message that is the incoming email
        self.assertEqual(len(new_groups.message_ids), 1,
                         'message_process: newly created group should have the incoming email in message_ids')
        msg = new_groups.message_ids[0]
        self.assertEqual(msg.subject, 'My Frogs',
                         'message_process: newly created group should have the incoming email as first message')
        self.assertIn('Please call me as soon as possible this afternoon!', msg.body,
                      'message_process: newly created group should have the incoming email as first message')
        self.assertEqual(msg.message_type, 'email',
                         'message_process: newly created group should have an email as first message')
        self.assertEqual(msg.subtype_id, self.env.ref('mail.mt_comment'),
                         'message_process: newly created group should not have a log first message but an email')

        # Test: sent emails: no-one
        self.assertEqual(len(self._mails), 0,
                         'message_process: should create emails without any follower added')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_user_id(self):
        """ Test alias ownership """
        self.alias.write({'alias_user_id': self.user_employee.id})
        new_groups = self.format_and_process(MAIL_TEMPLATE, to='groups@example.com, other@gmail.com')

        # Test: one group created by mailgateway administrator
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.test should have been created')
        res = new_groups.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_employee.id,
                         'message_process: group should have been created by alias_user_id')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_email_from(self):
        """ Incoming email: not recognized author: email_from, no author_id, no followers """
        new_groups = self.format_and_process(MAIL_TEMPLATE, to='groups@example.com, other@gmail.com')

        self.assertFalse(new_groups.message_ids[0].author_id,
                         'message_process: unrecognized email -> no author_id')
        self.assertIn('test.sylvie.lelitre@agrolait.com', new_groups.message_ids[0].email_from,
                      'message_process: unrecognized email -> email_from')

        self.assertEqual(len(new_groups.message_partner_ids), 0,
                         'message_process: newly create group should not have any follower')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_email_author(self):
        """ Incoming email: recognized author: email_from, author_id, added as follower """
        new_groups = self.format_and_process(MAIL_TEMPLATE, email_from='Valid Lelitre <valid.lelitre@agrolait.com>', to='groups@example.com, valid.other@gmail.com')

        self.assertEqual(new_groups.message_ids[0].author_id, self.partner_1,
                         'message_process: recognized email -> author_id')
        self.assertIn('Valid Lelitre <valid.lelitre@agrolait.com>', new_groups.message_ids[0].email_from,
                      'message_process: recognized email -> email_from')

        # TODO : the author of a message post on mail.test should not be added as follower
        # FAIL ON recognized email -> added as follower')
        # self.assertEqual(new_groups.message_partner_ids, self.partner_1,
        #                  'message_process: recognized email -> added as follower')

        self.assertEqual(len(self._mails), 0,
                         'message_process: no bounce or notificatoin email should be sent with follower = author')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_partners_bounce(self):
        """ Incoming email from an unknown partner on a Partners only alias -> bounce """
        self.alias.write({'alias_contact': 'partners'})

        # Test: no group created, email bounced
        new_groups = self.format_and_process(MAIL_TEMPLATE, subject='New Frogs', to='groups@example.com, other@gmail.com')
        self.assertTrue(len(new_groups) == 0)
        self.assertEqual(len(self._mails), 1,
                         'message_process: incoming email on Partners alias should send a bounce email')
        self.assertIn('New Frogs', self._mails[0].get('subject'),
                      'message_process: bounce email on Partners alias should contain the original subject')
        self.assertIn('whatever-2a840@postmaster.twitter.com', self._mails[0].get('email_to'),
                      'message_process: bounce email on Partners alias should go to Return-Path address')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_followers_bounce(self):
        """ Incoming email from unknown partner / not follower partner on a Followers only alias -> bounce """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.env['ir.model']._get('mail.test').id,
            'alias_parent_thread_id': self.test_pigs.id})

        # Test: unknown on followers alias -> bounce
        new_groups = self.format_and_process(MAIL_TEMPLATE, to='groups@example.com, other@gmail.com')
        self.assertEqual(len(new_groups), 0, 'message_process: should have bounced')
        self.assertEqual(len(self._mails), 1,
                         'message_process: incoming email on Followers alias should send a bounce email')

        # Test: partner on followers alias -> bounce
        self._init_mock_build_email()
        new_groups = self.format_and_process(MAIL_TEMPLATE, email_from='Valid Lelitre <valid.lelitre@agrolait.com>', to='groups@example.com, other@gmail.com')
        self.assertTrue(len(new_groups) == 0, 'message_process: should have bounced')
        self.assertEqual(len(self._mails), 1,
                         'message_process: incoming email on Followers alias should send a bounce email')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_partner(self):
        """ Incoming email from a known partner on a Partners alias -> ok (+ test on alias.user_id) """
        self.alias.write({'alias_contact': 'partners'})
        new_groups = self.format_and_process(MAIL_TEMPLATE, email_from='Valid Lelitre <valid.lelitre@agrolait.com>', to='groups@example.com, valid.other@gmail.com')

        # Test: one group created by alias user
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.test should have been created')

        # Test: one message that is the incoming email
        self.assertEqual(len(new_groups.message_ids), 1,
                         'message_process: newly created group should have the incoming email in message_ids')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_followers(self):
        """ Incoming email from a parent document follower on a Followers only alias -> ok """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.env['ir.model']._get('mail.test').id,
            'alias_parent_thread_id': self.test_pigs.id})
        self.test_pigs.message_subscribe(partner_ids=[self.partner_1.id])
        new_groups = self.format_and_process(MAIL_TEMPLATE, email_from='Valid Lelitre <valid.lelitre@agrolait.com>', to='groups@example.com, other6@gmail.com')

        # Test: one group created by Raoul (or Sylvie maybe, if we implement it)
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.test should have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_update(self):
        """ Incoming email update discussion + notification email """
        self.alias.write({'alias_force_thread_id': self.test_public.id})

        self.test_public.message_subscribe(partner_ids=[self.partner_1.id])
        new_groups = self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com',
            msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>',
            to='groups@example.com>', subject='Re: cats')

        # Test: no new group + new message
        self.assertEqual(len(new_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')
        self.assertEqual(len(self.test_public.message_ids), 2, 'message_process: group should contain one new message')
        # Test: sent emails: 1 (Sylvie copy of the incoming email)
        self.assertEqual(len(self._mails), 1,
                         'message_process: one email should have been generated')
        self.assertIn('valid.lelitre@agrolait.com', self._mails[0].get('email_to')[0],
                      'message_process: email should be sent to Sylvie')

        # TODO : the author of a message post on mail.test should not be added as follower
        # FAIL ON 'message_process: after reply, group should have 2 followers') ` AssertionError: res.partner(104,) != res.partner(104, 105) : message_process: after reply, group should have 2 followers

        # Test: author (and not recipient) added as follower
        # self.assertEqual(self.test_public.message_partner_ids, self.partner_1 | self.partner_2,
        #                  'message_process: after reply, group should have 2 followers')
        # self.assertEqual(self.test_public.message_channel_ids, self.env['mail.test'],
        #                  'message_process: after reply, group should have 2 followers (0 channels)')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_in_reply_to(self):
        """ Incoming email using in-rely-to should go into the right destination even with a wrong destination """
        self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com',
            msg_id='<1198923581.41972151344608186800.JavaMail.diff1@agrolait.com>',
            to='erroneous@example.com>', subject='Re: news',
            extra='In-Reply-To:\r\n\t%s\n' % self.fake_email.message_id)

        self.assertEqual(len(self.test_public.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references(self):
        """ Incoming email using references should go into the right destination even with a wrong destination """
        self.format_and_process(
            MAIL_TEMPLATE, to='erroneous@example.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>')

        self.assertEqual(len(self.test_public.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    def test_message_process_references_external(self):
        """ Incoming email being a reply to an external email processed by odoo should update thread accordingly """
        new_message_id = '<ThisIsTooMuchFake.MonsterEmail.789@agrolait.com>'
        self.fake_email.write({
            'message_id': new_message_id
        })
        self.format_and_process(
            MAIL_TEMPLATE, to='erroneous@example.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>')

        self.assertEqual(len(self.test_public.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    # @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references_forward(self):
        """ Incoming email using references but with alias forward should not go into references destination """
        res_test = self.format_and_process(
            MAIL_TEMPLATE, to='test@example.com',
            subject='My Dear Forward',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>',
            target_model='mail.channel')

        self.assertEqual(len(self.test_public.message_ids), 1, 'message_process: group should not contain new message')
        self.assertEqual(len(self.fake_email.child_ids), 0, 'message_process: original email should not contain childs')
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
            target_model='mail.test')

        self.assertEqual(len(self.test_public.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_model_res_id(self):
        """ Incoming email with ref holding model / res_id but that does not match any message in the thread: must raise since OpenERP saas-3 """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, email_from='valid.lelitre@agrolait.com',
                          to='noone@example.com', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.test@%s>' % (self.test_public.id, socket.gethostname()),
                          msg_id='<1198923581.41972151344608186802.JavaMail.diff1@agrolait.com>')

        # when 6.1 messages are present, compat mode is available
        # Odoo 10 update: compat mode has been removed and should not work anymore
        self.fake_email.write({'message_id': False})
        # Do: compat mode accepts partial-matching emails
        self.assertRaises(
            ValueError,
            self.format_and_process,
            MAIL_TEMPLATE, email_from='other5@gmail.com',
            msg_id='<1.2.JavaMail.new@agrolait.com>',
            to='noone@example.com>', subject='spam',
            extra='In-Reply-To: <12321321-openerp-%d-mail.test@%s>' % (self.test_public.id, socket.gethostname()))

        # 3''. 6.1 compat mode should not work if hostname does not match!
        # Odoo 10 update: compat mode has been removed and should not work anymore and does not depend from hostname
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, email_from='other5@gmail.com',
                          msg_id='<1.3.JavaMail.new@agrolait.com>',
                          to='noone@example.com>', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.test@neighbor.com>' % self.test_public.id)

        # Test created messages
        self.assertEqual(len(self.test_public.message_ids), 1)
        self.assertEqual(len(self.test_public.message_ids[0].child_ids), 0)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_duplicate(self):
        """ Duplicate emails (same message_id) are not processed """
        self.alias.write({'alias_force_thread_id': self.test_public.id,})

        # Post a base message
        frog_groups = self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com', subject='Re: super cats',
            msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')

        # Do: due to some issue, same email goes back into the mailgateway
        frog_groups = self.format_and_process(
            MAIL_TEMPLATE, email_from='other4@gmail.com', subject='Re: news',
            msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>',
            extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>\n')

        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')

        # Test: no new message
        self.assertEqual(len(self.test_public.message_ids), 2, 'message_process: message with already existing message_id should not have been duplicated')
        # Test: message_id is still unique
        no_of_msg = self.env['mail.message'].search_count([('message_id', 'ilike', '<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')])
        self.assertEqual(no_of_msg, 1,
                         'message_process: message with already existing message_id should not have been duplicated')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_partner_find(self):
        """ Finding the partner based on email, based on partner / user / follower """
        from_1 = self.env['res.partner'].create({'name': 'A', 'email': 'from.test@example.com'})

        self.format_and_process(MAIL_TEMPLATE, to='public@example.com', msg_id='<1>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.test_public.message_ids[0].author_id, from_1, 'message_process: email_from -> author_id wrong')
        self.test_public.message_unsubscribe([from_1.id])

        from_2 = self.env['res.users'].with_context({'no_reset_password': True}).create({'name': 'B', 'login': 'B', 'email': 'from.test@example.com'})

        self.format_and_process(MAIL_TEMPLATE, to='public@example.com', msg_id='<2>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.test_public.message_ids[0].author_id, from_2.partner_id, 'message_process: email_from -> author_id wrong')
        self.test_public.message_unsubscribe([from_2.partner_id.id])

        from_3 = self.env['res.partner'].create({'name': 'C', 'email': 'from.test@example.com'})
        self.test_public.message_subscribe([from_3.id])

        self.format_and_process(MAIL_TEMPLATE, to='public@example.com', msg_id='<3>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.test_public.message_ids[0].author_id, from_3, 'message_process: email_from -> author_id wrong')

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
        frog_groups = self.format_and_process(
            MAIL_TEMPLATE, to='noone@example.com', subject='Spammy', extra='', model='mail.test',
            msg_id='<1198923581.41972151344608186760.JavaMail.new6@agrolait.com>')
        self.assertEqual(len(frog_groups), 1,
                         'message_process: erroneous email but with a fallback model should have created a new mail.test')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_plain_text(self):
        """ Incoming email in plaintext should be stored as html """
        frog_groups = self.format_and_process(
            MAIL_TEMPLATE_PLAINTEXT, to='groups@example.com', subject='Frogs Return', extra='',
            msg_id='<deadcafe.1337@smtp.agrolait.com>')
        self.assertEqual(len(frog_groups), 1, 'message_process: a new mail.test should have been created')
        msg = frog_groups.message_ids[0]
        # signature recognition -> Sylvie should be in a span
        self.assertIn('<pre>\nPlease call me as soon as possible this afternoon!\n<span data-o-mail-quote="1">\n--\nSylvie\n</span></pre>', msg.body,
                      'message_process: plaintext incoming email incorrectly parsed')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_private_discussion(self):
        """ Testing private discussion between partners. """
        msg1_pids = [self.env.user.partner_id.id, self.partner_1.id]

        # Do: Raoul writes to Bert and Administrator, with a thread_model in context that should not be taken into account
        msg1 = self.env['mail.thread'].with_context({
            'thread_model': 'mail.test'
        }).sudo(self.user_employee).message_post(partner_ids=msg1_pids, subtype='mail.mt_comment')

        # Test: message recipients
        msg = self.env['mail.message'].browse(msg1.id)
        self.assertEqual(msg.partner_ids, self.env.user.partner_id | self.partner_1,
                         'message_post: private discussion: incorrect recipients')
        self.assertEqual(msg.model, False,
                         'message_post: private discussion: context key "thread_model" not correctly ignored when having no res_id')
        # Test: message-id
        self.assertIn('openerp-private', msg.message_id, 'message_post: private discussion: message-id should contain the private keyword')

        # Do: Bert replies through mailgateway (is a customer)
        self.format_and_process(
            MAIL_TEMPLATE, to='not_important@mydomain.com', email_from='valid.lelitre@agrolait.com',
            extra='In-Reply-To: %s' % msg.message_id, msg_id='<test30.JavaMail.0@agrolait.com>')

        # Test: last mail_message created
        msg2 = self.env['mail.message'].search([], limit=1)
        # Test: message recipients
        self.assertEqual(msg2.author_id, self.partner_1,
                         'message_post: private discussion: wrong author through mailgateway based on email')
        self.assertEqual(msg2.partner_ids, self.user_employee.partner_id | self.env.user.partner_id,
                         'message_post: private discussion: incorrect recipients when replying')

        # Do: Bert replies through chatter (is a customer)
        msg3 = self.env['mail.thread'].message_post(author_id=self.partner_1.id, parent_id=msg1.id, subtype='mail.mt_comment')

        # Test: message recipients
        msg = self.env['mail.message'].browse(msg3.id)
        self.assertEqual(msg.partner_ids, self.user_employee.partner_id | self.env.user.partner_id,
                         'message_post: private discussion: incorrect recipients when replying')
        self.assertEqual(msg.needaction_partner_ids, self.user_employee.partner_id | self.env.user.partner_id,
                         'message_post: private discussion: incorrect notified recipients when replying')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_forward_parent_id(self):
        msg = self.test_pigs.sudo(self.user_employee).message_post(no_auto_thread=True, subtype='mail.mt_comment')
        self.assertNotIn(msg.model, msg.message_id)
        self.assertNotIn('-%d-' % msg.res_id, msg.message_id)
        self.assertIn('reply_to', msg.message_id)

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
        channel = self.env['mail.test'].search([('name', "=", msg_fw.subject)])
        self.assertEqual(len(channel), 1)
        self.assertEqual(msg_fw.model, 'mail.test')
        self.assertFalse(msg_fw.parent_id)
        self.assertTrue(msg_fw.res_id == channel.id)

        # tmp
        from odoo.addons.mail.tests.models.test_mail_models import MailTestAlias
        MailTestAlias._mail_flat_thread = False

        fw_msg_id = '<THIS.IS.A.FW.MESSAGE.2@bert.fr>'
        fw_message = MAIL_TEMPLATE.format(to='public@example.com',
                                          cc='',
                                          subject='FW: Re: 2',
                                          email_from='b.t@example.com',
                                          extra='In-Reply-To: %s' % msg.message_id,
                                          msg_id=fw_msg_id)
        self.env['mail.thread'].message_process(None, fw_message)
        msg_fw = self.env['mail.message'].search([('message_id', '=', fw_msg_id)])
        self.assertEqual(len(msg_fw), 1)
        channel = self.env['mail.test'].search([('name', "=", msg_fw.subject)])
        self.assertEqual(len(channel), 0)
        self.assertEqual(msg_fw.model, 'mail.test')
        self.assertFalse(msg_fw.parent_id)
        self.assertTrue(msg_fw.res_id == self.test_public.id)

        # re-tmp
        MailTestAlias._mail_flat_thread = True
