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

from .common import TestMail
from openerp.tools import mute_logger
import socket

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
From: Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>
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

MAIL_MULTIPART_MIXED = """Return-Path: <ignasse.carambar@gmail.com>
X-Original-To: raoul@grosbedon.fr
Delivered-To: raoul@grosbedon.fr
Received: by mail1.grosbedon.com (Postfix, from userid 10002)
    id E8166BFACA; Fri, 23 Aug 2013 13:18:01 +0200 (CEST)
X-Spam-Checker-Version: SpamAssassin 3.3.1 (2010-03-16) on mail1.grosbedon.com
X-Spam-Level: 
X-Spam-Status: No, score=-2.6 required=5.0 tests=BAYES_00,FREEMAIL_FROM,
    HTML_MESSAGE,RCVD_IN_DNSWL_LOW autolearn=unavailable version=3.3.1
Received: from mail-ie0-f173.google.com (mail-ie0-f173.google.com [209.85.223.173])
    by mail1.grosbedon.com (Postfix) with ESMTPS id 9BBD7BFAAA
    for <raoul@openerp.fr>; Fri, 23 Aug 2013 13:17:55 +0200 (CEST)
Received: by mail-ie0-f173.google.com with SMTP id qd12so575130ieb.4
        for <raoul@grosbedon.fr>; Fri, 23 Aug 2013 04:17:54 -0700 (PDT)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=gmail.com; s=20120113;
        h=mime-version:date:message-id:subject:from:to:content-type;
        bh=dMNHV52EC7GAa7+9a9tqwT9joy9z+1950J/3A6/M/hU=;
        b=DGuv0VjegdSrEe36ADC8XZ9Inrb3Iu+3/52Bm+caltddXFH9yewTr0JkCRQaJgMwG9
         qXTQgP8qu/VFEbCh6scu5ZgU1hknzlNCYr3LT+Ih7dAZVUEHUJdwjzUU1LFV95G2RaCd
         /Lwff6CibuUvrA+0CBO7IRKW0Sn5j0mukYu8dbaKsm6ou6HqS8Nuj85fcXJfHSHp6Y9u
         dmE8jBh3fHCHF/nAvU+8aBNSIzl1FGfiBYb2jCoapIuVFitKR4q5cuoodpkH9XqqtOdH
         DG+YjEyi8L7uvdOfN16eMr7hfUkQei1yQgvGu9/5kXoHg9+Gx6VsZIycn4zoaXTV3Nhn
         nu4g==
MIME-Version: 1.0
X-Received: by 10.50.124.65 with SMTP id mg1mr1144467igb.43.1377256674216;
 Fri, 23 Aug 2013 04:17:54 -0700 (PDT)
Received: by 10.43.99.71 with HTTP; Fri, 23 Aug 2013 04:17:54 -0700 (PDT)
Date: Fri, 23 Aug 2013 13:17:54 +0200
Message-ID: <CAP76m_V4BY2F7DWHzwfjteyhW8L2LJswVshtmtVym+LUJ=rASQ@mail.gmail.com>
Subject: Test mail multipart/mixed
From: =?ISO-8859-1?Q?Raoul Grosbedon=E9e?= <ignasse.carambar@gmail.com>
To: Followers of ASUSTeK-Joseph-Walters <raoul@grosbedon.fr>
Content-Type: multipart/mixed; boundary=089e01536c4ed4d17204e49b8e96

--089e01536c4ed4d17204e49b8e96
Content-Type: multipart/alternative; boundary=089e01536c4ed4d16d04e49b8e94

--089e01536c4ed4d16d04e49b8e94
Content-Type: text/plain; charset=ISO-8859-1

Should create a multipart/mixed: from gmail, *bold*, with attachment.

-- 
Marcel Boitempoils.

--089e01536c4ed4d16d04e49b8e94
Content-Type: text/html; charset=ISO-8859-1

<div dir="ltr">Should create a multipart/mixed: from gmail, <b>bold</b>, with attachment.<br clear="all"><div><br></div>-- <br>Marcel Boitempoils.</div>

--089e01536c4ed4d16d04e49b8e94--
--089e01536c4ed4d17204e49b8e96
Content-Type: text/plain; charset=US-ASCII; name="test.txt"
Content-Disposition: attachment; filename="test.txt"
Content-Transfer-Encoding: base64
X-Attachment-Id: f_hkpb27k00

dGVzdAo=
--089e01536c4ed4d17204e49b8e96--"""

