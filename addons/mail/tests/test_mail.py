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

from openerp.tests import common
import tools

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

class test_mail(common.TransactionCase):

    def _mock_smtp_gateway(self, *args, **kwargs):
        return True

    def _mock_build_email(self, *args, **kwargs):
        self._build_email_args = args
        self._build_email_kwargs = kwargs
        return self.build_email_real(*args, **kwargs)

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

        # Install mock SMTP gateway
        self.build_email_real = self.registry('ir.mail_server').build_email
        self.registry('ir.mail_server').build_email = self._mock_build_email
        self.registry('ir.mail_server').send_email = self._mock_smtp_gateway

        # groups@.. will cause the creation of new mail groups
        self.mail_group_model_id = self.ir_model.search(self.cr, self.uid, [('model','=', 'mail.group')])[0]
        self.mail_alias.create(self.cr, self.uid, {'alias_name': 'groups',
                                                   'alias_model_id': self.mail_group_model_id})
        
        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

    def test_00_message_process(self):
        cr, uid = self.cr, self.uid
        # Incoming mail creates a new mail_group "frogs"
        self.assertEqual(self.mail_group.search(cr, uid, [('name','=','frogs')]), [])
        mail_frogs = MAIL_TEMPLATE.format(to='groups@example.com, other@gmail.com', subject='frogs', extra='')
        self.mail_thread.message_process(cr, uid, None, mail_frogs)
        frog_groups = self.mail_group.search(cr, uid, [('name','=','frogs')])
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
                                          extra='In-Reply-To: <12321321-openerp-%d-mail.group@example.com>\n'%frog_group.id)
        self.mail_thread.message_process(cr, uid, None, mail_reply)
        frog_group.refresh()
        self.assertTrue(len(frog_group.message_ids) == 3, 'Group should contain 3 messages now')
        
        # No model passed and no matching alias must raise
        mail_spam = MAIL_TEMPLATE.format(to='noone@example.com', subject='spam', extra='')
        self.assertRaises(Exception,
                          self.mail_thread.message_process,
                          cr, uid, None, mail_spam)

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
        self.assertEqual(follower_ids,set([partner_bert_id, user_admin.partner_id.id]), 'Bert and Admin should be the followers of dummy mail.group data')

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
        _mail_body2 = '<html>Pigs rules\n<pre>Admin</pre>\n</html>'
        _mail_bodyalt2 = 'Pigs rules\nAdmin\n'

        # Post comment with body and subject, comment preference
        msg_id = self.mail_group.message_post(cr, uid, self.group_pigs_id, body=_body1, subject=_subject, msg_type='comment')
        # Fetch: created mail_message, mail_mail, sent_email
        message = self.mail_message.browse(cr, uid, msg_id)
        mail_ids = self.mail_mail.search(cr, uid, [], limit=1)
        mail = self.mail_mail.browse(cr, uid, mail_ids[0])
        sent_email = self._build_email_kwargs
        
        # Test: mail_message: subject is _subject, body is _body1 (no formatting done)
        self.assertEqual(message.subject, _subject, 'mail.message subject incorrect')
        self.assertEqual(message.body, _body1, 'mail.message body incorrect')
        # Test: mail_mail: subject is _subject, body_html is _mail_body1 (signature appended)
        self.assertEqual(mail.subject, _subject, 'mail.mail subject incorrect')
        self.assertEqual(mail.body_html, _mail_body1, 'mail.mail body_html incorrect')
        self.assertEqual(mail.mail_message_id.id, msg_id, 'mail_mail.mail_message_id is not the id of its related mail_message)')
        # Test: sent_email: email send by server: correct subject and body
        self.assertEqual(sent_email['subject'], _subject, 'sent_email subject incorrect')
        self.assertEqual(sent_email['body'], _mail_body1, 'sent_email body incorrect')
        self.assertEqual(sent_email['body_alternative'], _mail_bodyalt1, 'sent_email body_alternative is incorrect')
        # Test: mail_message: partner_ids = group followers
        message_pids = set([partner.id for partner in message.partner_ids])
        test_pids = set([p_a_id, p_b_id, p_c_id])
        self.assertEqual(test_pids, message_pids, 'mail.message partners incorrect')
        # Test: notification linked to this message = group followers = partner_ids
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', message.id)])
        notif_pids = set([notif.partner_id.id for notif in self.mail_notification.browse(cr, uid, notif_ids)])
        self.assertEqual(notif_pids, test_pids, 'mail.message notification partners incorrect')
        # Test: sent_email: email_to should contain b@b, not c@c (pref email), not a@a (writer)
        self.assertEqual(sent_email['email_to'], ['b@b'], 'sent_email email_to is incorrect')

        # New post: test automatic subject, signature in html, add a partner, email preference, parent_id previous message
        msg_id2 = self.mail_group.message_post(cr, uid, self.group_pigs_id, body=_body2, msg_type='email', partner_ids=[(6, 0, [p_d_id])], parent_id=msg_id)
        # Fetch: created mail_message, mail_mail, sent_email
        message = self.mail_message.browse(cr, uid, msg_id2)
        mail_ids = self.mail_mail.search(cr, uid, [], limit=1)
        mail = self.mail_mail.browse(cr, uid, mail_ids[0])
        sent_email = self._build_email_kwargs

        # Test: mail_message: subject is False, body is _body1 (no formatting done), parent_id is msg_id
        self.assertEqual(message.subject, False, 'mail.message subject incorrect')
        self.assertEqual(message.body, _body2, 'mail.message body incorrect')
        self.assertEqual(message.parent_id.id, msg_id, 'mail.message parent_id incorrect')
        # Test: mail_mail: subject is False, body_html is _mail_body1 (signature appended)
        self.assertEqual(mail.subject, False, 'mail.mail subject is incorrect')
        self.assertEqual(mail.body_html, _mail_body2, 'mail.mail body_html incorrect')
        self.assertEqual(mail.mail_message_id.id, msg_id2, 'mail_mail.mail_message_id incorrect')
        # Test: sent_email: email send by server: correct subject and body
        self.assertEqual(sent_email['subject'], _mail_subject, 'sent_email subject incorrect')
        self.assertEqual(sent_email['body'], _mail_body2, 'sent_email body incorrect')
        self.assertEqual(sent_email['body_alternative'], _mail_bodyalt2, 'sent_email body_alternative incorrect')
        # Test: mail_message: partner_ids = group followers
        message_pids = set([partner.id for partner in message.partner_ids])
        test_pids = set([p_a_id, p_b_id, p_c_id, p_d_id])
        self.assertEqual(message_pids, test_pids, 'mail.message partners incorrect')
        # Test: notification linked to this message = group followers = partner_ids
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', message.id)])
        notif_pids = set([notif.partner_id.id for notif in self.mail_notification.browse(cr, uid, notif_ids)])
        self.assertEqual(notif_pids, test_pids, 'mail.message notification partners incorrect')
        # Test: sent_email: email_to should contain b@b, c@c, not a@a (writer)
        self.assertEqual(set(sent_email['email_to']), set(['b@b', 'c@c']), 'sent_email email_to incorrect')

    def test_21_message_post_attachments(self):
        """ Tests designed for attachments. """

    def test_22_message_compose_wizard(self):
        """ Tests designed for the mail.compose.message wizard. """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a'})
        user_admin = self.res_users.browse(cr, uid, uid)
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Mail data
        _subject = 'Pigs'
        _mail_subject = '%s posted on %s' % (user_admin.name, group_pigs.name)
        _body_text = 'Pigs rules'
        _msg_body1 = '<pre>Pigs rules</pre>'
        _body_html = '<html>Pigs rules</html>'
        _msg_body2 = '<html>Pigs rules</html>'

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

        # Comment group_pigs: body_text
        compose_id = mail_compose.create(cr, uid,
            {'subject': _subject, 'body_text': _body_text, 'partner_ids': [(4, p_c_id), (4, p_d_id)]},
            {'mail.compose.message.mode': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_pigs_id})
        compose = mail_compose.browse(cr, uid, compose_id)

        # Test: model, res_id
        self.assertTrue(compose.model == 'mail.group' and compose.res_id == self.group_pigs_id,
            'mail.compose.message has model %s and res_id %s; should be mail.group and %s' % (compose.model, compose.res_id, self.group_pigs_id))

        # Post the comment, get created message
        mail_compose.send_mail(cr, uid, [compose_id])
        group_pigs.refresh()
        msg = group_pigs.message_ids[0]

        # Test: mail.message: subject, body inside pre
        self.assertTrue(msg.subject == False and msg.body == _msg_body1,
            'mail.message subject is %s, body is %s; should be %s and %s' % (msg.subject, msg.body, False, _msg_body1))
        # Test: mail.message partners = notified people: group_pigs followers (a, b) + mail.compose.message partner_ids (c, d)
        msg_pids = [partner.id for partner in msg.partner_ids]
        test_pids = [p_a_id, p_b_id, p_c_id, p_d_id]
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', msg.id)])
        self.assertTrue(len(msg_pids) == 4, 'There are %s partners linked to the newly posted comment; should be 4' % (len(msg_pids)))
        self.assertTrue(len(notif_ids) == 4, 'There are %s entries in mail_notification: should be 4' % (len(notif_ids)))
        self.assertTrue(all(id in msg_pids for id in test_pids) and len(msg_pids) == len(test_pids),
            'Admin, Bert Raoul and Roger should be the 4 partners of the newly created message')

        # Create a reply to the last comment
        compose_id = mail_compose.create(cr, uid,
            {}, {'mail.compose.message.mode': 'reply', 'default_model': 'mail.thread', 'default_res_id': self.group_pigs_id,
                'active_id': msg.id})
        compose = mail_compose.browse(cr, uid, compose_id)

        # Test: model, res_id, parent_id
        self.assertTrue(compose.model == 'mail.group' and compose.res_id == self.group_pigs_id,
            'Wizard message has model: %s and res_id:%s; should be mail.group and %s' % (compose.model, compose.res_id, self.group_pigs_id))
        self.assertEqual(compose.parent_id.id, msg.id,
            'Wizard parent_id is %d; should be %d' % (compose.parent_id.id, msg.id))

        # 3 - Create in mass_mail composition mode that should work with or without email_template installed
        compose_id = mail_compose.create(cr, uid,
            {'subject': _subject, 'body': '${object.description}'},
            {'default_composition_mode': 'mass_mail', 'default_model': 'mail.group', 'default_res_id': -1,
                'active_ids': [self.group_pigs_id]})
        compose = mail_compose.browse(cr, uid, compose_id)

        # Post the comment, get created message
        mail_compose.send_mail(cr, uid, [compose_id], {'default_res_id': -1, 'active_ids': [self.group_pigs_id]})
        group_pigs.refresh()
        msg = group_pigs.message_ids[0]

        # Test: last message on Pigs = last created message
        test_msg = self.mail_message.browse(cr, uid, self.mail_message.search(cr, uid, [], limit=1))[0]
        self.assertEqual(msg.id, test_msg.id, 'Pigs did not receive its mass mailing message')
        # Test: mail.message: subject, body
        self.assertEqual(msg.subject, _subject, 'mail.message subject is incorrect')
        self.assertEqual(msg.body, group_pigs.description, 'mail.message body is incorrect')


    def test_30_message_read(self):
        """ Tests designed for message_read. """
        def _simplify_struct(read_dict):
            res = []
            for val in read_dict:
                current = {'_id': val['id']}
                if val.get('child_ids'):
                    current['child_ids'] = _simplify_struct(val.get('child_ids'))
                res.append(current)
            return res

        # TDE NOTE: this test is not finished, as the message_read method is not fully specified.
        # It wil be updated as soon as we have fixed specs !
        cr, uid  = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Test message_read_tree_flatten that flattens a thread according to a given thread_level
        import copy
        tree = [
            {'id': 1, 'child_ids':[
                {'id': 3, 'child_ids': [] },
                {'id': 4, 'child_ids': [
                    {'id': 5, 'child_ids': []},
                    {'id': 12, 'child_ids': []},
                    ] },
                {'id': 8, 'child_ids': [
                    {'id': 10, 'child_ids': []},
                    ] },
                ] },
            {'id': 2, 'child_ids': [
                {'id': 7, 'child_ids': [
                    {'id': 9, 'child_ids': []},
                    ] },
                ] },
            {'id': 6, 'child_ids': [
                {'id': 11, 'child_ids': [] },
                ] },
            ]
        new_tree = self.mail_message.message_read_tree_flatten(cr, uid, copy.deepcopy(tree), 0, 0)
        # self.mail_message._debug_print_tree(new_tree)
        # print '-------------------'
        self.assertTrue(len(new_tree) == 12, 'Flattening wrongly produced')
        new_tree = self.mail_message.message_read_tree_flatten(cr, uid, copy.deepcopy(tree), 0, 1)
        # self.mail_message._debug_print_tree(new_tree)
        # print '-------------------'
        self.assertTrue(len(new_tree) == 3 and len(new_tree[0]['child_ids']) == 6 and len(new_tree[1]['child_ids']) == 2 and len(new_tree[2]['child_ids']) == 1,
            'Flattening wrongly produced')
        new_tree = self.mail_message.message_read_tree_flatten(cr, uid, copy.deepcopy(tree), 0, 2)
        # self.mail_message._debug_print_tree(new_tree)
        # print '-------------------'
        self.assertTrue(len(new_tree) == 3 and len(new_tree[0]['child_ids']) == 3 and len(new_tree[0]['child_ids'][1]) == 2,
            'Flattening wrongly produced')

        # Add a few messages to pigs group
        msgid1 = group_pigs.message_post(body='My Body', subject='1', parent_id=False)
        msgid2 = group_pigs.message_post(body='My Body', subject='1-1', parent_id=msgid1)
        msgid3 = group_pigs.message_post(body='My Body', subject='1-2', parent_id=msgid1)
        msgid4 = group_pigs.message_post(body='My Body', subject='2', parent_id=False)
        msgid5 = group_pigs.message_post(body='My Body', subject='1-1-1', parent_id=msgid2)
        msgid6 = group_pigs.message_post(body='My Body', subject='2-1', parent_id=msgid4)

        # First try: read flat
        first_try_ids = [msgid6, msgid5, msgid4, msgid3, msgid2, msgid1]
        tree = self.mail_message.message_read(cr, uid, ids=False, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)], thread_level=0)
        self.assertTrue(all(elem['id'] in first_try_ids for elem in tree) and len(tree) == 6,
            'Incorrect structure and/or number of childs in purely flat message_read')

        # Second try: read with thread_level 1
        tree = self.mail_message.message_read(cr, uid, ids=False, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)], thread_level=1)
        # self.mail_message._debug_print_tree(tree)
        self.assertTrue(len(tree) == 2 and len(tree[1]['child_ids']) == 3, 'Incorrect number of child in message_read')

        # Third try: read with thread_level 2
        tree = self.mail_message.message_read(cr, uid, ids=False, domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)], thread_level=2)
        # self.mail_message._debug_print_tree(tree)
        self.assertTrue(len(tree) == 2 and len(tree[1]['child_ids']) == 2 and len(tree[1]['child_ids'][0]['child_ids']) == 1, 'Incorrect number of child in message_read')

    def test_40_needaction(self):
        """ Tests for mail.message needaction. """
        cr, uid  = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        user_admin = self.res_users.browse(cr, uid, uid)

        # Demo values: check unread notification = needaction on mail.message
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_admin.partner_id.id),
            ('read', '=', False)
            ])
        na_count = self.mail_message._needaction_count(cr, uid, domain = [])
        self.assertEqual(len(notif_ids), na_count,
            'Number of unread notifications (%s) does not match the needaction count (%s)' % (len(notif_ids), na_count))

        # Post 4 message on group_pigs
        for dummy in range(4):
            group_pigs.message_post(body='My Body')

        # Check there are 4 new needaction on mail.message
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_admin.partner_id.id),
            ('read', '=', False)
            ])
        na_count = self.mail_message._needaction_count(cr, uid, domain = [])
        self.assertEqual(len(notif_ids), na_count,
            'Number of unread notifications after posting messages (%s) does not match the needaction count (%s)' % (len(notif_ids), na_count))

        # Check there are 4 needaction on mail.message with particular domain
        na_count = self.mail_message._needaction_count(cr, uid, domain = [('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)])
        self.assertEqual(na_count, 4,
            'Number of posted message (4) does not match the needaction count with domain mail.group - group pigs (%s)' % (na_count))

    def test_50_thread_parent_resolution(self):
        """Verify parent/child relationships are correctly established when processing incoming mails"""
        cr, uid = self.cr, self.uid
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        msg1 = group_pigs.message_post(body='My Body', subject='1')
        msg2 = group_pigs.message_post(body='My Body', subject='2')
        msg1, msg2 = self.mail_message.browse(cr, uid, [msg1,msg2])
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
