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

import tools

from openerp.tests import common
from openerp.tools.html_sanitize import html_sanitize

MAIL_TEMPLATE = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: Sylvie Lelitre <sylvie.lelitre@agrolait.com>
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative;
    boundary="----=_Part_4200734_24778174.1344608186754"
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: <1198923581.41972151344608186760.JavaMail@agrolait.com>
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


class TestMailMockups(common.TransactionCase):

    def _mock_smtp_gateway(self, *args, **kwargs):
        return True

    def _init_mock_build_email(self):
        self._build_email_args_list = []
        self._build_email_kwargs_list = []

    def _mock_build_email(self, *args, **kwargs):
        self._build_email_args_list.append(args)
        self._build_email_kwargs_list.append(kwargs)
        return self._build_email(*args, **kwargs)

    def setUp(self):
        super(TestMailMockups, self).setUp()
        # Install mock SMTP gateway
        self._init_mock_build_email()
        self._build_email = self.registry('ir.mail_server').build_email
        self.registry('ir.mail_server').build_email = self._mock_build_email
        self._send_email = self.registry('ir.mail_server').send_email
        self.registry('ir.mail_server').send_email = self._mock_smtp_gateway

    def tearDown(self):
        # Remove mocks
        self.registry('ir.mail_server').build_email = self._build_email
        self.registry('ir.mail_server').send_email = self._send_email
        super(TestMailMockups, self).tearDown()


