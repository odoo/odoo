# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.mail.tests.test_mail_base import TestMailBase

MAIL_TEMPLATE = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: {email_from}
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative;
    boundary="----=_Part_4200734_24778174.1344608186754"
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: {msg_id}
{extra}
------=_Part_4200734_24778174.1344608186754
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable

Please call me as soon as possible this afternoon!

--
Sylvie
------=_Part_4200734_24778174.1344608186754
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: quoted-printable

<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
 <head>=20
  <meta http-equiv=3D"Content-Type" content=3D"text/html; charset=3Dutf-8" />
 </head>=20
 <body style=3D"margin: 0; padding: 0; background: #ffffff;-webkit-text-size-adjust: 100%;">=20

  <p>Please call me as soon as possible this afternoon!</p>

  <p>--<br/>
     Sylvie
  <p>
 </body>
</html>
------=_Part_4200734_24778174.1344608186754--
"""

MAIL_TEMPLATE_PLAINTEXT = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: Sylvie Lelitre <sylvie.lelitre@agrolait.com>
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/plain
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: {msg_id}
{extra}

Please call me as soon as possible this afternoon!

--
Sylvie
"""


class TestMailgateway(TestMailBase):

    def test_00_message_process(self):
        """ Testing incoming emails processing. """
        cr, uid, user_raoul = self.cr, self.uid, self.user_raoul

        def format_and_process(template, to='groups@example.com, other@gmail.com', subject='Frogs',
                                extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                                msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                                model=None):
            self.assertEqual(self.mail_group.search(cr, uid, [('name', '=', subject)]), [])
            mail = template.format(to=to, subject=subject, extra=extra, email_from=email_from, msg_id=msg_id)
            self.mail_thread.message_process(cr, uid, model, mail)
            return self.mail_group.search(cr, uid, [('name', '=', subject)])

        # --------------------------------------------------
        # Data creation
        # --------------------------------------------------

        # groups@.. will cause the creation of new mail groups
        self.mail_group_model_id = self.ir_model.search(cr, uid, [('model', '=', 'mail.group')])[0]
        alias_id = self.mail_alias.create(cr, uid, {
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': self.mail_group_model_id})

        # --------------------------------------------------
        # Test1: new record creation
        # --------------------------------------------------

        # Do: incoming mail from an unknown partner on an alias creates a new mail_group "frogs"
        self._init_mock_build_email()
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other@gmail.com')
        sent_emails = self._build_email_kwargs_list
        # Test: one group created by mailgateway administrator
        self.assertEqual(len(frog_groups), 1, 'message_process: a new mail.group should have been created')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        res = self.mail_group.perm_read(cr, uid, [frog_group.id], details=False)
        self.assertEqual(res[0].get('create_uid'), uid,
                            'message_process: group should have been created by uid as alias_user__id is False on the alias')
        # Test: one message that is the incoming email
        self.assertEqual(len(frog_group.message_ids), 1,
                            'message_process: newly created group should have the incoming email in message_ids')
        msg = frog_group.message_ids[0]
        self.assertEqual('Frogs', msg.subject,
                            'message_process: newly created group should have the incoming email as first message')
        self.assertIn('Please call me as soon as possible this afternoon!', msg.body,
                            'message_process: newly created group should have the incoming email as first message')
        self.assertEqual('email', msg.type,
                            'message_process: newly created group should have an email as first message')
        self.assertEqual('Discussions', msg.subtype_id.name,
                            'message_process: newly created group should not have a log first message but an email')
        # Test: message: unknown email address -> message has email_from, not author_id
        self.assertFalse(msg.author_id,
                            'message_process: message on created group should not have an author_id')
        self.assertIn('test.sylvie.lelitre@agrolait.com', msg.email_from,
                            'message_process: message on created group should have an email_from')
        # Test: followers: nobody
        self.assertEqual(len(frog_group.message_follower_ids), 0, 'message_process: newly create group should not have any follower')
        # Test: sent emails: no-one
        self.assertEqual(len(sent_emails), 0,
                            'message_process: should create emails without any follower added')
        # Data: unlink group
        frog_group.unlink()

        # Do: incoming email from a known partner on an alias with known recipients, alias is owned by user that can create a group
        self.mail_alias.write(cr, uid, [alias_id], {'alias_user_id': self.user_raoul_id})
        p1id = self.res_partner.create(cr, uid, {'name': 'Sylvie Lelitre', 'email': 'test.sylvie.lelitre@agrolait.com'})
        p2id = self.res_partner.create(cr, uid, {'name': 'Other Poilvache', 'email': 'other@gmail.com'})
        self._init_mock_build_email()
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other@gmail.com')
        sent_emails = self._build_email_kwargs_list
        # Test: one group created by Raoul
        self.assertEqual(len(frog_groups), 1, 'message_process: a new mail.group should have been created')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        res = self.mail_group.perm_read(cr, uid, [frog_group.id], details=False)
        self.assertEqual(res[0].get('create_uid'), self.user_raoul_id,
                            'message_process: group should have been created by alias_user_id')
        # Test: one message that is the incoming email
        self.assertEqual(len(frog_group.message_ids), 1,
                            'message_process: newly created group should have the incoming email in message_ids')
        msg = frog_group.message_ids[0]
        # Test: message: unknown email address -> message has email_from, not author_id
        self.assertEqual(p1id, msg.author_id.id,
                            'message_process: message on created group should have Sylvie as author_id')
        self.assertIn('Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>', msg.email_from,
                            'message_process: message on created group should have have an email_from')
        # Test: author (not recipient and not raoul (as alias owner)) added as follower
        frog_follower_ids = set([p.id for p in frog_group.message_follower_ids])
        self.assertEqual(frog_follower_ids, set([p1id]),
                            'message_process: newly created group should have 1 follower (author, not creator, not recipients)')
        # Test: sent emails: no-one, no bounce effet
        self.assertEqual(len(sent_emails), 0,
                            'message_process: should not bounce incoming emails')
        # Data: unlink group
        frog_group.unlink()

        # Do: incoming email from a known partner that is also an user that can create a mail.group
        self.res_users.create(cr, uid, {'partner_id': p1id, 'login': 'sylvie', 'groups_id': [(6, 0, [self.group_employee_id])]})
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other@gmail.com')
        # Test: one group created by Raoul (or Sylvie maybe, if we implement it)
        self.assertEqual(len(frog_groups), 1, 'message_process: a new mail.group should have been created')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: one message that is the incoming email
        self.assertEqual(len(frog_group.message_ids), 1,
                            'message_process: newly created group should have the incoming email in message_ids')
        # Test: author (and not recipient) added as follower
        frog_follower_ids = set([p.id for p in frog_group.message_follower_ids])
        self.assertEqual(frog_follower_ids, set([p1id]),
                            'message_process: newly created group should have 1 follower (author, not creator, not recipients)')
        # Test: sent emails: no-one, no bounce effet
        self.assertEqual(len(sent_emails), 0,
                            'message_process: should not bounce incoming emails')

        # --------------------------------------------------
        # Test2: discussion update
        # --------------------------------------------------

        # Do: even with a wrong destination, a reply should end up in the correct thread
        frog_groups = format_and_process(MAIL_TEMPLATE, email_from='other@gmail.com',
                                            msg_id='<1198923581.41972151344608186760.JavaMail.diff1@agrolait.com>',
                                            to='erroneous@example.com>', subject='Re: news',
                                            extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>\n' % frog_group.id)
        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                            'message_process: reply on Frogs should not have created a new group with new subject')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        self.assertEqual(len(frog_groups), 1,
                            'message_process: reply on Frogs should not have created a duplicate group with old subject')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: one new message
        self.assertEqual(len(frog_group.message_ids), 2, 'message_process: group should contain 2 messages after reply')
        # Test: author (and not recipient) added as follower
        frog_follower_ids = set([p.id for p in frog_group.message_follower_ids])
        self.assertEqual(frog_follower_ids, set([p1id, p2id]),
                            'message_process: after reply, group should have 2 followers')

        # Do: due to some issue, same email goes back into the mailgateway
        frog_groups = format_and_process(MAIL_TEMPLATE, email_from='other@gmail.com',
                                            msg_id='<1198923581.41972151344608186760.JavaMail.diff1@agrolait.com>',
                                            subject='Re: news', extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>\n' % frog_group.id)
        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                            'message_process: reply on Frogs should not have created a new group with new subject')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        self.assertEqual(len(frog_groups), 1,
                            'message_process: reply on Frogs should not have created a duplicate group with old subject')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: no new message
        self.assertEqual(len(frog_group.message_ids), 2, 'message_process: message with already existing message_id should not have been duplicated')
        # Test: message_id is still unique
        msg_ids = self.mail_message.search(cr, uid, [('message_id', 'ilike', '<1198923581.41972151344608186760.JavaMail.diff1@agrolait.com>')])
        self.assertEqual(len(msg_ids), 1,
                            'message_process: message with already existing message_id should not have been duplicated')

        # --------------------------------------------------
        # Test3: email_from and partner finding
        # --------------------------------------------------

        # Data: extra partner with Raoul's email -> test the 'better author finding'
        extra_partner_id = self.res_partner.create(cr, uid, {'name': 'A-Raoul', 'email': 'test_raoul@email.com'})
        # extra_user_id = self.res_users.create(cr, uid, {'name': 'B-Raoul', 'email': self.user_raoul.email})
        # extra_user_pid = self.res_users.browse(cr, uid, extra_user_id).partner_id.id

        # Do: post a new message, with a known partner -> duplicate emails -> partner
        format_and_process(MAIL_TEMPLATE, email_from='Lombrik Lubrik <test_raoul@email.com>',
                                            to='erroneous@example.com>', subject='Re: news (2)',
                                            msg_id='<1198923581.41972151344608186760.JavaMail.new1@agrolait.com>',
                                            extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>\n' % frog_group.id)
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: author is A-Raoul (only existing)
        self.assertEqual(frog_group.message_ids[0].author_id.id, extra_partner_id,
                            'message_process: email_from -> author_id wrong')

        # Do: post a new message, with a known partner -> duplicate emails -> user
        frog_group.message_unsubscribe([extra_partner_id])
        raoul_email = self.user_raoul.email
        self.res_users.write(cr, uid, self.user_raoul_id, {'email': 'test_raoul@email.com'})
        format_and_process(MAIL_TEMPLATE, email_from='Lombrik Lubrik <test_raoul@email.com>',
                                            to='erroneous@example.com>', subject='Re: news (3)',
                                            msg_id='<1198923581.41972151344608186760.JavaMail.new2@agrolait.com>',
                                            extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>\n' % frog_group.id)
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: author is Raoul (user), not A-Raoul
        self.assertEqual(frog_group.message_ids[0].author_id.id, self.partner_raoul_id,
                            'message_process: email_from -> author_id wrong')

        # Do: post a new message, with a known partner -> duplicate emails -> partner because is follower
        frog_group.message_unsubscribe([self.partner_raoul_id])
        frog_group.message_subscribe([extra_partner_id])
        raoul_email = self.user_raoul.email
        self.res_users.write(cr, uid, self.user_raoul_id, {'email': 'test_raoul@email.com'})
        format_and_process(MAIL_TEMPLATE, email_from='Lombrik Lubrik <test_raoul@email.com>',
                                            to='erroneous@example.com>', subject='Re: news (3)',
                                            msg_id='<1198923581.41972151344608186760.JavaMail.new3@agrolait.com>',
                                            extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>\n' % frog_group.id)
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: author is Raoul (user), not A-Raoul
        self.assertEqual(frog_group.message_ids[0].author_id.id, extra_partner_id,
                            'message_process: email_from -> author_id wrong')

        self.res_users.write(cr, uid, self.user_raoul_id, {'email': raoul_email})

        # --------------------------------------------------
        # Test4: misc gateway features
        # --------------------------------------------------

        # Do: incoming email with model that does not accepts incoming emails must raise
        self.assertRaises(AssertionError,
                            format_and_process,
                            MAIL_TEMPLATE,
                            to='noone@example.com', subject='spam', extra='', model='res.country',
                            msg_id='<1198923581.41972151344608186760.JavaMail.new4@agrolait.com>')

        # Do: incoming email without model and without alias must raise
        self.assertRaises(AssertionError,
                            format_and_process,
                            MAIL_TEMPLATE,
                            to='noone@example.com', subject='spam', extra='',
                            msg_id='<1198923581.41972151344608186760.JavaMail.new5@agrolait.com>')

        # Do: incoming email with model that accepting incoming emails as fallback
        frog_groups = format_and_process(MAIL_TEMPLATE,
                                            to='noone@example.com',
                                            subject='Spammy', extra='', model='mail.group',
                                            msg_id='<1198923581.41972151344608186760.JavaMail.new6@agrolait.com>')
        self.assertEqual(len(frog_groups), 1,
                            'message_process: erroneous email but with a fallback model should have created a new mail.group')

        # Do: incoming email in plaintext should be stored as  html
        frog_groups = format_and_process(MAIL_TEMPLATE_PLAINTEXT,
                                            to='groups@example.com', subject='Frogs Return', extra='',
                                            msg_id='<deadcafe.1337@smtp.agrolait.com>')
        # Test: one group created with one message
        self.assertEqual(len(frog_groups), 1, 'message_process: a new mail.group should have been created')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        msg = frog_group.message_ids[0]
        # Test: plain text content should be wrapped and stored as html
        self.assertEqual(msg.body, '<pre>\nPlease call me as soon as possible this afternoon!\n\n--\nSylvie\n</pre>',
                            'message_process: plaintext incoming email incorrectly parsed')

    def test_10_thread_parent_resolution(self):
        """ Testing parent/child relationships are correctly established when processing incoming mails """
        cr, uid = self.cr, self.uid

        def format(template, to='Pretty Pigs <group+pigs@example.com>, other@gmail.com', subject='Re: 1',
                                extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                                msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
            return template.format(to=to, subject=subject, extra=extra, email_from=email_from, msg_id=msg_id)

        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        msg1 = group_pigs.message_post(body='My Body', subject='1')
        msg2 = group_pigs.message_post(body='My Body', subject='2')
        msg1, msg2 = self.mail_message.browse(cr, uid, [msg1, msg2])
        self.assertTrue(msg1.message_id, "message_process: new message should have a proper message_id")

        # Reply to msg1, make sure the reply is properly attached using the various reply identification mechanisms
        # 0. Direct alias match
        reply_msg1 = format(MAIL_TEMPLATE, to='Pretty Pigs <group+pigs@example.com>',
                                extra='In-Reply-To: %s' % msg1.message_id,
                                msg_id='<1198923581.41972151344608186760.JavaMail.2@agrolait.com>')
        self.mail_group.message_process(cr, uid, None, reply_msg1)

        # 1. In-Reply-To header
        reply_msg2 = format(MAIL_TEMPLATE, to='erroneous@example.com',
                                extra='In-Reply-To: %s' % msg1.message_id,
                                msg_id='<1198923581.41972151344608186760.JavaMail.3@agrolait.com>')
        self.mail_group.message_process(cr, uid, None, reply_msg2)

        # 2. References header
        reply_msg3 = format(MAIL_TEMPLATE, to='erroneous@example.com',
                                extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % msg1.message_id,
                                msg_id='<1198923581.41972151344608186760.JavaMail.4@agrolait.com>')
        self.mail_group.message_process(cr, uid, None, reply_msg3)

        # 3. Subject contains [<ID>] + model passed to message+process -> only attached to group, but not to mail (not in msg1.child_ids)
        reply_msg4 = format(MAIL_TEMPLATE, to='erroneous@example.com',
                                extra='', subject='Re: [%s] 1' % self.group_pigs_id,
                                msg_id='<1198923581.41972151344608186760.JavaMail.5@agrolait.com>')
        self.mail_group.message_process(cr, uid, 'mail.group', reply_msg4)

        group_pigs.refresh()
        msg1.refresh()
        self.assertEqual(6, len(group_pigs.message_ids), 'message_process: group should contain 6 messages')
        self.assertEqual(3, len(msg1.child_ids), 'message_process: msg1 should have 3 children now')

    def test_20_private_discussion(self):
        """ Testing private discussion between partners. """
        cr, uid = self.cr, self.uid

        # Do: Raoul writes to Bert and Administrator, with a thread_model in context that should not be taken into account
        msg1_pids = [self.partner_admin_id, self.partner_bert_id]
        msg1_id = self.mail_thread.message_post(cr, self.user_raoul_id, False,
                        partner_ids=msg1_pids,
                        subtype='mail.mt_comment',
                        context={'thread_model': 'mail.group'})

        # Test: message recipients
        msg = self.mail_message.browse(cr, uid, msg1_id)
        msg_pids = [p.id for p in msg.partner_ids]
        msg_nids = [p.id for p in msg.notified_partner_ids]
        test_pids = msg1_pids
        test_nids = msg1_pids
        self.assertEqual(set(msg_pids), set(test_pids),
                        'message_post: private discussion: incorrect recipients')
        self.assertEqual(set(msg_nids), set(test_nids),
                        'message_post: private discussion: incorrect notified recipients')
        self.assertEqual(msg.model, False,
                        'message_post: private discussion: context key "thread_model" not correctly ignored when having no res_id')

        # Do: Bert replies through mailgateway (is a customer)
        msg2_id = self.mail_thread.message_post(cr, uid, False,
                        author_id=self.partner_bert_id,
                        parent_id=msg1_id, subtype='mail.mt_comment')

        # Test: message recipients
        msg = self.mail_message.browse(cr, uid, msg2_id)
        msg_pids = [p.id for p in msg.partner_ids]
        msg_nids = [p.id for p in msg.notified_partner_ids]
        test_pids = [self.partner_admin_id, self.partner_raoul_id]
        test_nids = test_pids
        self.assertEqual(set(msg_pids), set(test_pids),
                        'message_post: private discussion: incorrect recipients when replying')
        self.assertEqual(set(msg_nids), set(test_nids),
                        'message_post: private discussion: incorrect notified recipients when replying')

        # Do: Administrator replies
        msg3_id = self.mail_thread.message_post(cr, uid, False,
                        parent_id=msg2_id, subtype='mail.mt_comment')

        # Test: message recipients
        msg = self.mail_message.browse(cr, uid, msg3_id)
        msg_pids = [p.id for p in msg.partner_ids]
        msg_nids = [p.id for p in msg.notified_partner_ids]
        test_pids = [self.partner_bert_id, self.partner_raoul_id]
        test_nids = test_pids
        self.assertEqual(set(msg_pids), set(test_pids),
                        'message_post: private discussion: incorrect recipients when replying')
        self.assertEqual(set(msg_nids), set(test_nids),
                        'message_post: private discussion: incorrect notified recipients when replying')
