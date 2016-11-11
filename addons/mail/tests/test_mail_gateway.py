# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import socket

from odoo.addons.mail.tests.common import TestMail
from odoo.tools import mute_logger


MAIL_TEMPLATE = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
cc: {cc}
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


MAIL_MULTIPART_IMAGE = """X-Original-To: raoul@example.com
Delivered-To: micheline@example.com
Received: by mail1.example.com (Postfix, from userid 99999)
    id 9DFB7BF509; Thu, 17 Dec 2015 15:22:56 +0100 (CET)
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on mail1.example.com
X-Spam-Level: *
X-Spam-Status: No, score=1.1 required=5.0 tests=FREEMAIL_FROM,
    HTML_IMAGE_ONLY_08,HTML_MESSAGE,RCVD_IN_DNSWL_LOW,RCVD_IN_MSPIKE_H3,
    RCVD_IN_MSPIKE_WL,T_DKIM_INVALID autolearn=no autolearn_force=no version=3.4.0
Received: from mail-lf0-f44.example.com (mail-lf0-f44.example.com [209.85.215.44])
    by mail1.example.com (Postfix) with ESMTPS id 1D80DBF509
    for <micheline@example.com>; Thu, 17 Dec 2015 15:22:56 +0100 (CET)
Authentication-Results: mail1.example.com; dkim=pass
    reason="2048-bit key; unprotected key"
    header.d=example.com header.i=@example.com header.b=kUkTIIlt;
    dkim-adsp=pass; dkim-atps=neutral
Received: by mail-lf0-f44.example.com with SMTP id z124so47959461lfa.3
        for <micheline@example.com>; Thu, 17 Dec 2015 06:22:56 -0800 (PST)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=example.com; s=20120113;
        h=mime-version:date:message-id:subject:from:to:content-type;
        bh=GdrEuMrz6vxo/Z/F+mJVho/1wSe6hbxLx2SsP8tihzw=;
        b=kUkTIIlt6fe4dftKHPNBkdHU2rO052o684R0e2bqH7roGUQFb78scYE+kqX0wo1zlk
         zhKPVBR1TqTsYlqcHu+D3aUzai7L/Q5m40sSGn7uYGkZJ6m1TwrWNqVIgTZibarqvy94
         NWhrjjK9gqd8segQdSjCgTipNSZME4bJCzPyBg/D5mqe07FPBJBGoF9SmIzEBhYeqLj1
         GrXjb/D8J11aOyzmVvyt+bT+oeLUJI8E7qO5g2eQkMncyu+TyIXaRofOOBA14NhQ+0nS
         w5O9rzzqkKuJEG4U2TJ2Vi2nl2tHJW2QPfTtFgcCzGxQ0+5n88OVlbGTLnhEIJ/SYpem
         O5EA==
MIME-Version: 1.0
X-Received: by 10.25.167.197 with SMTP id q188mr22222517lfe.129.1450362175493;
 Thu, 17 Dec 2015 06:22:55 -0800 (PST)
Received: by 10.25.209.145 with HTTP; Thu, 17 Dec 2015 06:22:55 -0800 (PST)
Date: Thu, 17 Dec 2015 15:22:55 +0100
Message-ID: <CAP76m_UB=aLqWEFccnq86AhkpwRB3aZoGL9vMffX7co3YEro_A@mail.gmail.com>
Subject: {subject}
From: =?UTF-8?Q?Thibault_Delavall=C3=A9e?= <raoul@example.com>
To: {to}
Content-Type: multipart/related; boundary=001a11416b9e9b229a05272b7052

--001a11416b9e9b229a05272b7052
Content-Type: multipart/alternative; boundary=001a11416b9e9b229805272b7051

--001a11416b9e9b229805272b7051
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: quoted-printable

Premi=C3=A8re image, orang=C3=A9e.

[image: Inline image 1]

Seconde image, rosa=C3=A7=C3=A9e.

[image: Inline image 2]

Troisi=C3=A8me image, verte!=C2=B5

[image: Inline image 3]

J'esp=C3=A8re que tout se passera bien.
--=20
Thibault Delavall=C3=A9e

--001a11416b9e9b229805272b7051
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: quoted-printable

<div dir=3D"ltr"><div>Premi=C3=A8re image, orang=C3=A9e.</div><div><br></di=
v><div><img src=3D"cid:ii_151b519fc025fdd3" alt=3D"Inline image 1" width=3D=
"2" height=3D"2"><br></div><div><br></div><div>Seconde image, rosa=C3=A7=C3=
=A9e.</div><div><br></div><div><img src=3D"cid:ii_151b51a290ed6a91" alt=3D"=
Inline image 2" width=3D"2" height=3D"2"></div><div><br></div><div>Troisi=
=C3=A8me image, verte!=C2=B5</div><div><br></div><div><img src=3D"cid:ii_15=
1b51a37e5eb7a6" alt=3D"Inline image 3" width=3D"10" height=3D"10"><br></div=
><div><br></div><div>J&#39;esp=C3=A8re que tout se passera bien.</div>-- <b=
r><div class=3D"gmail_signature">Thibault Delavall=C3=A9e</div>
</div>

--001a11416b9e9b229805272b7051--
--001a11416b9e9b229a05272b7052
Content-Type: image/gif; name="=?UTF-8?B?b3JhbmfDqWUuZ2lm?="
Content-Disposition: inline; filename="=?UTF-8?B?b3JhbmfDqWUuZ2lm?="
Content-Transfer-Encoding: base64
Content-ID: <ii_151b519fc025fdd3>
X-Attachment-Id: ii_151b519fc025fdd3

R0lGODdhAgACALMAAAAAAP///wAAAP//AP8AAP+AAAD/AAAAAAAA//8A/wAAAAAAAAAAAAAAAAAA
AAAAACwAAAAAAgACAAAEA7DIEgA7
--001a11416b9e9b229a05272b7052
Content-Type: image/gif; name="=?UTF-8?B?dmVydGUhwrUuZ2lm?="
Content-Disposition: inline; filename="=?UTF-8?B?dmVydGUhwrUuZ2lm?="
Content-Transfer-Encoding: base64
Content-ID: <ii_151b51a37e5eb7a6>
X-Attachment-Id: ii_151b51a37e5eb7a6

R0lGODlhCgAKALMAAAAAAIAAAACAAICAAAAAgIAAgACAgMDAwICAgP8AAAD/AP//AAAA//8A/wD/
/////ywAAAAACgAKAAAEClDJSau9OOvNe44AOw==
--001a11416b9e9b229a05272b7052
Content-Type: image/gif; name="=?UTF-8?B?cm9zYcOnw6llLmdpZg==?="
Content-Disposition: inline; filename="=?UTF-8?B?cm9zYcOnw6llLmdpZg==?="
Content-Transfer-Encoding: base64
Content-ID: <ii_151b51a290ed6a91>
X-Attachment-Id: ii_151b51a290ed6a91

R0lGODdhAgACALMAAAAAAP///wAAAP//AP8AAP+AAAD/AAAAAAAA//8A/wAAAP+AgAAAAAAAAAAA
AAAAACwAAAAAAgACAAAEA3DJFQA7
--001a11416b9e9b229a05272b7052--
"""


