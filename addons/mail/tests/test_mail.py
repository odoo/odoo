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
        self.registry('ir.mail_server').send_email = lambda *a,**kwargs: True

        # groups@.. will cause the creation of new mail groups
        self.mail_group_model_id = self.ir_model.search(self.cr, self.uid, [('model','=', 'mail.group')])[0]
        self.mail_alias.create(self.cr, self.uid, {'alias_name': 'groups',
                                                   'alias_model_id': self.mail_group_model_id})
        
        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid, {'name': 'pigs'})

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
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 1,
            'Newly created group should have only 1 follower')
        self.assertTrue(user_admin.partner_id.id in follower_ids,
            'Admin should be the only Pigs group follower')

        # Subscribe Bert through a '4' command
        group_pigs.write({'message_follower_ids': [(4, partner_bert_id)]})
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 2,
            'Pigs group should have 2 followers after linking Bert')
        self.assertTrue(all(id in follower_ids for id in [partner_bert_id, user_admin.partner_id.id]),
            'Bert and Admin should be the 2 Pigs group followers')

        # Unsubscribe Bert through a '3' command
        group_pigs.write({'message_follower_ids': [(3, partner_bert_id)]})
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 1,
            'Pigs group should have 1 follower after unlinking Bert')
        self.assertTrue(all(id in follower_ids for id in [user_admin.partner_id.id]),
            'Admin should be the only Pigs group follower')

        # Set followers through a '6' command
        group_pigs.write({'message_follower_ids': [(6, 0, [partner_bert_id])]})
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 1,
            'Pigs group should have 1 follower after replacing followers')
        self.assertTrue(follower_ids == [partner_bert_id],
            'Bert should be the only Pigs group follower')

        # Add a follower created on the fly through a '0' command
        group_pigs.write({'message_follower_ids': [(0, 0, {'name': 'Patrick Fiori'})]})
        partner_patrick_id = self.res_partner.search(cr, uid, [('name', '=', 'Patrick Fiori')])[0]
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 2,
            'Pigs group should have 2 followers after linking to new partner')
        self.assertTrue(all(id in follower_ids for id in [partner_bert_id, partner_patrick_id]),
            'Bert and Patrick should be Pigs group followers')

        # Finally, unlink through a '5' command
        group_pigs.write({'message_follower_ids': [(5, 0)]})
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 0,
            'Pigs group should not have followers anymore')

        # Test dummy data has not been altered
        fol_obj_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.thread'), ('res_id', '=', self.group_pigs_id)])
        follower_ids = [follower.partner_id.id for follower in self.mail_followers.browse(cr, uid, fol_obj_ids)]
        self.assertTrue(len(follower_ids) == 1,
            'mail.thread dummy data should have 1 follower')
        self.assertTrue(follower_ids[0] == partner_bert_id,
            'Bert should be the follower of dummy mail.thread data')
        fol_obj_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', group_dummy_id)])
        follower_ids = [follower.partner_id.id for follower in self.mail_followers.browse(cr, uid, fol_obj_ids)]
        self.assertTrue(len(follower_ids) == 2,
            'mail.group dummy data should have 2 followers')
        self.assertTrue(all(id in follower_ids for id in [partner_bert_id, user_admin.partner_id.id]),
            'Bert and Admin should be the followers of dummy mail.group data')

    def test_11_message_followers(self):
        """ Tests designed for the subscriber API. """
        cr, uid = self.cr, self.uid
        user_admin = self.res_users.browse(cr, uid, uid)
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Create user Raoul
        user_raoul_id = self.res_users.create(cr, uid, {'name': 'Raoul Grosbedon', 'login': 'raoul'})
        user_raoul = self.res_users.browse(cr, uid, user_raoul_id)

        # Subscribe Raoul twice (niak niak) through message_subscribe_users
        group_pigs.message_subscribe_users([user_raoul_id, user_raoul_id])
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 2,
            'Pigs group should have 2 followers after having subscribed Raoul. Subscribing twice '\
            'the same user should create only one follower.')
        self.assertTrue(all(id in follower_ids for id in [user_raoul.partner_id.id, user_admin.partner_id.id]),
            'Admin and Raoul should be the 2 Pigs group followers')

        # Unsubscribe Raoul twice through message_unsubscribe_users
        group_pigs.message_unsubscribe_users([user_raoul_id, user_raoul_id])
        group_pigs.refresh()
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertTrue(len(follower_ids) == 1,
            'Pigs group should have 1 follower after unsubscribing Raoul')
        self.assertTrue(all(id in follower_ids for id in [user_admin.partner_id.id]),
            'Admin the only Pigs group followers')

    def test_20_message_post_and_compose(self):
        """ Tests designed for message_post and the mail.compose.message wizard. """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')
        user_admin = self.res_users.browse(cr, uid, uid)
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin'})
        user_admin.refresh()
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Mail data
        _subject = 'Pigs'
        _mail_subject = '%s posted a comment on %s' % (user_admin.name, group_pigs.name)
        _body_text = 'Pigs rules'
        _body_html = '<b>Pigs</b> rules'

        # Create partners
        # 0 - Create an email address for Admin, to check email sending
        self.res_users.write(cr, uid, [uid], {'email': 'a@a'})
        # 1 - Bert Tartopoils, with email, should receive emails for comments and emails
        partner_bert_id = self.res_partner.create(cr, uid, {'name': 'Bert Tartopoils', 'email': 'b@b'})
        # 2 - Raoul Grosbedon, without email, to test email verification; should receive emails for every message
        partner_raoul_id = self.res_partner.create(cr, uid, {'name': 'Raoul Grosbedon', 'notification_email_pref': 'all'})
        # 3 - Roger Poilvache, with email, should never receive emails
        partner_roger_id = self.res_partner.create(cr, uid, {'name': 'Roger Poilvache', 'email': 'r@r', 'notification_email_pref': 'none'})

        # Create a new comment on group_pigs
        compose_id = mail_compose.create(cr, uid,
            {'subject': _subject, 'body_text': _body_text, 'partner_ids': [(4, partner_bert_id), (4, partner_raoul_id), (4, partner_roger_id)]},
            {'mail.compose.message': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_pigs_id})
        compose = mail_compose.browse(cr, uid, compose_id)
        self.assertTrue(compose.model == 'mail.group' and compose.res_id == self.group_pigs_id,
            'Wizard message has model %s and res_id %s; should be mail.group and %s' % (compose.model, compose.res_id, self.group_pigs_id))

        # Post the comment, get created message
        mail_compose.send_mail(cr, uid, [compose_id])
        group_pigs.refresh()
        first_com = group_pigs.message_ids[0]

        # Check message content
        self.assertTrue(first_com.subject == False and first_com.body == _body_text,
            'Posted comment subject is %s and body is %s; should be False and %s' % (first_com.subject, first_com.body, _body_text))

        # Message partners = notified people = writer + partner_ids
        first_com_pids = [partner.id for partner in first_com.partner_ids]
        notif_ids = self.mail_notification.search(cr, uid, [('message_id', '=', first_com.id)])
        self.assertTrue(len(first_com_pids) == 4, 'There are %s partners linked to the newly posted comment; should be 4' % (len(first_com_pids)))
        self.assertTrue(len(notif_ids) == 4, 'There are %s entries in mail_notification: should be 4' % (len(notif_ids)))
        self.assertTrue(all(id in [user_admin.partner_id.id, partner_bert_id, partner_raoul_id, partner_roger_id] for id in first_com_pids),
            'Admin, Bert Raoul and Roger should be the 4 partners of the newly created message')

        # Fetch latest created email, that should be the email send to partners
        mail_ids = self.mail_mail.search(cr, uid, [], limit=1)
        mail = self.mail_mail.browse(cr, uid, mail_ids[0])
        mail_emails = tools.email_split(mail.email_to)

        # Check email subject, body, and email_to
        expected_emails = ['a@a', 'b@b']
        self.assertTrue(mail.subject == _mail_subject and _body_text in mail.body,
            'Send email subject is \'%s\' and should be %s; body is %s and should contain %s' % (mail.subject, _mail_subject, mail.body, _body_text))
        self.assertTrue(all(email in mail_emails for email in expected_emails) and len(mail_emails) == 2,
            'Send email emails are %s; should be %s' % (mail_emails, expected_emails))

        # Create a reply to the last comment
        compose_id = mail_compose.create(cr, uid,
            {}, {'mail.compose.message.mode': 'reply', 'default_model': 'mail.thread', 'default_res_id': self.group_pigs_id,
                'active_id': first_com.id})
        compose = mail_compose.browse(cr, uid, compose_id)
        self.assertTrue(compose.model == 'mail.group' and compose.res_id == self.group_pigs_id,
            'Wizard message has model: %s and res_id:%s; should be mail.group and %s' % (compose.model, compose.res_id, self.group_pigs_id))
        self.assertTrue(compose.parent_id.id == first_com.id,
            'Wizard parent_id is %d; should be %d' % (compose.parent_id.id, first_com.id))

    def test_30_message_read(self):
        """ Tests designed for message_read. """
        def _simplify_struct(read_dict):
            res = []
            for val in read_dict:
                current = {'_id': val['id']}
                if val.get('child_ids'):
                    current['child_ids'] = _flatten(val.get('child_ids'))
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
        self.assertTrue(len(notif_ids) == na_count,
            'Number of unread notifications (%s) does not match the needaction count (%s)' % (len(notif_ids), na_count))

        # Post 4 message on group_pigs
        msgid1 = group_pigs.message_post(body='My Body')
        msgid2 = group_pigs.message_post(body='My Body')
        msgid3 = group_pigs.message_post(body='My Body')
        msgid4 = group_pigs.message_post(body='My Body')

        # Check there are 4 new needaction on mail.message
        notif_ids = self.mail_notification.search(cr, uid, [
            ('partner_id', '=', user_admin.partner_id.id),
            ('read', '=', False)
            ])
        na_count = self.mail_message._needaction_count(cr, uid, domain = [])
        self.assertTrue(len(notif_ids) == na_count,
            'Number of unread notifications after posting messages (%s) does not match the needaction count (%s)' % (len(notif_ids), na_count))

        # Check there are 4 needaction on mail.message with particular domain
        na_count = self.mail_message._needaction_count(cr, uid, domain = [('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)])
        self.assertTrue(na_count == 4,
            'Number of posted message (4) does not match the needaction count with domain mail.group - group pigs (%s)' % (na_count))