MAIL_MULTIPART_MIXED_TWO = """X-Original-To: raoul@grosbedon.fr
Delivered-To: raoul@grosbedon.fr
Received: by mail1.grosbedon.com (Postfix, from userid 10002)
    id E8166BFACA; Fri, 23 Aug 2013 13:18:01 +0200 (CEST)
From: "Bruce Wayne" <bruce@wayneenterprises.com>
Content-Type: multipart/alternative;
 boundary="Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227"
Message-Id: <6BB1FAB2-2104-438E-9447-07AE2C8C4A92@sexample.com>
Mime-Version: 1.0 (Mac OS X Mail 7.3 \(1878.6\))

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227
Content-Transfer-Encoding: 7bit
Content-Type: text/plain;
    charset=us-ascii

First and second part

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227
Content-Type: multipart/mixed;
 boundary="Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F"

--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F
Content-Transfer-Encoding: 7bit
Content-Type: text/html;
    charset=us-ascii

<html><head></head><body>First part</body></html>

--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F
Content-Disposition: inline;
    filename=thetruth.pdf
Content-Type: application/pdf;
    name="thetruth.pdf"
Content-Transfer-Encoding: base64

SSBhbSB0aGUgQmF0TWFuCg==

--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F
Content-Transfer-Encoding: 7bit
Content-Type: text/html;
    charset=us-ascii

<html><head></head><body>Second part</body></html>
--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F--

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227--
"""