class TestMailgateway(TestMail):

    def setUp(self):
        super(TestMailgateway, self).setUp()
        # groups@.. will cause the creation of new mail.channels
        self.mail_channel_model = self.env['ir.model'].search([('model', '=', 'mail.channel')], limit=1)
        self.alias = self.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': self.mail_channel_model.id,
            'alias_contact': 'everyone'})

        # test@.. will cause the creation of new mail.test
        self.mail_test_model = self.env['ir.model'].search([('model', '=', 'mail.test')], limit=1)
        self.alias_2 = self.env['mail.alias'].create({
            'alias_name': 'test',
            'alias_user_id': False,
            'alias_model_id': self.mail_test_model.id,
            'alias_contact': 'everyone'})

        # Set a first message on public group to test update and hierarchy
        self.fake_email = self.env['mail.message'].create({
            'model': 'mail.channel',
            'res_id': self.group_public.id,
            'subject': 'Public Discussion',
            'message_type': 'email',
            'author_id': self.partner_1.id,
            'message_id': '<123456-openerp-%s-mail.channel@%s>' % (self.group_public.id, socket.gethostname()),
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
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.channel should have been created')
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
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.channel should have been created')
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

        # TODO : the author of a message post on mail.channel should not be added as follower
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
            'alias_parent_model_id': self.mail_channel_model.id,
            'alias_parent_thread_id': self.group_pigs.id})

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
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.channel should have been created')

        # Test: one message that is the incoming email
        self.assertEqual(len(new_groups.message_ids), 1,
                         'message_process: newly created group should have the incoming email in message_ids')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_followers(self):
        """ Incoming email from a parent document follower on a Followers only alias -> ok """
        self.alias.write({
            'alias_contact': 'followers',
            'alias_parent_model_id': self.mail_channel_model.id,
            'alias_parent_thread_id': self.group_pigs.id})
        self.group_pigs.message_subscribe(partner_ids=[self.partner_1.id])
        new_groups = self.format_and_process(MAIL_TEMPLATE, email_from='Valid Lelitre <valid.lelitre@agrolait.com>', to='groups@example.com, other6@gmail.com')

        # Test: one group created by Raoul (or Sylvie maybe, if we implement it)
        self.assertEqual(len(new_groups), 1, 'message_process: a new mail.channel should have been created')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models', 'odoo.addons.mail.models.mail_mail')
    def test_message_process_alias_update(self):
        """ Incoming email update discussion + notification email """
        self.alias.write({'alias_force_thread_id': self.group_public.id})

        self.group_public.message_subscribe(partner_ids=[self.partner_1.id])
        new_groups = self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com',
            msg_id='<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>',
            to='groups@example.com>', subject='Re: cats')

        # Test: no new group + new message
        self.assertEqual(len(new_groups), 0,
                         'message_process: reply on Frogs should not have created a new group with new subject')
        self.assertEqual(len(self.group_public.message_ids), 2, 'message_process: group should contain one new message')
        # Test: sent emails: 1 (Sylvie copy of the incoming email)
        self.assertEqual(len(self._mails), 1,
                         'message_process: one email should have been generated')
        self.assertIn('valid.lelitre@agrolait.com', self._mails[0].get('email_to')[0],
                      'message_process: email should be sent to Sylvie')

        # TODO : the author of a message post on mail.channel should not be added as follower
        # FAIL ON 'message_process: after reply, group should have 2 followers') ` AssertionError: res.partner(104,) != res.partner(104, 105) : message_process: after reply, group should have 2 followers

        # Test: author (and not recipient) added as follower
        # self.assertEqual(self.group_public.message_partner_ids, self.partner_1 | self.partner_2,
        #                  'message_process: after reply, group should have 2 followers')
        # self.assertEqual(self.group_public.message_channel_ids, self.env['mail.channel'],
        #                  'message_process: after reply, group should have 2 followers (0 channels)')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_in_reply_to(self):
        """ Incoming email using in-rely-to should go into the right destination even with a wrong destination """
        self.format_and_process(
            MAIL_TEMPLATE, email_from='valid.other@gmail.com',
            msg_id='<1198923581.41972151344608186800.JavaMail.diff1@agrolait.com>',
            to='erroneous@example.com>', subject='Re: news',
            extra='In-Reply-To:\r\n\t%s\n' % self.fake_email.message_id)

        self.assertEqual(len(self.group_public.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references(self):
        """ Incoming email using references should go into the right destination even with a wrong destination """
        self.format_and_process(
            MAIL_TEMPLATE, to='erroneous@example.com',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>')

        self.assertEqual(len(self.group_public.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_references_forward(self):
        """ Incoming email using references but with alias forward should not go into references destination """
        res_test = self.format_and_process(
            MAIL_TEMPLATE, to='test@example.com',
            subject='My Dear Forward',
            extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % self.fake_email.message_id,
            msg_id='<1198923581.41972151344608186800.JavaMail.4@agrolait.com>',
            target_model='mail.test')

        self.assertEqual(len(self.group_public.message_ids), 1, 'message_process: group should not contain new message')
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

        self.assertEqual(len(self.group_public.message_ids), 2, 'message_process: group should contain one new message')
        self.assertEqual(len(self.fake_email.child_ids), 1, 'message_process: new message should be children of the existing one')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_model_res_id(self):
        """ Incoming email with ref holding model / res_id but that does not match any message in the thread: must raise since OpenERP saas-3 """
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, email_from='valid.lelitre@agrolait.com',
                          to='noone@example.com', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.channel@%s>' % (self.group_public.id, socket.gethostname()),
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
            extra='In-Reply-To: <12321321-openerp-%d-mail.channel@%s>' % (self.group_public.id, socket.gethostname()))

        # 3''. 6.1 compat mode should not work if hostname does not match!
        # Odoo 10 update: compat mode has been removed and should not work anymore and does not depend from hostname
        self.assertRaises(ValueError,
                          self.format_and_process,
                          MAIL_TEMPLATE, email_from='other5@gmail.com',
                          msg_id='<1.3.JavaMail.new@agrolait.com>',
                          to='noone@example.com>', subject='spam',
                          extra='In-Reply-To: <12321321-openerp-%d-mail.channel@neighbor.com>' % self.group_public.id)

        # Test created messages
        self.assertEqual(len(self.group_public.message_ids), 1)
        self.assertEqual(len(self.group_public.message_ids[0].child_ids), 0)

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_duplicate(self):
        """ Duplicate emails (same message_id) are not processed """
        self.alias.write({'alias_force_thread_id': self.group_public.id,})

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
        self.assertEqual(len(self.group_public.message_ids), 2, 'message_process: message with already existing message_id should not have been duplicated')
        # Test: message_id is still unique
        no_of_msg = self.env['mail.message'].search_count([('message_id', 'ilike', '<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>')])
        self.assertEqual(no_of_msg, 1,
                         'message_process: message with already existing message_id should not have been duplicated')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_partner_find(self):
        """ Finding the partner based on email, based on partner / user / follower """
        from_1 = self.env['res.partner'].create({'name': 'A', 'email': 'from.test@example.com'})

        self.format_and_process(MAIL_TEMPLATE, to='public@example.com', msg_id='<1>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.group_public.message_ids[0].author_id, from_1, 'message_process: email_from -> author_id wrong')
        self.group_public.message_unsubscribe([from_1.id])

        from_2 = self.env['res.users'].with_context({'no_reset_password': True}).create({'name': 'B', 'login': 'B', 'email': 'from.test@example.com'})

        self.format_and_process(MAIL_TEMPLATE, to='public@example.com', msg_id='<2>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.group_public.message_ids[0].author_id, from_2.partner_id, 'message_process: email_from -> author_id wrong')
        self.group_public.message_unsubscribe([from_2.partner_id.id])

        from_3 = self.env['res.partner'].create({'name': 'C', 'email': 'from.test@example.com'})
        self.group_public.message_subscribe([from_3.id])

        self.format_and_process(MAIL_TEMPLATE, to='public@example.com', msg_id='<3>', email_from='Brice Denisse <from.test@example.com>')
        self.assertEqual(self.group_public.message_ids[0].author_id, from_3, 'message_process: email_from -> author_id wrong')

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
            MAIL_TEMPLATE, to='noone@example.com', subject='Spammy', extra='', model='mail.channel',
            msg_id='<1198923581.41972151344608186760.JavaMail.new6@agrolait.com>')
        self.assertEqual(len(frog_groups), 1,
                         'message_process: erroneous email but with a fallback model should have created a new mail.channel')

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_plain_text(self):
        """ Incoming email in plaintext should be stored as html """
        frog_groups = self.format_and_process(
            MAIL_TEMPLATE_PLAINTEXT, to='groups@example.com', subject='Frogs Return', extra='',
            msg_id='<deadcafe.1337@smtp.agrolait.com>')
        self.assertEqual(len(frog_groups), 1, 'message_process: a new mail.channel should have been created')
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
            'thread_model': 'mail.channel'
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
                         'message_post: private discussion: wrong author through mailgatewya based on email')
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
        msg = self.group_pigs.sudo(self.user_employee).message_post(no_auto_thread=True, subtype='mail.mt_comment')
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
        channel = self.env['mail.channel'].search([('name', "=", msg_fw.subject)])
        self.assertEqual(len(channel), 1)
        self.assertEqual(msg_fw.model, 'mail.channel')
        self.assertFalse(msg_fw.parent_id)
        self.assertTrue(msg_fw.res_id == channel.id)

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
        channel = self.env['mail.channel'].search([('name', "=", msg_fw.subject)])
        self.assertEqual(len(channel), 0)
        self.assertEqual(msg_fw.model, 'mail.channel')
        self.assertFalse(msg_fw.parent_id)
        self.assertTrue(msg_fw.res_id == self.group_public.id)
