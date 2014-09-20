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

from openerp.addons.mail.tests.common import TestMail
from openerp.exceptions import AccessError
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger


class TestMailMail(TestMail):

    def test_00_partner_find_from_email(self):
        """ Tests designed for partner fetch based on emails. """
        cr, uid, user_raoul, group_pigs = self.cr, self.uid, self.user_raoul, self.group_pigs

        # --------------------------------------------------
        # Data creation
        # --------------------------------------------------
        # 1 - Partner ARaoul
        p_a_id = self.res_partner.create(cr, uid, {'name': 'ARaoul', 'email': 'test@test.fr'})

        # --------------------------------------------------
        # CASE1: without object
        # --------------------------------------------------

        # Do: find partner with email -> first partner should be found
        partner_info = self.mail_thread.message_partner_info_from_emails(cr, uid, None, ['Maybe Raoul <test@test.fr>'], link_mail=False)[0]
        self.assertEqual(partner_info['full_name'], 'Maybe Raoul <test@test.fr>',
                         'mail_thread: message_partner_info_from_emails did not handle email')
        self.assertEqual(partner_info['partner_id'], p_a_id,
                         'mail_thread: message_partner_info_from_emails wrong partner found')

        # Data: add some data about partners
        # 2 - User BRaoul
        p_b_id = self.res_partner.create(cr, uid, {'name': 'BRaoul', 'email': 'test@test.fr', 'user_ids': [(4, user_raoul.id)]})

        # Do: find partner with email -> first user should be found
        partner_info = self.mail_thread.message_partner_info_from_emails(cr, uid, None, ['Maybe Raoul <test@test.fr>'], link_mail=False)[0]
        self.assertEqual(partner_info['partner_id'], p_b_id,
                         'mail_thread: message_partner_info_from_emails wrong partner found')

        # --------------------------------------------------
        # CASE1: with object
        # --------------------------------------------------

        # Do: find partner in group where there is a follower with the email -> should be taken
        self.mail_group.message_subscribe(cr, uid, [group_pigs.id], [p_b_id])
        partner_info = self.mail_group.message_partner_info_from_emails(cr, uid, group_pigs.id, ['Maybe Raoul <test@test.fr>'], link_mail=False)[0]
        self.assertEqual(partner_info['partner_id'], p_b_id,
                         'mail_thread: message_partner_info_from_emails wrong partner found')