class TestMailgateway(TestMail):

    def test_00_message_parse(self):
        """ Testing incoming emails parsing """
        cr, uid = self.cr, self.uid

        res = self.mail_thread.message_parse(cr, uid, MAIL_TEMPLATE_PLAINTEXT)
        self.assertIn('Please call me as soon as possible this afternoon!', res.get('body', ''),
                      'message_parse: missing text in text/plain body after parsing')

        res = self.mail_thread.message_parse(cr, uid, MAIL_TEMPLATE)
        self.assertIn('<p>Please call me as soon as possible this afternoon!</p>', res.get('body', ''),
                      'message_parse: missing html in multipart/alternative body after parsing')

        res = self.mail_thread.message_parse(cr, uid, MAIL_MULTIPART_MIXED)
        self.assertNotIn('Should create a multipart/mixed: from gmail, *bold*, with attachment', res.get('body', ''),
                         'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn('<div dir="ltr">Should create a multipart/mixed: from gmail, <b>bold</b>, with attachment.<br clear="all"><div><br></div>', res.get('body', ''),
                      'message_parse: html version should be in body after parsing multipart/mixed')

        res = self.mail_thread.message_parse(cr, uid, MAIL_MULTIPART_MIXED_TWO)
        self.assertNotIn('First and second part', res.get('body', ''),
                         'message_parse: text version should not be in body after parsing multipart/mixed')
        self.assertIn('First part', res.get('body', ''),
                      'message_parse: first part of the html version should be in body after parsing multipart/mixed')
        self.assertIn('Second part', res.get('body', ''),
                      'message_parse: second part of the html version should be in body after parsing multipart/mixed')

    @mute_logger('openerp.addons.mail.mail_thread', 'openerp.models')
    def test_10_message_process(self):
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
            'alias_model_id': self.mail_group_model_id,
            'alias_parent_model_id': self.mail_group_model_id,
            'alias_parent_thread_id': self.group_pigs_id,
            'alias_contact': 'everyone'})

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
        res = self.mail_group.get_metadata(cr, uid, [frog_group.id])[0].get('create_uid') or [None]
        self.assertEqual(res[0], uid,
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

        # Do: incoming email from an unknown partner on a Partners only alias -> bounce
        self._init_mock_build_email()
        self.mail_alias.write(cr, uid, [alias_id], {'alias_contact': 'partners'})
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other2@gmail.com')
        # Test: no group created
        self.assertTrue(len(frog_groups) == 0)
        # Test: email bounced
        sent_emails = self._build_email_kwargs_list
        self.assertEqual(len(sent_emails), 1,
                         'message_process: incoming email on Partners alias should send a bounce email')
        self.assertIn('Frogs', sent_emails[0].get('subject'),
                      'message_process: bounce email on Partners alias should contain the original subject')
        self.assertIn('test.sylvie.lelitre@agrolait.com', sent_emails[0].get('email_to'),
                      'message_process: bounce email on Partners alias should have original email sender as recipient')

        # Do: incoming email from an unknown partner on a Followers only alias -> bounce
        self._init_mock_build_email()
        self.mail_alias.write(cr, uid, [alias_id], {'alias_contact': 'followers'})
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other3@gmail.com')
        # Test: no group created
        self.assertTrue(len(frog_groups) == 0)
        # Test: email bounced
        sent_emails = self._build_email_kwargs_list
        self.assertEqual(len(sent_emails), 1,
                         'message_process: incoming email on Followers alias should send a bounce email')
        self.assertIn('Frogs', sent_emails[0].get('subject'),
                      'message_process: bounce email on Followers alias should contain the original subject')
        self.assertIn('test.sylvie.lelitre@agrolait.com', sent_emails[0].get('email_to'),
                      'message_process: bounce email on Followers alias should have original email sender as recipient')

        # Do: incoming email from a known partner on a Partners alias -> ok (+ test on alias.user_id)
        self.mail_alias.write(cr, uid, [alias_id], {'alias_user_id': self.user_raoul_id, 'alias_contact': 'partners'})
        p1id = self.res_partner.create(cr, uid, {'name': 'Sylvie Lelitre', 'email': 'test.sylvie.lelitre@agrolait.com'})
        p2id = self.res_partner.create(cr, uid, {'name': 'Other Poilvache', 'email': 'other4@gmail.com'})
        self._init_mock_build_email()
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other4@gmail.com')
        sent_emails = self._build_email_kwargs_list
        # Test: one group created by Raoul
        self.assertEqual(len(frog_groups), 1, 'message_process: a new mail.group should have been created')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        res = self.mail_group.get_metadata(cr, uid, [frog_group.id])[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.user_raoul_id,
                         'message_process: group should have been created by alias_user_id')
        # Test: one message that is the incoming email
        self.assertEqual(len(frog_group.message_ids), 1,
                         'message_process: newly created group should have the incoming email in message_ids')
        msg = frog_group.message_ids[0]
        # Test: message: author found
        self.assertEqual(p1id, msg.author_id.id,
                         'message_process: message on created group should have Sylvie as author_id')
        self.assertIn('Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>', msg.email_from,
                      'message_process: message on created group should have have an email_from')
        # Test: author (not recipient and not Raoul (as alias owner)) added as follower
        frog_follower_ids = set([p.id for p in frog_group.message_follower_ids])
        self.assertEqual(frog_follower_ids, set([p1id]),
                         'message_process: newly created group should have 1 follower (author, not creator, not recipients)')
        # Test: sent emails: no-one, no bounce effet
        sent_emails = self._build_email_kwargs_list
        self.assertEqual(len(sent_emails), 0,
                         'message_process: should not bounce incoming emails')
        # Data: unlink group
        frog_group.unlink()

        # Do: incoming email from a not follower Partner on a Followers only alias -> bounce
        self._init_mock_build_email()
        self.mail_alias.write(cr, uid, [alias_id], {'alias_user_id': False, 'alias_contact': 'followers'})
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other5@gmail.com')
        # Test: no group created
        self.assertTrue(len(frog_groups) == 0)
        # Test: email bounced
        sent_emails = self._build_email_kwargs_list
        self.assertEqual(len(sent_emails), 1,
                         'message_process: incoming email on Partners alias should send a bounce email')

        # Do: incoming email from a parent document follower on a Followers only alias -> ok
        self._init_mock_build_email()
        self.mail_group.message_subscribe(cr, uid, [self.group_pigs_id], [p1id])
        frog_groups = format_and_process(MAIL_TEMPLATE, to='groups@example.com, other6@gmail.com')
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
        sent_emails = self._build_email_kwargs_list
        self.assertEqual(len(sent_emails), 0,
                         'message_process: should not bounce incoming emails')

        # --------------------------------------------------
        # Test2: update-like alias
        # --------------------------------------------------

        # Do: Pigs alias is restricted, should bounce
        self._init_mock_build_email()
        self.mail_group.write(cr, uid, [frog_group.id], {'alias_name': 'frogs', 'alias_contact': 'followers', 'alias_force_thread_id': frog_group.id})
        frog_groups = format_and_process(MAIL_TEMPLATE, email_from='other4@gmail.com',
                                         msg_id='<1198923581.41972151344608186760.JavaMail.diff1@agrolait.com>',
                                         to='frogs@example.com>', subject='Re: news')
        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        self.assertEqual(len(frog_groups), 1,
                         'message_process: reply on Frogs should not have created a duplicate group with old subject')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: email bounced
        sent_emails = self._build_email_kwargs_list
        self.assertEqual(len(sent_emails), 1,
                         'message_process: incoming email on Followers alias should send a bounce email')
        self.assertIn('Re: news', sent_emails[0].get('subject'),
                      'message_process: bounce email on Followers alias should contain the original subject')

        # Do: Pigs alias is restricted, should accept Followers
        self._init_mock_build_email()
        self.mail_group.message_subscribe(cr, uid, [frog_group.id], [p2id])
        frog_groups = format_and_process(MAIL_TEMPLATE, email_from='other4@gmail.com',
                                         msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>',
                                         to='frogs@example.com>', subject='Re: cats')
        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        self.assertEqual(len(frog_groups), 1,
                         'message_process: reply on Frogs should not have created a duplicate group with old subject')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: one new message
        self.assertEqual(len(frog_group.message_ids), 2, 'message_process: group should contain 2 messages after reply')
        # Test: sent emails: 1 (Sylvie copy of the incoming email, but no bounce)
        sent_emails = self._build_email_kwargs_list
        self.assertEqual(len(sent_emails), 1,
                         'message_process: one email should have been generated')
        self.assertIn('test.sylvie.lelitre@agrolait.com', sent_emails[0].get('email_to')[0],
                      'message_process: email should be sent to Sylvie')
        self.mail_group.message_unsubscribe(cr, uid, [frog_group.id], [p2id])

        # --------------------------------------------------
        # Test3: discussion and replies
        # --------------------------------------------------

        # Do: even with a wrong destination, a reply should end up in the correct thread
        frog_groups = format_and_process(MAIL_TEMPLATE, email_from='other4@gmail.com',
                                         msg_id='<1198923581.41972151344608186760.JavaMail.diff1@agrolait.com>',
                                         to='erroneous@example.com>', subject='Re: news',
                                         extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>\n')
        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        self.assertEqual(len(frog_groups), 1,
                         'message_process: reply on Frogs should not have created a duplicate group with old subject')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: one new message
        self.assertEqual(len(frog_group.message_ids), 3, 'message_process: group should contain 3 messages after reply')
        # Test: author (and not recipient) added as follower
        frog_follower_ids = set([p.id for p in frog_group.message_follower_ids])
        self.assertEqual(frog_follower_ids, set([p1id, p2id]),
                         'message_process: after reply, group should have 2 followers')

        # Do: incoming email with ref holding model / res_id but that does not match any message in the thread: must raise since OpenERP saas-3
        self.assertRaises(ValueError,
                          format_and_process,
                          MAIL_TEMPLATE, email_from='other5@gmail.com',
                          to='noone@example.com', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>' % frog_group.id,
                          msg_id='<1.1.JavaMail.new@agrolait.com>')

        # When 6.1 messages are present, compat mode is available
        # Create a fake 6.1 message
        tmp_msg_id = self.mail_message.create(cr, uid, {'model': 'mail.group', 'res_id': frog_group.id})
        self.mail_message.write(cr, uid, [tmp_msg_id], {'message_id': False})
        # Do: compat mode accepts partial-matching emails
        frog_groups = format_and_process(MAIL_TEMPLATE, email_from='other5@gmail.com',
                                         msg_id='<1.2.JavaMail.new@agrolait.com>',
                                         to='noone@example.com>', subject='spam',
                                         extra='In-Reply-To: <12321321-openerp-%d-mail.group@%s>' % (frog_group.id, socket.gethostname()))
        self.mail_message.unlink(cr, uid, [tmp_msg_id])
        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        self.assertEqual(len(frog_groups), 1,
                         'message_process: reply on Frogs should not have created a duplicate group with old subject')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: one new message
        self.assertEqual(len(frog_group.message_ids), 4, 'message_process: group should contain 4 messages after reply')

        # 6.1 compat mode should not work if hostname does not match!
        tmp_msg_id = self.mail_message.create(cr, uid, {'model': 'mail.group', 'res_id': frog_group.id})
        self.mail_message.write(cr, uid, [tmp_msg_id], {'message_id': False})
        self.assertRaises(ValueError,
                          format_and_process,
                          MAIL_TEMPLATE, email_from='other5@gmail.com',
                          msg_id='<1.3.JavaMail.new@agrolait.com>',
                          to='noone@example.com>', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.group@neighbor.com>' % frog_group.id)
        self.mail_message.unlink(cr, uid, [tmp_msg_id])


        # Do: due to some issue, same email goes back into the mailgateway
        frog_groups = format_and_process(MAIL_TEMPLATE, email_from='other4@gmail.com',
                                         msg_id='<1198923581.41972151344608186760.JavaMail.diff1@agrolait.com>',
                                         subject='Re: news', extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>\n')
        # Test: no group 'Re: news' created, still only 1 Frogs group
        self.assertEqual(len(frog_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        self.assertEqual(len(frog_groups), 1,
                         'message_process: reply on Frogs should not have created a duplicate group with old subject')
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: no new message
        self.assertEqual(len(frog_group.message_ids), 4, 'message_process: message with already existing message_id should not have been duplicated')
        # Test: message_id is still unique
        msg_ids = self.mail_message.search(cr, uid, [('message_id', 'ilike', '<1198923581.41972151344608186760.JavaMail.diff1@agrolait.com>')])
        self.assertEqual(len(msg_ids), 1,
                         'message_process: message with already existing message_id should not have been duplicated')

        # --------------------------------------------------
        # Test4: email_from and partner finding
        # --------------------------------------------------

        # Data: extra partner with Raoul's email -> test the 'better author finding'
        extra_partner_id = self.res_partner.create(cr, uid, {'name': 'A-Raoul', 'email': 'test_raoul@email.com'})

        # Do: post a new message, with a known partner -> duplicate emails -> partner
        format_and_process(MAIL_TEMPLATE, email_from='Lombrik Lubrik <test_raoul@email.com>',
                           subject='Re: news (2)',
                           msg_id='<1198923581.41972151344608186760.JavaMail.new1@agrolait.com>',
                           extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: author is A-Raoul (only existing)
        self.assertEqual(frog_group.message_ids[0].author_id.id, extra_partner_id,
                         'message_process: email_from -> author_id wrong')

        # Do: post a new message with a non-existant email that is a substring of a partner email
        format_and_process(MAIL_TEMPLATE, email_from='Not really Lombrik Lubrik <oul@email.com>',
                           subject='Re: news (2)',
                           msg_id='<zzzbbbaaaa@agrolait.com>',
                           extra='In-Reply-To: <1198923581.41972151344608186760.JavaMail@agrolait.com>\n')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: author must not be set, otherwise the system is confusing different users
        self.assertFalse(frog_group.message_ids[0].author_id, 'message_process: email_from -> mismatching author_id')

        # Do: post a new message, with a known partner -> duplicate emails -> user
        frog_group.message_unsubscribe([extra_partner_id])
        self.res_users.write(cr, uid, self.user_raoul_id, {'email': 'test_raoul@email.com'})
        format_and_process(MAIL_TEMPLATE, email_from='Lombrik Lubrik <test_raoul@email.com>',
                           to='groups@example.com', subject='Re: news (3)',
                           msg_id='<1198923581.41972151344608186760.JavaMail.new2@agrolait.com>',
                           extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')
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
                           to='groups@example.com', subject='Re: news (3)',
                           msg_id='<1198923581.41972151344608186760.JavaMail.new3@agrolait.com>',
                           extra='In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'Frogs')])
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        # Test: author is Raoul (user), not A-Raoul
        self.assertEqual(frog_group.message_ids[0].author_id.id, extra_partner_id,
                         'message_process: email_from -> author_id wrong')

        self.res_users.write(cr, uid, self.user_raoul_id, {'email': raoul_email})

        # --------------------------------------------------
        # Test5: misc gateway features
        # --------------------------------------------------

        # Do: incoming email with model that does not accepts incoming emails must raise
        self.assertRaises(ValueError,
                          format_and_process,
                          MAIL_TEMPLATE,
                          to='noone@example.com', subject='spam', extra='', model='res.country',
                          msg_id='<1198923581.41972151344608186760.JavaMail.new4@agrolait.com>')

        # Do: incoming email without model and without alias must raise
        self.assertRaises(ValueError,
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
        self.assertIn('<pre>\nPlease call me as soon as possible this afternoon!\n\n--\nSylvie\n</pre>', msg.body,
                      'message_process: plaintext incoming email incorrectly parsed')

    @mute_logger('openerp.addons.mail.mail_thread', 'openerp.models')
    def test_20_thread_parent_resolution(self):
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
                            extra='In-Reply-To:\r\n\t%s' % msg1.message_id,
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

    def test_30_private_discussion(self):
        """ Testing private discussion between partners. """
        cr, uid = self.cr, self.uid

        def format(template, to='Pretty Pigs <group+pigs@example.com>, other@gmail.com', subject='Re: 1',
                                extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                                msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
            return template.format(to=to, subject=subject, extra=extra, email_from=email_from, msg_id=msg_id)

        # Do: Raoul writes to Bert and Administrator, with a thread_model in context that should not be taken into account
        msg1_pids = [self.partner_admin_id, self.partner_bert_id]
        msg1_id = self.mail_thread.message_post(
            cr, self.user_raoul_id, False,
            partner_ids=msg1_pids,
            subtype='mail.mt_comment',
            context={'thread_model': 'mail.group'}
        )

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
        # Test: message-id
        self.assertIn('openerp-private', msg.message_id,
                      'message_post: private discussion: message-id should contain the private keyword')

        # Do: Bert replies through mailgateway (is a customer)
        reply_message = format(MAIL_TEMPLATE, to='not_important@mydomain.com',
                               email_from='bert@bert.fr',
                               extra='In-Reply-To: %s' % msg.message_id,
                               msg_id='<test30.JavaMail.0@agrolait.com>')
        self.mail_thread.message_process(cr, uid, None, reply_message)

        # Test: last mail_message created
        msg2_id = self.mail_message.search(cr, uid, [], limit=1)[0]

        # Test: message recipients
        msg = self.mail_message.browse(cr, uid, msg2_id)
        msg_pids = [p.id for p in msg.partner_ids]
        msg_nids = [p.id for p in msg.notified_partner_ids]
        test_pids = [self.partner_admin_id, self.partner_raoul_id]
        test_nids = test_pids
        self.assertEqual(msg.author_id.id, self.partner_bert_id,
                         'message_post: private discussion: wrong author through mailgatewya based on email')
        self.assertEqual(set(msg_pids), set(test_pids),
                         'message_post: private discussion: incorrect recipients when replying')
        self.assertEqual(set(msg_nids), set(test_nids),
                         'message_post: private discussion: incorrect notified recipients when replying')

        # Do: Bert replies through chatter (is a customer)
        msg3_id = self.mail_thread.message_post(
            cr, uid, False,
            author_id=self.partner_bert_id,
            parent_id=msg1_id, subtype='mail.mt_comment')

        # Test: message recipients
        msg = self.mail_message.browse(cr, uid, msg3_id)
        msg_pids = [p.id for p in msg.partner_ids]
        msg_nids = [p.id for p in msg.notified_partner_ids]
        test_pids = [self.partner_admin_id, self.partner_raoul_id]
        test_nids = test_pids
        self.assertEqual(set(msg_pids), set(test_pids),
                         'message_post: private discussion: incorrect recipients when replying')
        self.assertEqual(set(msg_nids), set(test_nids),
                         'message_post: private discussion: incorrect notified recipients when replying')

        # Do: Administrator replies
        msg3_id = self.mail_thread.message_post(cr, uid, False, parent_id=msg3_id, subtype='mail.mt_comment')

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

        # Do bert forward it to an alias
        mail_group_model_id = self.ir_model.search(cr, uid, [('model', '=', 'mail.group')])[0]
        self.mail_alias.create(cr, uid, {
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': mail_group_model_id,
            'alias_parent_model_id': mail_group_model_id,
            'alias_parent_thread_id': self.group_pigs_id,
            'alias_contact': 'everyone'})

        msg = self.mail_message.browse(cr, uid, msg1_id)
        # forward it to a new thread AND an existing thread
        for i, to in enumerate(['groups', 'group+pigs']):
            fw_msg_id = '<THIS.IS.A.FW.MESSAGE.%d@bert.fr>' % (i,)
            fw_message = format(MAIL_TEMPLATE, to='%s@whatever.tld' % (to,),
                                subject='FW: Re: 1',
                                email_from='bert@bert.fr',
                                extra='References: %s' % msg.message_id,
                                msg_id=fw_msg_id)
            self.mail_thread.message_process(cr, uid, None, fw_message)

            msg_ids = self.mail_message.search(cr, uid, [('message_id', '=', fw_msg_id)])
            self.assertEqual(len(msg_ids), 1)
            msg_fw = self.mail_message.browse(cr, uid, msg_ids[0])

            self.assertEqual(msg_fw.model, 'mail.group')
            self.assertFalse(msg_fw.parent_id)
