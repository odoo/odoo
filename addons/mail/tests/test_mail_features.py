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
from openerp.tools.mail import html_sanitize, append_content_to_html

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


class test_mail(TestMailBase):

    def _mock_send_get_mail_body(self, *args, **kwargs):
        # def _send_get_mail_body(self, cr, uid, mail, partner=None, context=None)
        body = append_content_to_html(args[2].body_html, kwargs.get('partner').name if kwargs.get('partner') else 'No specific partner', plaintext=False)
        return body

    def setUp(self):
        super(test_mail, self).setUp()

        # Mock send_get_mail_body to test its functionality without other addons override
        self._send_get_mail_body = self.registry('mail.mail').send_get_mail_body
        self.registry('mail.mail').send_get_mail_body = self._mock_send_get_mail_body

    def tearDown(self):
        # Remove mocks
        self.registry('mail.mail').send_get_mail_body = self._send_get_mail_body
        super(test_mail, self).tearDown()

    def test_00_message_process(self):
        """ Testing incoming emails processing. """
        cr, uid, user_raoul = self.cr, self.uid, self.user_raoul

        # groups@.. will cause the creation of new mail groups
        self.mail_group_model_id = self.ir_model.search(cr, uid, [('model', '=', 'mail.group')])[0]
        self.mail_alias.create(cr, uid, {'alias_name': 'groups', 'alias_model_id': self.mail_group_model_id})

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
        self.assertEqual(new_mail.body, '<pre>\nPlease call me as soon as possible this afternoon!\n\n--\nSylvie\n</pre>',
                         'plaintext mail incorrectly parsed')

        # Do: post a new message, with a known partner
        test_msg_id = '<deadcafe.1337-2@smtp.agrolait.com>'
        TEMPLATE_MOD = MAIL_TEMPLATE_PLAINTEXT.replace('Sylvie Lelitre <sylvie.lelitre@agrolait.com>', user_raoul.email)
        mail_new = TEMPLATE_MOD.format(to='Friendly Frogs <group+frogs@example.com>', subject='extra news', extra='', msg_id=test_msg_id)
        self.mail_thread.message_process(cr, uid, None, mail_new)
        new_mail = self.mail_message.browse(cr, uid, self.mail_message.search(cr, uid, [('message_id', '=', test_msg_id)])[0])
        # Test: author_id set, not email_from
        self.assertEqual(new_mail.author_id, user_raoul.partner_id, 'message process wrong author found')
        self.assertEqual(new_mail.email_from, user_raoul.email, 'message process wrong email_from')

        # Do: post a new message, with a unknown partner
        test_msg_id = '<deadcafe.1337-3@smtp.agrolait.com>'
        TEMPLATE_MOD = MAIL_TEMPLATE_PLAINTEXT.replace('Sylvie Lelitre <sylvie.lelitre@agrolait.com>', '_abcd_')
        mail_new = TEMPLATE_MOD.format(to='Friendly Frogs <group+frogs@example.com>', subject='super news', extra='', msg_id=test_msg_id)
        self.mail_thread.message_process(cr, uid, None, mail_new)
        new_mail = self.mail_message.browse(cr, uid, self.mail_message.search(cr, uid, [('message_id', '=', test_msg_id)])[0])
        # Test: author_id set, not email_from
        self.assertFalse(new_mail.author_id, 'message process shnould not have found a partner for _abcd_ email address')
        self.assertIn('_abcd_', new_mail.email_from, 'message process should set en email_from when not finding a partner_id')

    def test_05_thread_parent_resolution(self):
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
        self.mail_group.message_process(cr, uid, None, reply_msg)

        # 2. References header
        reply_msg2 = MAIL_TEMPLATE.format(to='Pretty Pigs <group+pigs@example.com>, other@gmail.com', subject='Re: Re: 1',
                                         extra='References: <2233@a.com>\r\n\t<3edss_dsa@b.com> %s' % msg1.message_id)
        self.mail_group.message_process(cr, uid, None, reply_msg2)

        # 3. Subject contains [<ID>] + model passed to message+process -> only attached to group, not to mail
        reply_msg3 = MAIL_TEMPLATE.format(to='Pretty Pigs <group+pigs@example.com>, other@gmail.com',
                                          extra='', subject='Re: [%s] 1' % self.group_pigs_id)
        self.mail_group.message_process(cr, uid, 'mail.group', reply_msg3)

        group_pigs.refresh()
        msg1.refresh()
        self.assertEqual(5, len(group_pigs.message_ids), 'group should contain 5 messages')
        self.assertEqual(2, len(msg1.child_ids), 'msg1 should have 2 children now')

    def test_10_followers_function_field(self):
        """ Tests designed for the many2many function field 'follower_ids'.
            We will test to perform writes using the many2many commands 0, 3, 4,
            5 and 6. """
        cr, uid, user_admin, partner_bert_id, group_pigs = self.cr, self.uid, self.user_admin, self.partner_bert_id, self.group_pigs

        # Data: create 'disturbing' values in mail.followers: same res_id, other res_model; same res_model, other res_id
        group_dummy_id = self.mail_group.create(cr, uid,
            {'name': 'Dummy group'}, {'mail_create_nolog': True})
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

    def test_11_message_followers_and_subtypes(self):
        """ Tests designed for the subscriber API as well as message subtypes """
        cr, uid, user_admin, user_raoul, group_pigs = self.cr, self.uid, self.user_admin, self.user_raoul, self.group_pigs
        # Data: message subtypes
        self.mail_message_subtype.create(cr, uid, {'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.group'})
        self.mail_message_subtype.create(cr, uid, {'name': 'mt_other_def', 'default': True, 'res_model': 'crm.lead'})
        self.mail_message_subtype.create(cr, uid, {'name': 'mt_all_def', 'default': True, 'res_model': False})
        mt_mg_nodef = self.mail_message_subtype.create(cr, uid, {'name': 'mt_mg_nodef', 'default': False, 'res_model': 'mail.group'})
        mt_all_nodef = self.mail_message_subtype.create(cr, uid, {'name': 'mt_all_nodef', 'default': False, 'res_model': False})
        default_group_subtypes = self.mail_message_subtype.search(cr, uid, [('default', '=', True), '|', ('res_model', '=', 'mail.group'), ('res_model', '=', False)])

        # ----------------------------------------
        # CASE1: test subscriptions with subtypes
        # ----------------------------------------

        # Do: Subscribe Raoul three times (niak niak) through message_subscribe_users
        group_pigs.message_subscribe_users([user_raoul.id, user_raoul.id])
        group_pigs.message_subscribe_users([user_raoul.id])
        group_pigs.refresh()
        # Test: 2 followers (Admin and Raoul)
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(set(follower_ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]), 'Admin and Raoul should be the only 2 Pigs fans')
        # Test: Raoul follows default subtypes
        fol_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id), ('partner_id', '=', user_raoul.partner_id.id)])
        fol_obj = self.mail_followers.browse(cr, uid, fol_ids)[0]
        fol_subtype_ids = set([subtype.id for subtype in fol_obj.subtype_ids])
        self.assertEqual(set(fol_subtype_ids), set(default_group_subtypes), 'subscription subtypes are incorrect')

        # Do: Unsubscribe Raoul twice through message_unsubscribe_users
        group_pigs.message_unsubscribe_users([user_raoul.id, user_raoul.id])
        group_pigs.refresh()
        # Test: 1 follower (Admin)
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(follower_ids, [user_admin.partner_id.id], 'Admin must be the only Pigs fan')

        # Do: subscribe Admin with subtype_ids
        group_pigs.message_subscribe_users([uid], [mt_mg_nodef, mt_all_nodef])
        fol_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id), ('partner_id', '=', user_admin.partner_id.id)])
        fol_obj = self.mail_followers.browse(cr, uid, fol_ids)[0]
        fol_subtype_ids = set([subtype.id for subtype in fol_obj.subtype_ids])
        self.assertEqual(set(fol_subtype_ids), set([mt_mg_nodef, mt_all_nodef]), 'subscription subtypes are incorrect')

        # ----------------------------------------
        # CASE2: test mail_thread fields
        # ----------------------------------------

        subtype_data = group_pigs._get_subscription_data(None, None)[group_pigs.id]['message_subtype_data']
        self.assertEqual(set(subtype_data.keys()), set(['Discussions', 'mt_mg_def', 'mt_all_def', 'mt_mg_nodef', 'mt_all_nodef']), 'mail.group available subtypes incorrect')
        self.assertFalse(subtype_data['Discussions']['followed'], 'Admin should not follow Discussions in pigs')
        self.assertTrue(subtype_data['mt_mg_nodef']['followed'], 'Admin should follow mt_mg_nodef in pigs')
        self.assertTrue(subtype_data['mt_all_nodef']['followed'], 'Admin should follow mt_all_nodef in pigs')

    def test_20_message_quote_context(self):
        """ Tests designed for message_post. """
        cr, uid, user_admin, group_pigs = self.cr, self.uid, self.user_admin, self.group_pigs

        msg1_id = self.mail_message.create(cr, uid, {'body': 'Thread header about Zap Brannigan', 'subject': 'My subject'})
        msg2_id = self.mail_message.create(cr, uid, {'body': 'First answer, should not be displayed', 'subject': 'Re: My subject', 'parent_id': msg1_id})
        msg3_id = self.mail_message.create(cr, uid, {'body': 'Second answer', 'subject': 'Re: My subject', 'parent_id': msg1_id})
        msg4_id = self.mail_message.create(cr, uid, {'body': 'Third answer', 'subject': 'Re: My subject', 'parent_id': msg1_id})
        msg_new_id = self.mail_message.create(cr, uid, {'body': 'My answer I am propagating', 'subject': 'Re: My subject', 'parent_id': msg1_id})

        result = self.mail_message.message_quote_context(cr, uid, msg_new_id, limit=3)
        self.assertIn('Thread header about Zap Brannigan', result, 'Thread header content should be in quote.')
        self.assertIn('Second answer', result, 'Answer should be in quote.')
        self.assertIn('Third answer', result, 'Answer should be in quote.')
        self.assertIn('expandable', result, 'Expandable should be present.')
        self.assertNotIn('First answer, should not be displayed', result, 'Old answer should not be in quote.')
        self.assertNotIn('My answer I am propagating', result, 'Thread header content should be in quote.')

    def test_21_message_post(self):
        """ Tests designed for message_post. """
        cr, uid, user_raoul, group_pigs = self.cr, self.uid, self.user_raoul, self.group_pigs
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a'})
        # 1 - Bert Tartopoils, with email, should receive emails for comments and emails
        p_b_id = self.res_partner.create(cr, uid, {'name': 'Bert Tartopoils', 'email': 'b@b'})
        # 2 - Carine Poilvache, with email, should never receive emails
        p_c_id = self.res_partner.create(cr, uid, {'name': 'Carine Poilvache', 'email': 'c@c', 'notification_email_send': 'email'})
        # 3 - Dédé Grosbedon, without email, to test email verification; should receive emails for every message
        p_d_id = self.res_partner.create(cr, uid, {'name': 'Dédé Grosbedon', 'notification_email_send': 'all'})

        # Subscribe Raoul, #1, #2
        group_pigs.message_subscribe([self.partner_raoul_id, p_b_id, p_c_id])

        # Mail data
        _subject = 'Pigs'
        _mail_subject = 'Re: %s' % (group_pigs.name)
        _body1 = '<p>Pigs rules</p>'
        _mail_body1 = '<p>Pigs rules</p>\n<div><p>Raoul</p></div>\n'
        _mail_bodyalt1 = 'Pigs rules\nRaoul\n'
        _body2 = '<html>Pigs rules</html>'
        _mail_body2 = '<div><p>Pigs rules</p></div>\n<div><p>Raoul</p></div>'
        _mail_bodyalt2 = 'Pigs rules\nRaoul'
        _attachments = [('First', 'My first attachment'), ('Second', 'My second attachment')]

        # ----------------------------------------
        # CASE1: post comment, body and subject specified
        # ----------------------------------------

        # 1. Post a new comment on Pigs
        self._init_mock_build_email()
        msg1_id = self.mail_group.message_post(cr, user_raoul.id, self.group_pigs_id, body=_body1, subject=_subject, type='comment', subtype='mt_comment')
        message1 = self.mail_message.browse(cr, uid, msg1_id)
        sent_emails = self._build_email_kwargs_list
        # Test: mail.mail notifications have been deleted
        self.assertFalse(self.mail_mail.search(cr, uid, [('mail_message_id', '=', msg1_id)]), 'mail.mail notifications should have been auto-deleted!')
        # Test: mail_message: subject is _subject, body is _body1 (no formatting done)
        self.assertEqual(message1.subject, _subject, 'mail.message subject incorrect')
        self.assertEqual(message1.body, _body1, 'mail.message body incorrect')
        # Test: sent_email: email send by server: correct subject, body, body_alternative
        self.assertEqual(len(sent_emails), 2, 'sent_email number of sent emails incorrect')
        for sent_email in sent_emails:
            self.assertEqual(sent_email['subject'], _subject, 'sent_email subject incorrect')
            self.assertTrue(sent_email['body'] in [_mail_body1 + '\nBert Tartopoils\n', _mail_body1 + '\nAdministrator\n'],
                'sent_email body incorrect')
            # the html2plaintext uses etree or beautiful soup, so the result may be slighly different
            # depending if you have installed beautiful soup.
            self.assertTrue(sent_email['body_alternative'] in [_mail_bodyalt1 + '\nBert Tartopoils\n', _mail_bodyalt1 + '\nAdministrator\n'],
                'sent_email body_alternative is incorrect')
        # Test: mail_message: notified_partner_ids = group followers
        message_pids = set([partner.id for partner in message1.notified_partner_ids])
        test_pids = set([self.partner_admin_id, p_b_id, p_c_id])
        self.assertEqual(test_pids, message_pids, 'mail.message notified partners incorrect')
        # Test: notification linked to this message = group followers = notified_partner_ids
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', msg1_id)])
        notif_pids = set([notif.partner_id.id for notif in self.mail_notification.browse(cr, uid, notif_ids)])
        self.assertEqual(notif_pids, test_pids, 'mail.message notification partners incorrect')
        # Test: sent_email: email_to should contain b@b, not c@c (pref email), not a@a (writer)
        for sent_email in sent_emails:
            self.assertTrue(set(sent_email['email_to']).issubset(set(['a@a', 'b@b'])), 'sent_email email_to is incorrect')

        # ----------------------------------------
        # CASE2: post an email with attachments, parent_id, partner_ids, parent notification
        # ----------------------------------------

        # 1. Post a new email comment on Pigs
        self._init_mock_build_email()
        msg2_id = self.mail_group.message_post(cr, user_raoul.id, self.group_pigs_id, body=_body2, type='email', subtype='mt_comment',
            partner_ids=[p_d_id], parent_id=msg1_id, attachments=_attachments,
            context={'mail_post_autofollow': True})
        message2 = self.mail_message.browse(cr, uid, msg2_id)
        sent_emails = self._build_email_kwargs_list
        self.assertFalse(self.mail_mail.search(cr, uid, [('mail_message_id', '=', msg2_id)]), 'mail.mail notifications should have been auto-deleted!')
        # Test: mail_message: subject is False, body is _body2 (no formatting done), parent_id is msg_id
        self.assertEqual(message2.subject, False, 'mail.message subject incorrect')
        self.assertEqual(message2.body, html_sanitize(_body2), 'mail.message body incorrect')
        self.assertEqual(message2.parent_id.id, msg1_id, 'mail.message parent_id incorrect')
        # Test: sent_email: email send by server: correct automatic subject, body, body_alternative
        self.assertEqual(len(sent_emails), 3, 'sent_email number of sent emails incorrect')
        for sent_email in sent_emails:
            self.assertEqual(sent_email['subject'], _mail_subject, 'sent_email subject incorrect')
            self.assertIn(_mail_body2, sent_email['body'], 'sent_email body incorrect')
            self.assertIn(_mail_bodyalt2, sent_email['body_alternative'], 'sent_email body_alternative incorrect')
        # Test: mail_message: notified_partner_ids = group followers
        message_pids = set([partner.id for partner in message2.notified_partner_ids])
        test_pids = set([self.partner_admin_id, p_b_id, p_c_id, p_d_id])
        self.assertEqual(message_pids, test_pids, 'mail.message partners incorrect')
        # Test: notifications linked to this message = group followers = notified_partner_ids
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', msg2_id)])
        notif_pids = set([notif.partner_id.id for notif in self.mail_notification.browse(cr, uid, notif_ids)])
        self.assertEqual(notif_pids, test_pids, 'mail.message notification partners incorrect')
        # Test: sent_email: email_to should contain b@b, c@c, not a@a (writer)
        for sent_email in sent_emails:
            self.assertTrue(set(sent_email['email_to']).issubset(set(['a@a', 'b@b', 'c@c'])), 'sent_email email_to incorrect')
        # Test: attachments
        for attach in message2.attachment_ids:
            self.assertEqual(attach.res_model, 'mail.group', 'mail.message attachment res_model incorrect')
            self.assertEqual(attach.res_id, self.group_pigs_id, 'mail.message attachment res_id incorrect')
            self.assertIn((attach.name, attach.datas.decode('base64')), _attachments,
                'mail.message attachment name / data incorrect')
        # Test: download attachments
        for attach in message2.attachment_ids:
            dl_attach = self.mail_message.download_attachment(cr, user_raoul.id, id_message=message2.id, attachment_id=attach.id)
            self.assertIn((dl_attach['filename'], dl_attach['base64'].decode('base64')), _attachments, 'mail.message download_attachment is incorrect')

        # 2. Dédé has been notified -> should also have been notified of the parent message
        message1.refresh()
        message_pids = set([partner.id for partner in message1.notified_partner_ids])
        test_pids = set([self.partner_admin_id, p_b_id, p_c_id, p_d_id])
        self.assertEqual(test_pids, message_pids, 'mail.message parent notification not created')

        # 3. Reply to the last message, check that its parent will be the first message
        msg3_id = self.mail_group.message_post(cr, user_raoul.id, self.group_pigs_id, body='Test', parent_id=msg2_id)
        message = self.mail_message.browse(cr, uid, msg3_id)
        self.assertEqual(message.parent_id.id, msg1_id, 'message_post did not flatten the thread structure')

    def test_25_message_compose_wizard(self):
        """ Tests designed for the mail.compose.message wizard. """
        cr, uid, user_admin, group_pigs = self.cr, self.uid, self.user_admin, self.group_pigs
        mail_compose = self.registry('mail.compose.message')
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a'})
        group_bird_id = self.mail_group.create(cr, uid, {'name': 'Bird', 'description': 'Bird resistance'}, {'mail_create_nolog': True})
        group_bird = self.mail_group.browse(cr, uid, group_bird_id)

        # Mail data
        _subject = 'Pigs'
        _body = 'Pigs <b>rule</b>'
        _reply_subject = 'Re: Pigs'
        _attachments = [
            {'name': 'First', 'datas_fname': 'first.txt', 'datas': 'My first attachment'.encode('base64')},
            {'name': 'Second', 'datas_fname': 'second.txt', 'datas': 'My second attachment'.encode('base64')}
            ]
        _attachments_test = [('first.txt', 'My first attachment'), ('second.txt', 'My second attachment')]

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
            {'subject': _subject, 'body': _body, 'partner_ids': [(4, p_c_id), (4, p_d_id)]},
            {'default_composition_mode': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_pigs_id,
             'default_content_subtype': 'plaintext'})
        compose = mail_compose.browse(cr, uid, compose_id)
        # Test: mail.compose.message: composition_mode, model, res_id
        self.assertEqual(compose.composition_mode,  'comment', 'mail.compose.message incorrect composition_mode')
        self.assertEqual(compose.model,  'mail.group', 'mail.compose.message incorrect model')
        self.assertEqual(compose.res_id, self.group_pigs_id, 'mail.compose.message incorrect res_id')

        # 2. Post the comment, get created message
        mail_compose.send_mail(cr, uid, [compose_id], {'mail_post_autofollow': True})
        group_pigs.refresh()
        message = group_pigs.message_ids[0]
        # Test: mail.message: subject, body inside pre
        self.assertEqual(message.subject,  _subject, 'mail.message incorrect subject')
        self.assertEqual(message.body, '<p>%s</p>' % _body, 'mail.message incorrect body')
        # Test: mail.message: notified_partner_ids = entries in mail.notification: group_pigs fans (a, b) + mail.compose.message partner_ids (c, d)
        msg_pids = [partner.id for partner in message.notified_partner_ids]
        test_pids = [p_b_id, p_c_id, p_d_id]
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', message.id)])
        self.assertEqual(len(notif_ids), 3, 'mail.message: too much notifications created')
        self.assertEqual(set(msg_pids), set(test_pids), 'mail.message notified_partner_ids incorrect')

        # ----------------------------------------
        # CASE2: reply to last comment with attachments
        # ----------------------------------------

        # 1. Update last comment subject, reply with attachments
        message.write({'subject': _subject})
        compose_id = mail_compose.create(cr, uid,
            {'attachment_ids': [(0, 0, _attachments[0]), (0, 0, _attachments[1])]},
            {'default_composition_mode': 'reply', 'default_model': 'mail.thread', 'default_res_id': self.group_pigs_id, 'default_parent_id': message.id})
        compose = mail_compose.browse(cr, uid, compose_id)
        # Test: model, res_id, parent_id
        self.assertEqual(compose.model,  'mail.group', 'mail.compose.message incorrect model')
        self.assertEqual(compose.res_id, self.group_pigs_id, 'mail.compose.message incorrect res_id')
        self.assertEqual(compose.parent_id.id, message.id, 'mail.compose.message incorrect parent_id')
        # Test: mail.message: subject as Re:.., body in html, parent_id
        self.assertEqual(compose.subject, _reply_subject, 'mail.message incorrect subject')
        # self.assertIn('Administrator wrote:<blockquote><pre>Pigs rules</pre></blockquote>', compose.body, 'mail.message body is incorrect')
        self.assertEqual(compose.parent_id and compose.parent_id.id, message.id, 'mail.message parent_id incorrect')
        # Test: mail.message: attachments
        for attach in compose.attachment_ids:
            self.assertIn((attach.datas_fname, attach.datas.decode('base64')), _attachments_test, 'mail.message attachment name / data incorrect')

        # ----------------------------------------
        # CASE3: mass_mail on Pigs and Bird
        # ----------------------------------------

        # 1. mass_mail on pigs and bird
        compose_id = mail_compose.create(cr, uid,
            {'subject': _subject, 'body': '${object.description}'},
            {'default_composition_mode': 'mass_mail', 'default_model': 'mail.group', 'default_res_id': False,
                'active_ids': [self.group_pigs_id, group_bird_id]})
        compose = mail_compose.browse(cr, uid, compose_id)

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
        self.assertEqual(message1.body, '<p>%s</p>' % group_pigs.description, 'mail.message body incorrect')
        self.assertEqual(message2.subject, _subject, 'mail.message subject incorrect')
        self.assertEqual(message2.body, '<p>%s</p>' % group_bird.description, 'mail.message body incorrect')

    def test_30_needaction(self):
        """ Tests for mail.message needaction. """
        cr, uid, user_admin, user_raoul, group_pigs = self.cr, self.uid, self.user_admin, self.user_raoul, self.group_pigs
        group_pigs_demo = self.mail_group.browse(cr, self.user_raoul_id, self.group_pigs_id)
        na_admin_base = self.mail_message._needaction_count(cr, uid, domain=[])
        na_demo_base = self.mail_message._needaction_count(cr, user_raoul.id, domain=[])

        # Test: number of unread notification = needaction on mail.message
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_admin.partner_id.id),
            ('read', '=', False)
            ])
        na_count = self.mail_message._needaction_count(cr, uid, domain=[])
        self.assertEqual(len(notif_ids), na_count, 'unread notifications count does not match needaction count')

        # Do: post 2 message on group_pigs as admin, 3 messages as demo user
        for dummy in range(2):
            group_pigs.message_post(body='My Body', subtype='mt_comment')
        for dummy in range(3):
            group_pigs_demo.message_post(body='My Demo Body', subtype='mt_comment')

        # Test: admin has 3 new notifications (from demo), and 3 new needaction
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_admin.partner_id.id),
            ('read', '=', False)
            ])
        self.assertEqual(len(notif_ids), na_admin_base + 3, 'Admin should have 3 new unread notifications')
        na_admin = self.mail_message._needaction_count(cr, uid, domain=[])
        na_admin_group = self.mail_message._needaction_count(cr, uid, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)])
        self.assertEqual(na_admin, na_admin_base + 3, 'Admin should have 3 new needaction')
        self.assertEqual(na_admin_group, 3, 'Admin should have 3 needaction related to Pigs')
        # Test: demo has 0 new notifications (not a follower, not receiving its own messages), and 0 new needaction
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_raoul.partner_id.id),
            ('read', '=', False)
            ])
        self.assertEqual(len(notif_ids), na_demo_base + 0, 'Demo should have 0 new unread notifications')
        na_demo = self.mail_message._needaction_count(cr, user_raoul.id, domain=[])
        na_demo_group = self.mail_message._needaction_count(cr, user_raoul.id, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)])
        self.assertEqual(na_demo, na_demo_base + 0, 'Demo should have 0 new needaction')
        self.assertEqual(na_demo_group, 0, 'Demo should have 0 needaction related to Pigs')

    def test_40_track_field(self):
        """ Testing auto tracking of fields. """
        def _strip_string_spaces(body):
            return body.replace(' ', '').replace('\n', '')

        # Data: subscribe Raoul to Pigs, because he will change the public attribute and may loose access to the record
        cr, uid = self.cr, self.uid
        self.mail_group.message_subscribe_users(cr, uid, [self.group_pigs_id], [self.user_raoul_id])

        # Data: res.users.group, to test group_public_id automatic logging
        group_system_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_system')
        group_system_id = group_system_ref and group_system_ref[1] or False

        # Data: custom subtypes
        mt_private_id = self.mail_message_subtype.create(cr, uid, {'name': 'private', 'description': 'Private public'})
        self.ir_model_data.create(cr, uid, {'name': 'mt_private', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_private_id})
        mt_name_supername_id = self.mail_message_subtype.create(cr, uid, {'name': 'name_supername', 'description': 'Supername name'})
        self.ir_model_data.create(cr, uid, {'name': 'mt_name_supername', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_name_supername_id})
        mt_group_public_id = self.mail_message_subtype.create(cr, uid, {'name': 'group_public', 'description': 'Group changed'})
        self.ir_model_data.create(cr, uid, {'name': 'mt_group_public', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_group_public_id})

        # Data: alter mail_group model for testing purposes (test on classic, selection and many2one fields)
        self.mail_group._track = {
            'public': {
                'mail.mt_private': lambda self, cr, uid, obj, ctx=None: obj['public'] == 'private',
            },
            'name': {
                'mail.mt_name_supername': lambda self, cr, uid, obj, ctx=None: obj['name'] == 'supername',
            },
            'group_public_id': {
                'mail.mt_group_public': lambda self, cr, uid, obj, ctx=None: True,
            },
        }
        public_col = self.mail_group._columns.get('public')
        name_col = self.mail_group._columns.get('name')
        group_public_col = self.mail_group._columns.get('group_public_id')
        public_col.track_visibility = 'onchange'
        name_col.track_visibility = 'always'
        group_public_col.track_visibility = 'onchange'

        # Test: change name -> always tracked, not related to a subtype
        self.mail_group.write(cr, self.user_raoul_id, [self.group_pigs_id], {'public': 'public'})
        self.group_pigs.refresh()
        self.assertEqual(len(self.group_pigs.message_ids), 1, 'tracked: a message should have been produced')
        # Test: first produced message: no subtype, name change tracked
        last_msg = self.group_pigs.message_ids[-1]
        self.assertFalse(last_msg.subtype_id, 'tracked: message should not have been linked to a subtype')
        self.assertIn(u'SelectedGroupOnly\u2192Public', _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')
        self.assertIn('Pigs', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')

        # Test: change name as supername, public as private -> 2 subtypes
        self.mail_group.write(cr, self.user_raoul_id, [self.group_pigs_id], {'name': 'supername', 'public': 'private'})
        self.group_pigs.refresh()
        self.assertEqual(len(self.group_pigs.message_ids), 3, 'tracked: two messages should have been produced')
        # Test: first produced message: mt_name_supername
        last_msg = self.group_pigs.message_ids[-2]
        self.assertEqual(last_msg.subtype_id.id, mt_private_id, 'tracked: message should be linked to mt_private subtype')
        self.assertIn('Private public', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u'Pigs\u2192supername', _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')
        # Test: second produced message: mt_name_supername
        last_msg = self.group_pigs.message_ids[-3]
        self.assertEqual(last_msg.subtype_id.id, mt_name_supername_id, 'tracked: message should be linked to mt_name_supername subtype')
        self.assertIn('Supername name', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u'Public\u2192Private', _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')
        self.assertIn(u'Pigs\u2192supername', _strip_string_spaces(last_msg.body), 'tracked feature: message body does not hold always tracked field')

        # Test: change public as public, group_public_id -> 1 subtype, name always tracked
        self.mail_group.write(cr, self.user_raoul_id, [self.group_pigs_id], {'public': 'public', 'group_public_id': group_system_id})
        self.group_pigs.refresh()
        self.assertEqual(len(self.group_pigs.message_ids), 4, 'tracked: one message should have been produced')
        # Test: first produced message: mt_group_public_id, with name always tracked, public tracked on change
        last_msg = self.group_pigs.message_ids[-4]
        self.assertEqual(last_msg.subtype_id.id, mt_group_public_id, 'tracked: message should not be linked to any subtype')
        self.assertIn('Group changed', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u'Private\u2192Public', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold changed tracked field')
        self.assertIn(u'HumanResources/Employee\u2192Administration/Settings', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')

        # Test: change not tracked field, no tracking message
        self.mail_group.write(cr, self.user_raoul_id, [self.group_pigs_id], {'description': 'Dummy'})
        self.group_pigs.refresh()
        self.assertEqual(len(self.group_pigs.message_ids), 4, 'tracked: No message should have been produced')

        # Data: removed changes
        public_col.track_visibility = None
        name_col.track_visibility = None
        group_public_col.track_visibility = None
        self.mail_group._track = {}