class TestMailMessage(TestMail):

    def test_00_mail_message_values(self):
        """ Tests designed for testing email values based on mail.message, aliases, ... """
        cr, uid, user_raoul_id = self.cr, self.uid, self.user_raoul_id

        # Data: update + generic variables
        reply_to1 = '_reply_to1@example.com'
        reply_to2 = '_reply_to2@example.com'
        email_from1 = 'from@example.com'
        alias_domain = 'schlouby.fr'
        raoul_from = 'Raoul Grosbedon <raoul@raoul.fr>'
        raoul_from_alias = 'Raoul Grosbedon <raoul@schlouby.fr>'
        raoul_reply_alias = 'YourCompany Pigs <group+pigs@schlouby.fr>'

        # --------------------------------------------------
        # Case1: without alias_domain
        # --------------------------------------------------
        param_ids = self.registry('ir.config_parameter').search(cr, uid, [('key', '=', 'mail.catchall.domain')])
        self.registry('ir.config_parameter').unlink(cr, uid, param_ids)

        # Do: free message; specified values > default values
        msg_id = self.mail_message.create(cr, user_raoul_id, {'no_auto_thread': True, 'reply_to': reply_to1, 'email_from': email_from1})
        msg = self.mail_message.browse(cr, user_raoul_id, msg_id)
        # Test: message content
        self.assertIn('reply_to', msg.message_id,
                      'mail_message: message_id should be specific to a mail_message with a given reply_to')
        self.assertEqual(msg.reply_to, reply_to1,
                         'mail_message: incorrect reply_to: should come from values')
        self.assertEqual(msg.email_from, email_from1,
                         'mail_message: incorrect email_from: should come from values')

        # Do: create a mail_mail with the previous mail_message + specified reply_to
        mail_id = self.mail_mail.create(cr, user_raoul_id, {'mail_message_id': msg_id, 'state': 'cancel', 'reply_to': reply_to2})
        mail = self.mail_mail.browse(cr, user_raoul_id, mail_id)
        # Test: mail_mail content
        self.assertEqual(mail.reply_to, reply_to2,
                         'mail_mail: incorrect reply_to: should come from values')
        self.assertEqual(mail.email_from, email_from1,
                         'mail_mail: incorrect email_from: should come from mail.message')

        # Do: mail_message attached to a document
        msg_id = self.mail_message.create(cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_pigs_id})
        msg = self.mail_message.browse(cr, user_raoul_id, msg_id)
        # Test: message content
        self.assertIn('mail.group', msg.message_id,
                      'mail_message: message_id should contain model')
        self.assertIn('%s' % self.group_pigs_id, msg.message_id,
                      'mail_message: message_id should contain res_id')
        self.assertEqual(msg.reply_to, raoul_from,
                         'mail_message: incorrect reply_to: should be Raoul')
        self.assertEqual(msg.email_from, raoul_from,
                         'mail_message: incorrect email_from: should be Raoul')

        # --------------------------------------------------
        # Case2: with alias_domain, without catchall alias
        # --------------------------------------------------
        self.registry('ir.config_parameter').set_param(cr, uid, 'mail.catchall.domain', alias_domain)
        self.registry('ir.config_parameter').unlink(cr, uid, self.registry('ir.config_parameter').search(cr, uid, [('key', '=', 'mail.catchall.alias')]))

        # Update message
        msg_id = self.mail_message.create(cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_pigs_id})
        msg = self.mail_message.browse(cr, user_raoul_id, msg_id)
        # Test: generated reply_to
        self.assertEqual(msg.reply_to, raoul_reply_alias,
                         'mail_mail: incorrect reply_to: should be Pigs alias')

        # Update message: test alias on email_from
        msg_id = self.mail_message.create(cr, user_raoul_id, {})
        msg = self.mail_message.browse(cr, user_raoul_id, msg_id)
        # Test: generated reply_to
        self.assertEqual(msg.reply_to, raoul_from_alias,
                         'mail_mail: incorrect reply_to: should be message email_from using Raoul alias')

        # --------------------------------------------------
        # Case2: with alias_domain and  catchall alias
        # --------------------------------------------------
        self.registry('ir.config_parameter').set_param(self.cr, self.uid, 'mail.catchall.alias', 'gateway')

        # Update message
        msg_id = self.mail_message.create(cr, user_raoul_id, {})
        msg = self.mail_message.browse(cr, user_raoul_id, msg_id)
        # Test: generated reply_to
        self.assertEqual(msg.reply_to, 'YourCompany <gateway@schlouby.fr>',
                         'mail_mail: reply_to should equal the catchall email alias')

        # Do: create a mail_mail
        mail_id = self.mail_mail.create(cr, uid, {'state': 'cancel', 'reply_to': 'someone@example.com'})
        mail = self.mail_mail.browse(cr, uid, mail_id)
        # Test: mail_mail content
        self.assertEqual(mail.reply_to, 'someone@example.com',
                         'mail_mail: reply_to should equal the rpely_to given to create')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_10_mail_message_search_access_rights(self):
        """ Testing mail_message.search() using specific _search implementation """
        cr, uid, group_pigs_id = self.cr, self.uid, self.group_pigs_id
        # Data: comment subtype for mail.message creation
        ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'mail', 'mt_comment')
        subtype_id = ref and ref[1] or False

        # Data: Birds group, private
        group_birds_id = self.mail_group.create(self.cr, self.uid, {'name': 'Birds', 'public': 'private'})
        # Data: Raoul is member of Pigs
        self.mail_group.message_subscribe(cr, uid, [group_pigs_id], [self.partner_raoul_id])
        # Data: various author_ids, partner_ids, documents
        msg_id1 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A', 'subtype_id': subtype_id})
        msg_id2 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A+B', 'partner_ids': [(6, 0, [self.partner_bert_id])], 'subtype_id': subtype_id})
        msg_id3 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A Pigs', 'model': 'mail.group', 'res_id': group_pigs_id, 'subtype_id': subtype_id})
        msg_id4 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A+B Pigs', 'model': 'mail.group', 'res_id': group_pigs_id, 'partner_ids': [(6, 0, [self.partner_bert_id])], 'subtype_id': subtype_id})
        msg_id5 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A+R Pigs', 'model': 'mail.group', 'res_id': group_pigs_id, 'partner_ids': [(6, 0, [self.partner_raoul_id])], 'subtype_id': subtype_id})
        msg_id6 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A Birds', 'model': 'mail.group', 'res_id': group_birds_id, 'subtype_id': subtype_id})
        msg_id7 = self.mail_message.create(cr, self.user_raoul_id, {'subject': '_Test', 'body': 'B', 'subtype_id': subtype_id})
        msg_id8 = self.mail_message.create(cr, self.user_raoul_id, {'subject': '_Test', 'body': 'B+R', 'partner_ids': [(6, 0, [self.partner_raoul_id])], 'subtype_id': subtype_id})

        # Test: Bert: 2 messages that have Bert in partner_ids
        msg_ids = self.mail_message.search(cr, self.user_bert_id, [('subject', 'like', '_Test')])
        self.assertEqual(set([msg_id2, msg_id4]), set(msg_ids), 'mail_message search failed')
        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group)
        msg_ids = self.mail_message.search(cr, self.user_raoul_id, [('subject', 'like', '_Test'), ('body', 'like', 'A')])
        self.assertEqual(set([msg_id3, msg_id4, msg_id5]), set(msg_ids), 'mail_message search failed')
        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group) + 2 messages as author
        msg_ids = self.mail_message.search(cr, self.user_raoul_id, [('subject', 'like', '_Test')])
        self.assertEqual(set([msg_id3, msg_id4, msg_id5, msg_id7, msg_id8]), set(msg_ids), 'mail_message search failed')
        # Test: Admin: all messages
        msg_ids = self.mail_message.search(cr, uid, [('subject', 'like', '_Test')])
        self.assertEqual(set([msg_id1, msg_id2, msg_id3, msg_id4, msg_id5, msg_id6, msg_id7, msg_id8]), set(msg_ids), 'mail_message search failed')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_15_mail_message_check_access_rule(self):
        """ Testing mail_message.check_access_rule() """
        cr, uid = self.cr, self.uid
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert_id, user_raoul_id = self.user_bert_id, self.user_raoul_id

        # Prepare groups: Pigs (employee), Jobs (public)
        pigs_msg_id = self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
        priv_msg_id = self.mail_group.message_post(cr, uid, self.group_priv_id, body='Message')

        # prepare an attachment
        attachment_id = self.ir_attachment.create(cr, uid, {'datas': 'My attachment'.encode('base64'), 'name': 'doc.txt', 'datas_fname': 'doc.txt'})

        # ----------------------------------------
        # CASE1: read
        # ----------------------------------------

        # Do: create a new mail.message
        message_id = self.mail_message.create(cr, uid, {'body': 'My Body', 'attachment_ids': [(4, attachment_id)]})

        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        with self.assertRaises(except_orm):
            self.mail_message.read(cr, user_bert_id, message_id)
        # Do: message is pushed to Bert
        notif_id = self.mail_notification.create(cr, uid, {'message_id': message_id, 'partner_id': partner_bert_id})
        # Test: Bert reads the message, ok because notification pushed
        self.mail_message.read(cr, user_bert_id, message_id)
        # Test: Bert downloads attachment, ok because he can read message
        self.mail_message.download_attachment(cr, user_bert_id, message_id, attachment_id)
        # Do: remove notification
        self.mail_notification.unlink(cr, uid, notif_id)
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        with self.assertRaises(except_orm):
            self.mail_message.read(cr, self.user_bert_id, message_id)
        # Test: Bert downloads attachment, crash because he can't read message
        with self.assertRaises(except_orm):
            self.mail_message.download_attachment(cr, user_bert_id, message_id, attachment_id)
        # Do: Bert is now the author
        self.mail_message.write(cr, uid, [message_id], {'author_id': partner_bert_id})
        # Test: Bert reads the message, ok because Bert is the author
        self.mail_message.read(cr, user_bert_id, message_id)
        # Do: Bert is not the author anymore
        self.mail_message.write(cr, uid, [message_id], {'author_id': partner_raoul_id})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        with self.assertRaises(except_orm):
            self.mail_message.read(cr, user_bert_id, message_id)
        # Do: message is attached to a document Bert can read, Jobs
        self.mail_message.write(cr, uid, [message_id], {'model': 'mail.group', 'res_id': self.group_jobs_id})
        # Test: Bert reads the message, ok because linked to a doc he is allowed to read
        self.mail_message.read(cr, user_bert_id, message_id)
        # Do: message is attached to a document Bert cannot read, Pigs
        self.mail_message.write(cr, uid, [message_id], {'model': 'mail.group', 'res_id': self.group_pigs_id})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        with self.assertRaises(except_orm):
            self.mail_message.read(cr, user_bert_id, message_id)

        # ----------------------------------------
        # CASE2: create
        # ----------------------------------------

        # Do: Bert creates a message on Pigs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.mail_message.create(cr, user_bert_id, {'model': 'mail.group', 'res_id': self.group_pigs_id, 'body': 'Test'})
        # Do: Bert create a message on Jobs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.mail_message.create(cr, user_bert_id, {'model': 'mail.group', 'res_id': self.group_jobs_id, 'body': 'Test'})
        # Do: Bert create a private message -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.mail_message.create(cr, user_bert_id, {'body': 'Test'})

        # Do: Raoul creates a message on Jobs -> ok, write access to the related document
        self.mail_message.create(cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_jobs_id, 'body': 'Test'})
        # Do: Raoul creates a message on Priv -> ko, no write access to the related document
        with self.assertRaises(except_orm):
            self.mail_message.create(cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_priv_id, 'body': 'Test'})
        # Do: Raoul creates a private message -> ok
        self.mail_message.create(cr, user_raoul_id, {'body': 'Test'})
        # Do: Raoul creates a reply to a message on Priv -> ko
        with self.assertRaises(except_orm):
            self.mail_message.create(cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_priv_id, 'body': 'Test', 'parent_id': priv_msg_id})
        # Do: Raoul creates a reply to a message on Priv-> ok if has received parent
        self.mail_notification.create(cr, uid, {'message_id': priv_msg_id, 'partner_id': self.partner_raoul_id})
        self.mail_message.create(cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_priv_id, 'body': 'Test', 'parent_id': priv_msg_id})

    def test_20_message_set_star(self):
        """ Tests for starring messages and its related access rights """
        cr, uid = self.cr, self.uid
        # Data: post a message on Pigs
        msg_id = self.group_pigs.message_post(body='My Body', subject='1')
        msg = self.mail_message.browse(cr, uid, msg_id)
        msg_raoul = self.mail_message.browse(cr, self.user_raoul_id, msg_id)

        # Do: Admin stars msg
        self.mail_message.set_message_starred(cr, uid, [msg.id], True)
        msg.refresh()
        # Test: notification exists
        notif_ids = self.mail_notification.search(cr, uid, [('partner_id', '=', self.partner_admin_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notif_ids), 1, 'mail_message set_message_starred: more than one notification created')
        # Test: notification starred
        notif = self.mail_notification.browse(cr, uid, notif_ids[0])
        self.assertTrue(notif.starred, 'mail_notification starred failed')
        self.assertTrue(msg.starred, 'mail_message starred failed')

        # Do: Raoul stars msg
        self.mail_message.set_message_starred(cr, self.user_raoul_id, [msg.id], True)
        msg_raoul.refresh()
        # Test: notification exists
        notif_ids = self.mail_notification.search(cr, uid, [('partner_id', '=', self.partner_raoul_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notif_ids), 1, 'mail_message set_message_starred: more than one notification created')
        # Test: notification starred
        notif = self.mail_notification.browse(cr, uid, notif_ids[0])
        self.assertTrue(notif.starred, 'mail_notification starred failed')
        self.assertTrue(msg_raoul.starred, 'mail_message starred failed')

        # Do: Admin unstars msg
        self.mail_message.set_message_starred(cr, uid, [msg.id], False)
        msg.refresh()
        msg_raoul.refresh()
        # Test: msg unstarred for Admin, starred for Raoul
        self.assertFalse(msg.starred, 'mail_message starred failed')
        self.assertTrue(msg_raoul.starred, 'mail_message starred failed')

    def test_30_message_set_read(self):
        """ Tests for reading messages and its related access rights """
        cr, uid = self.cr, self.uid
        # Data: post a message on Pigs
        msg_id = self.group_pigs.message_post(body='My Body', subject='1')
        msg = self.mail_message.browse(cr, uid, msg_id)
        msg_raoul = self.mail_message.browse(cr, self.user_raoul_id, msg_id)

        # Do: Admin reads msg
        self.mail_message.set_message_read(cr, uid, [msg.id], True)
        msg.refresh()
        # Test: notification exists
        notif_ids = self.mail_notification.search(cr, uid, [('partner_id', '=', self.partner_admin_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notif_ids), 1, 'mail_message set_message_read: more than one notification created')
        # Test: notification read
        notif = self.mail_notification.browse(cr, uid, notif_ids[0])
        self.assertTrue(notif['is_read'], 'mail_notification read failed')
        self.assertFalse(msg.to_read, 'mail_message read failed')

        # Do: Raoul reads msg
        self.mail_message.set_message_read(cr, self.user_raoul_id, [msg.id], True)
        msg_raoul.refresh()
        # Test: notification exists
        notif_ids = self.mail_notification.search(cr, uid, [('partner_id', '=', self.partner_raoul_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notif_ids), 1, 'mail_message set_message_read: more than one notification created')
        # Test: notification read
        notif = self.mail_notification.browse(cr, uid, notif_ids[0])
        self.assertTrue(notif['is_read'], 'mail_notification starred failed')
        self.assertFalse(msg_raoul.to_read, 'mail_message starred failed')

        # Do: Admin unreads msg
        self.mail_message.set_message_read(cr, uid, [msg.id], False)
        msg.refresh()
        msg_raoul.refresh()
        # Test: msg unread for Admin, read for Raoul
        self.assertTrue(msg.to_read, 'mail_message read failed')
        self.assertFalse(msg_raoul.to_read, 'mail_message read failed')

    def test_40_message_vote(self):
        """ Test designed for the vote/unvote feature. """
        cr, uid = self.cr, self.uid
        # Data: post a message on Pigs
        msg_id = self.group_pigs.message_post(body='My Body', subject='1')
        msg = self.mail_message.browse(cr, uid, msg_id)
        msg_raoul = self.mail_message.browse(cr, self.user_raoul_id, msg_id)

        # Do: Admin vote for msg
        self.mail_message.vote_toggle(cr, uid, [msg.id])
        msg.refresh()
        # Test: msg has Admin as voter
        self.assertEqual(set(msg.vote_user_ids), set([self.user_admin]), 'mail_message vote: after voting, Admin should be in the voter')
        # Do: Bert vote for msg
        self.mail_message.vote_toggle(cr, self.user_raoul_id, [msg.id])
        msg_raoul.refresh()
        # Test: msg has Admin and Bert as voters
        self.assertEqual(set(msg_raoul.vote_user_ids), set([self.user_admin, self.user_raoul]), 'mail_message vote: after voting, Admin and Bert should be in the voters')
        # Do: Admin unvote for msg
        self.mail_message.vote_toggle(cr, uid, [msg.id])
        msg.refresh()
        msg_raoul.refresh()
        # Test: msg has Bert as voter
        self.assertEqual(set(msg.vote_user_ids), set([self.user_raoul]), 'mail_message vote: after unvoting, Bert should be in the voter')
        self.assertEqual(set(msg_raoul.vote_user_ids), set([self.user_raoul]), 'mail_message vote: after unvoting, Bert should be in the voter')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_50_mail_flow_access_rights(self):
        """ Test a Chatter-looks alike flow to test access rights """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert_id, user_raoul_id = self.user_bert_id, self.user_raoul_id

        # Prepare groups: Pigs (employee), Jobs (public)
        pigs_msg_id = self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message', partner_ids=[self.partner_admin_id])
        jobs_msg_id = self.mail_group.message_post(cr, uid, self.group_jobs_id, body='Message', partner_ids=[self.partner_admin_id])

        # ----------------------------------------
        # CASE1: Bert, without groups
        # ----------------------------------------

        # Do: Bert reads Jobs basic fields, ok because public = read access on the group
        self.mail_group.read(cr, user_bert_id, [self.group_jobs_id], ['name', 'description'])
        # Do: Bert reads Jobs messages, ok because read access on the group => read access on its messages
        jobs_message_ids = self.mail_group.read(cr, user_bert_id, [self.group_jobs_id], ['message_ids'])[0]['message_ids']
        self.mail_message.read(cr, user_bert_id, jobs_message_ids)
        # Do: Bert browses Jobs, ok (no direct browse of partners), ok for messages, ko for followers (accessible to employees or partner manager)
        bert_jobs = self.mail_group.browse(cr, user_bert_id, self.group_jobs_id)
        trigger_read = bert_jobs.name
        for message in bert_jobs.message_ids:
            trigger_read = message.subject
        for partner in bert_jobs.message_follower_ids:
            with self.assertRaises(AccessError):
                trigger_read = partner.name
        # Do: Bert comments Jobs, ko because no creation right
        with self.assertRaises(AccessError):
            self.mail_group.message_post(cr, user_bert_id, self.group_jobs_id, body='I love Pigs')

        # Do: Bert writes on its own profile, ko because no message create access
        with self.assertRaises(AccessError):
            self.res_users.message_post(cr, user_bert_id, user_bert_id, body='I love Bert')
            self.res_partner.message_post(cr, user_bert_id, partner_bert_id, body='I love Bert')

        # ----------------------------------------
        # CASE2: Raoul, employee
        # ----------------------------------------

        # Do: Raoul browses Jobs -> ok, ok for message_ids, of for message_follower_ids
        raoul_jobs = self.mail_group.browse(cr, user_raoul_id, self.group_jobs_id)
        trigger_read = raoul_jobs.name
        for message in raoul_jobs.message_ids:
            trigger_read = message.subject
        for partner in raoul_jobs.message_follower_ids:
            trigger_read = partner.name

        # Do: Raoul comments Jobs, ok
        self.mail_group.message_post(cr, user_raoul_id, self.group_jobs_id, body='I love Pigs')
        # Do: Raoul create a mail.compose.message record on Jobs, because he uses the wizard
        compose_id = mail_compose.create(cr, user_raoul_id,
            {'subject': 'Subject', 'body': 'Body text', 'partner_ids': []},
            {'default_composition_mode': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_jobs_id})
        mail_compose.send_mail(cr, user_raoul_id, [compose_id])
        # Do: Raoul replies to a Jobs message using the composer
        compose_id = mail_compose.create(cr, user_raoul_id,
            {'subject': 'Subject', 'body': 'Body text'},
            {'default_composition_mode': 'comment', 'default_parent_id': pigs_msg_id})
        mail_compose.send_mail(cr, user_raoul_id, [compose_id])