class test_mail(TestMailMockups):

    def _mock_send_get_mail_body(self, *args, **kwargs):
        # def _send_get_mail_body(self, cr, uid, mail, partner=None, context=None)
        body = tools.append_content_to_html(args[2].body_html, kwargs.get('partner').name if kwargs.get('partner') else 'No specific partner')
        return body

    def setUp(self):
        super(test_mail, self).setUp()
        self.ir_model = self.registry('ir.model')
        self.mail_alias = self.registry('mail.alias')
        self.mail_thread = self.registry('mail.thread')
        self.mail_group = self.registry('mail.group')
        self.mail_mail = self.registry('mail.mail')
        self.mail_message = self.registry('mail.message')
        self.mail_notification = self.registry('mail.notification')
        self.mail_followers = self.registry('mail.followers')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # Mock send_get_mail_body to test its functionality without other addons override
        self._send_get_mail_body = self.registry('mail.mail').send_get_mail_body
        self.registry('mail.mail').send_get_mail_body = self._mock_send_get_mail_body

        # groups@.. will cause the creation of new mail groups
        self.mail_group_model_id = self.ir_model.search(self.cr, self.uid, [('model', '=', 'mail.group')])[0]
        self.mail_alias.create(self.cr, self.uid, {'alias_name': 'groups',
                                                   'alias_model_id': self.mail_group_model_id})
        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

    def tearDown(self):
        # Remove mocks
        self.registry('mail.mail').send_get_mail_body = self._send_get_mail_body
        super(test_mail, self).tearDown()

    def test_00_message_process(self):
        cr, uid = self.cr, self.uid
        # Incoming mail creates a new mail_group "frogs"
        self.assertEqual(self.mail_group.search(cr, uid, [('name', '=', 'frogs')]), [])
        mail_frogs = MAIL_TEMPLATE.format(to='groups@example.com, other@gmail.com', subject='frogs', extra='')
        self.mail_thread.message_process(cr, uid, None, mail_frogs)
        frog_groups = self.mail_group.search(cr, uid, [('name', '=', 'frogs')])
        self.assertTrue(len(frog_groups) == 1)

        # Previously-created group can be emailed now - it should have an implicit alias group+frogs@...
        frog_group = self.mail_group.browse(cr, uid, frog_groups[0])
        group_messages = frog_group.message_ids
        self.assertTrue(len(group_messages) == 1, 'New group should only have the original message')
        mail_frog_news = MAIL_TEMPLATE.format(to='Friendly Frogs <group+frogs@example.com>', subject='news', extra='')
        self.mail_thread.message_process(cr, uid, None, mail_frog_news)
        frog_group.refresh()
        self.assertTrue(len(frog_group.message_ids) == 2, 'Group should contain 2 messages now')

        # Even with a wrong destination, a reply should end up in the correct thread
        mail_reply = MAIL_TEMPLATE.format(to='erroneous@example.com>', subject='Re: news',
                                          extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>\n' % frog_group.id)
        self.mail_thread.message_process(cr, uid, None, mail_reply)
        frog_group.refresh()
        self.assertTrue(len(frog_group.message_ids) == 3, 'Group should contain 3 messages now')

        # No model passed and no matching alias must raise
        mail_spam = MAIL_TEMPLATE.format(to='noone@example.com', subject='spam', extra='')
        self.assertRaises(Exception,
                          self.mail_thread.message_process,
                          cr, uid, None, mail_spam)

        # plain text content should be wrapped and stored as html
        test_msg_id = '<deadcafe.1337@smtp.agrolait.com>'
        mail_text = MAIL_TEMPLATE_PLAINTEXT.format(to='groups@example.com', subject='frogs', extra='', msg_id=test_msg_id)
        self.mail_thread.message_process(cr, uid, None, mail_text)
        new_mail = self.mail_message.browse(cr, uid, self.mail_message.search(cr, uid, [('message_id', '=', test_msg_id)])[0])
        self.assertEqual(new_mail.body, '\n<pre>\nPlease call me as soon as possible this afternoon!\n\n--\nSylvie\n</pre>\n',
                         'plaintext mail incorrectly parsed')

    def test_10_many2many_reference_field(self):
        """ Tests designed for the many2many_reference field (follower_ids).
            We will test to perform writes using the many2many commands 0, 3, 4,
            5 and 6. """
        cr, uid = self.cr, self.uid
        user_admin = self.res_users.browse(cr, uid, uid)
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Create partner Bert Poilu
        partner_bert_id = self.res_partner.create(cr, uid, {'name': 'Bert Poilu'})

        # Create 'disturbing' values in mail.followers: same res_id, other res_model; same res_model, other res_id
        group_dummy_id = self.mail_group.create(cr, uid,
            {'name': 'Dummy group'})
        self.mail_followers.create(cr, uid,
            {'res_model': 'mail.thread', 'res_id': self.group_pigs_id, 'partner_id': partner_bert_id})
        self.mail_followers.create(cr, uid,
            {'res_model': 'mail.group', 'res_id': group_dummy_id, 'partner_id': partner_bert_id})

        # Pigs just created: should be only Admin as follower
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([user_admin.partner_id.id]), 'Admin should be the only Pigs fan')

        # Subscribe Bert through a '4' command
        group_pigs.write({'message_follower_ids': [(4, partner_bert_id)]})
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([partner_bert_id, user_admin.partner_id.id]), 'Bert and Admin should be the only Pigs fans')

        # Unsubscribe Bert through a '3' command
        group_pigs.write({'message_follower_ids': [(3, partner_bert_id)]})
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([user_admin.partner_id.id]), 'Admin should be the only Pigs fan')

        # Set followers through a '6' command
        group_pigs.write({'message_follower_ids': [(6, 0, [partner_bert_id])]})
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([partner_bert_id]), 'Bert should be the only Pigs fan')

        # Add a follower created on the fly through a '0' command
        group_pigs.write({'message_follower_ids': [(0, 0, {'name': 'Patrick Fiori'})]})
        partner_patrick_id = self.res_partner.search(cr, uid, [('name', '=', 'Patrick Fiori')])[0]
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([partner_bert_id, partner_patrick_id]), 'Bert and Patrick should be the only Pigs fans')

        # Finally, unlink through a '5' command
        group_pigs.write({'message_follower_ids': [(5, 0)]})
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertFalse(follower_ids, 'Pigs group should not have fans anymore')

        # Test dummy data has not been altered
        fol_obj_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.thread'), ('res_id', '=', self.group_pigs_id)])
        follower_ids = set([follower.partner_id.id for follower in self.mail_followers.browse(cr, uid, fol_obj_ids)])
        self.assertEqual(follower_ids, set([partner_bert_id]), 'Bert should be the follower of dummy mail.thread data')
        fol_obj_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', group_dummy_id)])
        follower_ids = set([follower.partner_id.id for follower in self.mail_followers.browse(cr, uid, fol_obj_ids)])
        self.assertEqual(follower_ids, set([partner_bert_id, user_admin.partner_id.id]), 'Bert and Admin should be the followers of dummy mail.group data')

    def test_11_message_followers(self):
        """ Tests designed for the subscriber API. """
        cr, uid = self.cr, self.uid
        user_admin = self.res_users.browse(cr, uid, uid)
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Create user Raoul
        user_raoul_id = self.res_users.create(cr, uid, {'name': 'Raoul Grosbedon', 'login': 'raoul'})
        user_raoul = self.res_users.browse(cr, uid, user_raoul_id)

        # Subscribe Raoul three times (niak niak) through message_subscribe_users
        group_pigs.message_subscribe_users([user_raoul_id, user_raoul_id])
        group_pigs.message_subscribe_users([user_raoul_id])
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(len(follower_ids), 2, 'There should be 2 Pigs fans')
        self.assertEqual(set(follower_ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]), 'Admin and Raoul should be the only 2 Pigs fans')

        # Unsubscribe Raoul twice through message_unsubscribe_users
        group_pigs.message_unsubscribe_users([user_raoul_id, user_raoul_id])
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(follower_ids, [user_admin.partner_id.id], 'Admin must be the only Pigs fan')

    def test_20_message_post(self):
        """ Tests designed for message_post. """
        cr, uid = self.cr, self.uid
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a'})
        user_admin = self.res_users.browse(cr, uid, uid)
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # 0 - Admin
        p_a_id = user_admin.partner_id.id
        # 1 - Bert Tartopoils, with email, should receive emails for comments and emails
        p_b_id = self.res_partner.create(cr, uid, {'name': 'Bert Tartopoils', 'email': 'b@b'})
        # 2 - Carine Poilvache, with email, should never receive emails
        p_c_id = self.res_partner.create(cr, uid, {'name': 'Carine Poilvache', 'email': 'c@c', 'notification_email_send': 'email'})
        # 3 - Dédé Grosbedon, without email, to test email verification; should receive emails for every message
        p_d_id = self.res_partner.create(cr, uid, {'name': 'Dédé Grosbedon', 'notification_email_send': 'all'})

        # Subscribe #1, #2
        group_pigs.message_subscribe([p_b_id, p_c_id])

        # Mail data
        _subject = 'Pigs'
        _mail_subject = '%s posted on %s' % (user_admin.name, group_pigs.name)
        _body1 = 'Pigs rules'
        _mail_body1 = 'Pigs rules\n<pre>Admin</pre>\n'
        _mail_bodyalt1 = 'Pigs rules\nAdmin'
        _body2 = '<html>Pigs rules</html>'
        _mail_body2 = html_sanitize('<html>Pigs rules\n<pre>Admin</pre>\n</html>')
        _mail_bodyalt2 = 'Pigs rules\nAdmin'
        _attachments = [('First', 'My first attachment'), ('Second', 'My second attachment')]

        # CASE1: post comment, body and subject specified
        self._init_mock_build_email()
        msg_id = self.mail_group.message_post(cr, uid, self.group_pigs_id, body=_body1, subject=_subject, type='comment')
        message = self.mail_message.browse(cr, uid, msg_id)
        sent_emails = self._build_email_kwargs_list
        # Test: notifications have been deleted
        self.assertFalse(self.mail_mail.search(cr, uid, [('mail_message_id', '=', msg_id)]), 'mail.mail notifications should have been auto-deleted!')
        # Test: mail_message: subject is _subject, body is _body1 (no formatting done)
        self.assertEqual(message.subject, _subject, 'mail.message subject incorrect')
        self.assertEqual(message.body, _body1, 'mail.message body incorrect')
        # Test: sent_email: email send by server: correct subject, body, body_alternative
        for sent_email in sent_emails:
            self.assertEqual(sent_email['subject'], _subject, 'sent_email subject incorrect')
            self.assertEqual(sent_email['body'], _mail_body1 + '\n<pre>Bert Tartopoils</pre>\n', 'sent_email body incorrect')
            self.assertEqual(sent_email['body_alternative'], _mail_bodyalt1 + '\nBert Tartopoils', 'sent_email body_alternative is incorrect')
        # Test: mail_message: partner_ids = group followers
        message_pids = set([partner.id for partner in message.partner_ids])
        test_pids = set([p_a_id, p_b_id, p_c_id])
        self.assertEqual(test_pids, message_pids, 'mail.message partners incorrect')
        # Test: notification linked to this message = group followers = partner_ids
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', message.id)])
        notif_pids = set([notif.partner_id.id for notif in self.mail_notification.browse(cr, uid, notif_ids)])
        self.assertEqual(notif_pids, test_pids, 'mail.message notification partners incorrect')
        # Test: sent_email: email_to should contain b@b, not c@c (pref email), not a@a (writer)
        for sent_email in sent_emails:
            self.assertEqual(sent_email['email_to'], ['b@b'], 'sent_email email_to is incorrect')

        # CASE2: post an email with attachments, parent_id, partner_ids
        # TESTS: automatic subject, signature in body_html, attachments propagation
        self._init_mock_build_email()
        msg_id2 = self.mail_group.message_post(cr, uid, self.group_pigs_id, body=_body2, type='email',
            partner_ids=[(6, 0, [p_d_id])], parent_id=msg_id, attachments=_attachments)
        message = self.mail_message.browse(cr, uid, msg_id2)
        sent_emails = self._build_email_kwargs_list
        self.assertFalse(self.mail_mail.search(cr, uid, [('mail_message_id', '=', msg_id2)]), 'mail.mail notifications should have been auto-deleted!')

        # Test: mail_message: subject is False, body is _body2 (no formatting done), parent_id is msg_id
        self.assertEqual(message.subject, False, 'mail.message subject incorrect')
        self.assertEqual(message.body, html_sanitize(_body2), 'mail.message body incorrect')
        self.assertEqual(message.parent_id.id, msg_id, 'mail.message parent_id incorrect')
        # Test: sent_email: email send by server: correct subject, body, body_alternative
        self.assertEqual(len(sent_emails), 2, 'sent_email number of sent emails incorrect')
        for sent_email in sent_emails:
            self.assertEqual(sent_email['subject'], _mail_subject, 'sent_email subject incorrect')
            self.assertIn(_mail_body2, sent_email['body'], 'sent_email body incorrect')
            self.assertIn(_mail_bodyalt2, sent_email['body_alternative'], 'sent_email body_alternative incorrect')
        # Test: mail_message: partner_ids = group followers
        message_pids = set([partner.id for partner in message.partner_ids])
        test_pids = set([p_a_id, p_b_id, p_c_id, p_d_id])
        self.assertEqual(message_pids, test_pids, 'mail.message partners incorrect')
        # Test: notifications linked to this message = group followers = partner_ids
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', message.id)])
        notif_pids = set([notif.partner_id.id for notif in self.mail_notification.browse(cr, uid, notif_ids)])
        self.assertEqual(notif_pids, test_pids, 'mail.message notification partners incorrect')
        # Test: sent_email: email_to should contain b@b, c@c, not a@a (writer)
        for sent_email in sent_emails:
            self.assertTrue(set(sent_email['email_to']).issubset(set(['b@b', 'c@c'])), 'sent_email email_to incorrect')
        # Test: attachments
        for attach in message.attachment_ids:
            self.assertEqual(attach.res_model, 'mail.group', 'mail.message attachment res_model incorrect')
            self.assertEqual(attach.res_id, self.group_pigs_id, 'mail.message attachment res_id incorrect')
            self.assertIn((attach.name, attach.datas.decode('base64')), _attachments,
                'mail.message attachment name / data incorrect')

    def test_21_message_compose_wizard(self):
        """ Tests designed for the mail.compose.message wizard. """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a'})
        user_admin = self.res_users.browse(cr, uid, uid)
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        group_bird_id = self.mail_group.create(cr, uid, {'name': 'Bird', 'description': 'Bird resistance'})
        group_bird = self.mail_group.browse(cr, uid, group_bird_id)

        # Mail data
        _subject = 'Pigs'
        _body_text = 'Pigs rules'
        _msg_reply = 'Re: Pigs'
        _msg_body = '<pre>Pigs rules</pre>'
        _attachments = [
            {'name': 'First', 'datas_fname': 'first.txt', 'datas': 'My first attachment'.encode('base64')},
            {'name': 'Second', 'datas_fname': 'second.txt', 'datas': 'My second attachment'.encode('base64')}
            ]
        _attachments_test = [('first.txt', 'My first attachment'), ('second.txt', 'My second attachment')]

        # Create partners
        # 0 - Admin
        p_a_id = user_admin.partner_id.id
        # 1 - Bert Tartopoils, with email, should receive emails for comments and emails
        p_b_id = self.res_partner.create(cr, uid, {'name': 'Bert Tartopoils', 'email': 'b@b'})
        # 2 - Carine Poilvache, with email, should never receive emails
        p_c_id = self.res_partner.create(cr, uid, {'name': 'Carine Poilvache', 'email': 'c@c', 'notification_email_send': 'email'})
        # 3 - Dédé Grosbedon, without email, to test email verification; should receive emails for every message
        p_d_id = self.res_partner.create(cr, uid, {'name': 'Dédé Grosbedon', 'notification_email_send': 'all'})

        # Subscribe #1
        group_pigs.message_subscribe([p_b_id])

        # ----------------------------------------
        # CASE1: comment on group_pigs
        # ----------------------------------------

        # 1. Comment group_pigs with body_text and subject
        compose_id = mail_compose.create(cr, uid,
            {'subject': _subject, 'body_text': _body_text, 'partner_ids': [(4, p_c_id), (4, p_d_id)]},
            {'default_composition_mode': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_pigs_id})
        compose = mail_compose.browse(cr, uid, compose_id)
        # Test: mail.compose.message: composition_mode, model, res_id
        self.assertEqual(compose.composition_mode,  'comment', 'mail.compose.message incorrect composition_mode')
        self.assertEqual(compose.model,  'mail.group', 'mail.compose.message incorrect model')
        self.assertEqual(compose.res_id, self.group_pigs_id, 'mail.compose.message incorrect res_id')

        # 2. Post the comment, get created message
        mail_compose.send_mail(cr, uid, [compose_id])
        group_pigs.refresh()
        message = group_pigs.message_ids[0]
        # Test: mail.message: subject, body inside pre
        self.assertEqual(message.subject,  False, 'mail.message incorrect subject')
        self.assertEqual(message.body, _msg_body, 'mail.message incorrect body')
        # Test: mail.message: partner_ids = entries in mail.notification: group_pigs fans (a, b) + mail.compose.message partner_ids (c, d)
        msg_pids = [partner.id for partner in message.partner_ids]
        test_pids = [p_a_id, p_b_id, p_c_id, p_d_id]
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', message.id)])
        self.assertEqual(len(notif_ids), 4, 'mail.message: too much notifications created')
        self.assertEqual(set(msg_pids), set(test_pids), 'mail.message partner_ids incorrect')

        # ----------------------------------------
        # CASE2: reply to last comment with attachments
        # ----------------------------------------

        # 1. Update last comment subject, reply with attachments
        message.write({'subject': _subject})
        compose_id = mail_compose.create(cr, uid,
            {'attachment_ids': [(0, 0, _attachments[0]), (0, 0, _attachments[1])]},
            {'default_composition_mode': 'reply', 'default_model': 'mail.thread', 'default_res_id': self.group_pigs_id, 'default_parent_id': message.id})
        compose = mail_compose.browse(cr, uid, compose_id)
        # Test: model, res_id, parent_id, content_subtype
        self.assertEqual(compose.model,  'mail.group', 'mail.compose.message incorrect model')
        self.assertEqual(compose.res_id, self.group_pigs_id, 'mail.compose.message incorrect res_id')
        self.assertEqual(compose.parent_id.id, message.id, 'mail.compose.message incorrect parent_id')
        self.assertEqual(compose.content_subtype, 'html', 'mail.compose.message incorrect content_subtype')

        # 2. Post the comment, get created message
        parent_id = message.id
        mail_compose.send_mail(cr, uid, [compose_id])
        group_pigs.refresh()
        message = group_pigs.message_ids[0]
        # Test: mail.message: subject as Re:.., body in html, parent_id
        self.assertEqual(message.subject, _msg_reply, 'mail.message incorrect subject')
        self.assertIn('Administrator wrote:<blockquote><pre>Pigs rules</pre></blockquote></div>', message.body, 'mail.message body is incorrect')
        self.assertEqual(message.parent_id and message.parent_id.id, parent_id, 'mail.message parent_id incorrect')
        # Test: mail.message: attachments
        for attach in message.attachment_ids:
            self.assertEqual(attach.res_model, 'mail.group', 'mail.message attachment res_model incorrect')
            self.assertEqual(attach.res_id, self.group_pigs_id, 'mail.message attachment res_id incorrect')
            self.assertIn((attach.name, attach.datas.decode('base64')), _attachments_test,
                'mail.message attachment name / data incorrect')

        # ----------------------------------------
        # CASE3: mass_mail on Pigs and Bird
        # ----------------------------------------

        # 1. mass_mail on pigs and bird
        compose_id = mail_compose.create(cr, uid,
            {'subject': _subject, 'body': '${object.description}'},
            {'default_composition_mode': 'mass_mail', 'default_model': 'mail.group', 'default_res_id': -1,
                'active_ids': [self.group_pigs_id, group_bird_id]})
        compose = mail_compose.browse(cr, uid, compose_id)
        # Test: content_subtype is html
        self.assertEqual(compose.content_subtype, 'html', 'mail.compose.message content_subtype incorrect')

        # 2. Post the comment, get created message for each group
        mail_compose.send_mail(cr, uid, [compose_id],
            context={'default_res_id': -1, 'active_ids': [self.group_pigs_id, group_bird_id]})
        group_pigs.refresh()
        group_bird.refresh()
        message1 = group_pigs.message_ids[0]
        message2 = group_bird.message_ids[0]
        # Test: Pigs and Bird did receive their message
        test_msg_ids = self.mail_message.search(cr, uid, [], limit=2)
        self.assertIn(message1.id, test_msg_ids, 'Pigs did not receive its mass mailing message')
        self.assertIn(message2.id, test_msg_ids, 'Bird did not receive its mass mailing message')
        # Test: mail.message: subject, body
        self.assertEqual(message1.subject, _subject, 'mail.message subject incorrect')
        self.assertEqual(message1.body, group_pigs.description, 'mail.message body incorrect')
        self.assertEqual(message2.subject, _subject, 'mail.message subject incorrect')
        self.assertEqual(message2.body, group_bird.description, 'mail.message body incorrect')

    def test_30_message_read(self):
        """ Tests designed for message_read. """
        # TDE NOTE: this test is not finished, as the message_read method is not fully specified.
        # It will be updated as soon as we have fixed specs !
        cr, uid = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        def _compare_structures(struct1, struct2, n=0):
            # print '%scompare structure' % ('\t' * n)
            self.assertEqual(len(struct1), len(struct2), 'message_read structure number of childs incorrect')
            for x in range(len(struct1)):
                # print '%s' % ('\t' * n), struct1[x]['id'], struct2[x]['id'], struct1[x].get('subject') or ''
                self.assertEqual(struct1[x]['id'], struct2[x]['id'], 'message_read failure %s' % struct1[x].get('subject'))
                _compare_structures(struct1[x]['child_ids'], struct2[x]['child_ids'], n + 1)
            # print '%send compare' % ('\t' * n)

        # ----------------------------------------
        # CASE1: Flattening test
        # ----------------------------------------

        # Create dummy message structure
        import copy
        tree = [{'id': 2, 'child_ids': [
                    {'id': 6, 'child_ids': [
                        {'id': 8, 'child_ids': []},
                        ]},
                    ]},
                {'id': 1, 'child_ids':[
                    {'id': 7, 'child_ids': [
                        {'id': 9, 'child_ids': []},
                        ]},
                    {'id': 4, 'child_ids': [
                        {'id': 10, 'child_ids': []},
                        {'id': 5, 'child_ids': []},
                        ]},
                    {'id': 3, 'child_ids': []},
                    ]},
                ]
        # Test: completely flat
        new_tree = self.mail_message.message_read_tree_flatten(cr, uid, copy.deepcopy(tree), 0, 0)
        self.assertEqual(len(new_tree), 10, 'message_read_tree_flatten wrong in flat')
        # Test: 1 thread level
        tree_test = [{'id': 2, 'child_ids': [
                        {'id': 8, 'child_ids': []}, {'id': 6, 'child_ids': []},
                    ]},
                    {'id': 1, 'child_ids': [
                        {'id': 10, 'child_ids': []}, {'id': 9, 'child_ids': []},
                        {'id': 7, 'child_ids': []}, {'id': 5, 'child_ids': []},
                        {'id': 4, 'child_ids': []}, {'id': 3, 'child_ids': []},
                    ]},
                    ]
        new_tree = self.mail_message.message_read_tree_flatten(cr, uid, copy.deepcopy(tree), 0, 1)
        _compare_structures(new_tree, tree_test)
        # Test: 2 thread levels
        new_tree = self.mail_message.message_read_tree_flatten(cr, uid, copy.deepcopy(tree), 0, 2)
        _compare_structures(new_tree, tree)

        # ----------------------------------------
        # CASE2: message_read test
        # ----------------------------------------

        # 1. Add a few messages to pigs group
        msgid1 = group_pigs.message_post(body='1', subject='1', parent_id=False)
        msgid2 = group_pigs.message_post(body='2', subject='1-1', parent_id=msgid1)
        msgid3 = group_pigs.message_post(body='3', subject='1-2', parent_id=msgid1)
        msgid4 = group_pigs.message_post(body='4', subject='2', parent_id=False)
        msgid5 = group_pigs.message_post(body='5', subject='1-1-1', parent_id=msgid2)
        msgid6 = group_pigs.message_post(body='6', subject='2-1', parent_id=msgid4)

        # Test: read all messages flat
        tree_test = [{'id': msgid6, 'child_ids': []}, {'id': msgid5, 'child_ids': []},
                        {'id': msgid4, 'child_ids': []}, {'id': msgid3, 'child_ids': []},
                        {'id': msgid2, 'child_ids': []}, {'id': msgid1, 'child_ids': []}]
        tree = self.mail_message.message_read(cr, uid, ids=False, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)], thread_level=0, limit=10)
        _compare_structures(tree, tree_test)
        # Test: read with 1 level of thread
        tree_test = [{'id': msgid4, 'child_ids': [{'id': msgid6, 'child_ids': []}, ]},
                    {'id': msgid1, 'child_ids': [
                        {'id': msgid5, 'child_ids': []}, {'id': msgid3, 'child_ids': []},
                        {'id': msgid2, 'child_ids': []},
                    ]},
                    ]
        tree = self.mail_message.message_read(cr, uid, ids=False, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)], thread_level=1, limit=10)
        _compare_structures(tree, tree_test)
        # Test: read with 2 levels of thread
        tree_test = [{'id': msgid4, 'child_ids': [{'id': msgid6, 'child_ids': []}, ]},
                    {'id': msgid1, 'child_ids': [
                        {'id': msgid3, 'child_ids': []},
                        {'id': msgid2, 'child_ids': [{'id': msgid5, 'child_ids': []}, ]},
                    ]},
                    ]
        tree = self.mail_message.message_read(cr, uid, ids=False, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)], thread_level=2, limit=10)
        _compare_structures(tree, tree_test)

        # 2. Test expandables
        # TDE FIXME: add those tests when expandables are specified and implemented

    def test_40_needaction(self):
        """ Tests for mail.message needaction. """
        cr, uid = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        user_admin = self.res_users.browse(cr, uid, uid)

        # Demo values: check unread notification = needaction on mail.message
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_admin.partner_id.id),
            ('read', '=', False)
            ])
        na_count = self.mail_message._needaction_count(cr, uid, domain=[])
        self.assertEqual(len(notif_ids), na_count, 'unread notifications count does not match needaction count')

        # Post 4 message on group_pigs
        for dummy in range(4):
            group_pigs.message_post(body='My Body')

        # Check there are 4 new needaction on mail.message
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_admin.partner_id.id),
            ('read', '=', False)
            ])
        na_count = self.mail_message._needaction_count(cr, uid, domain=[])
        self.assertEqual(len(notif_ids), na_count, 'unread notifications count does not match needaction count')

        # Check there are 4 needaction on mail.message with particular domain
        na_count = self.mail_message._needaction_count(cr, uid, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)])
        self.assertEqual(na_count, 4, 'posted message count does not match needaction count')

    def test_50_thread_parent_resolution(self):
        """Verify parent/child relationships are correctly established when processing incoming mails"""
        cr, uid = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        msg1 = group_pigs.message_post(body='My Body', subject='1')
        msg2 = group_pigs.message_post(body='My Body', subject='2')
        msg1, msg2 = self.mail_message.browse(cr, uid, [msg1, msg2])
        self.assertTrue(msg1.message_id, "New message should have a proper message_id")

        # Reply to msg1, make sure the reply is properly attached using the various reply identification mechanisms
        # 1. In-Reply-To header
        reply_msg = MAIL_TEMPLATE.format(to='Pretty Pigs <group+pigs@example.com>, other@gmail.com', subject='Re: 1',
                                         extra='In-Reply-To: %s' % msg1.message_id)
        self.mail_thread.message_process(cr, uid, None, reply_msg)
        # 2. References header
        reply_msg2 = MAIL_TEMPLATE.format(to='Pretty Pigs <group+pigs@example.com>, other@gmail.com', subject='Re: Re: 1',
                                         extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % msg1.message_id)
        self.mail_thread.message_process(cr, uid, None, reply_msg2)
        # 3. Subject contains [<ID>] + model passed to message+process -> only attached to group, not to mail
        reply_msg3 = MAIL_TEMPLATE.format(to='Pretty Pigs <group+pigs@example.com>, other@gmail.com',
                                          extra='', subject='Re: [%s] 1' % self.group_pigs_id)
        self.mail_thread.message_process(cr, uid, 'mail.group', reply_msg3)
        group_pigs.refresh()
        msg1.refresh()
        self.assertEqual(5, len(group_pigs.message_ids), 'group should contain 5 messages')
        self.assertEqual(2, len(msg1.child_ids), 'msg1 should have 2 children now')

    def test_60_vote(self):
        """ Test designed for the vote/unvote feature. """
        cr, uid = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        user_admin = self.res_users.browse(cr, uid, uid)
        msg1 = group_pigs.message_post(body='My Body', subject='1')
        msg1 = self.mail_message.browse(cr, uid, msg1)

        # Create user Bert Tartopoils
        user_bert_id = self.res_users.create(cr, uid, {'name': 'Bert', 'login': 'bert'})
        user_bert = self.res_users.browse(cr, uid, user_bert_id)

        # Test: msg1 and msg2 have void vote_user_ids
        self.assertFalse(msg1.vote_user_ids, 'newly created message msg1 has not void vote_user_ids')
        # Do: Admin vote for msg1
        self.mail_message.vote_toggle(cr, uid, [msg1.id])
        msg1.refresh()
        # Test: msg1 has Admin as voter
        self.assertEqual(set(msg1.vote_user_ids), set([user_admin]), 'after voting, Admin is not the voter')
        # Do: Bert vote for msg1
        self.mail_message.vote_toggle(cr, uid, [msg1.id], [user_bert_id])
        msg1.refresh()
        # Test: msg1 has Admin and Bert as voters
        self.assertEqual(set(msg1.vote_user_ids), set([user_admin, user_bert]), 'after voting, Admin and Bert are not the voters')
        # Do: Admin unvote for msg1
        self.mail_message.vote_toggle(cr, uid, [msg1.id])
        msg1.refresh()
        # Test: msg1 has Bert as voter
        self.assertEqual(set(msg1.vote_user_ids), set([user_bert]), 'after unvoting for Admin, Bert is not the voter')

    def test_70_read_unread(self):
        """ Test designed for the message read or unread feature. """
        cr, uid = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        user_admin = self.res_users.browse(cr, uid, uid)
        
        # Create user Bert Tartopoils
        user_bert_id = self.res_users.create(cr, uid, {'name': 'Bert', 'login': 'bert'})
        user_bert = self.res_users.browse(cr, uid, user_bert_id)
        #subscribe Bert Tartopoils
        group_pigs.message_subscribe([user_bert.partner_id.id])
        #Post two new message into pigs group
        msg1 = group_pigs.message_post(body='My Body', subject='1')
        msg2 = group_pigs.message_post(body='My Body', subject='2')
        message1 = self.mail_message.browse(cr, uid, msg1)
        message2 = self.mail_message.browse(cr, uid, msg2)
        context= {}
        #Check Before read , number of posted message count are 2.
        na_count = self.mail_message._needaction_count(cr, uid, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)])
        self.assertEqual(na_count, 2, 'posted message count does not match needaction count')
        #Test : Groups contain two messages.
        self.assertEqual(2, len(group_pigs.message_ids), 'group should contain 2 messages')
        #Read message without key. using bert parner
        msg_data1 = self.mail_message.message_read(cr, user_bert.id, ids=[message1.id], domain=[], thread_level=2, limit=10,context=context)
        #check notification For message readable or unread.
        notif_msg1_ids1 = self.mail_notification.search(cr, uid, [('partner_id', '=', user_bert.partner_id.id),('message_id', '=', message1.id)], context=context)
        notif_data1 = self.mail_notification.read(cr, uid, notif_msg1_ids1, ['read'])[0]['read']
        # Test: Message1 are marked as read.
        self.assertTrue(notif_data1, 'Message1 are set as read for the user Bert that read it')
        #Pass key in context for unread message..
        context.update({'default_model': 'mail.group', 'default_res_id': [self.group_pigs_id], 'mail_keep_unread': True})
        # Test: New created Message2 are set as unread.
        msg_data2 = self.mail_message.message_read(cr, uid, ids=[message2.id], domain=[], thread_level=2, limit=10,context=context)
        #Check Notification For unread message..
        notif_msg2_ids2 = self.mail_notification.search(cr, uid, [('partner_id', '=', user_admin.partner_id.id),('message_id', '=', message2.id)], context=context)
        notif_data2 = self.mail_notification.read(cr, uid, notif_msg2_ids2, ['read'])[0]['read']
        self.assertFalse(notif_data2, 'Newly created  Message2 are set as unread')
        # Check there are 1 needaction after Reading one posted message on mail.message with particular domain.
        na_count = self.mail_message._needaction_count(cr, uid, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)])
        self.assertEqual(na_count, 1, 'posted message count does not match needaction count')
