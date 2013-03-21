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
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger


class test_mail_access_rights(TestMailBase):

    def setUp(self):
        super(test_mail_access_rights, self).setUp()
        cr, uid = self.cr, self.uid

        # Test mail.group: public to provide access to everyone
        self.group_jobs_id = self.mail_group.create(cr, uid, {'name': 'Jobs', 'public': 'public'})
        # Test mail.group: private to restrict access
        self.group_priv_id = self.mail_group.create(cr, uid, {'name': 'Private', 'public': 'private'})

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    def test_00_mail_group_access_rights(self):
        """ Testing mail_group access rights and basic mail_thread features """
        cr, uid, user_bert_id, user_raoul_id = self.cr, self.uid, self.user_bert_id, self.user_raoul_id

        # Do: Bert reads Jobs -> ok, public
        self.mail_group.read(cr, user_bert_id, [self.group_jobs_id])
        # Do: Bert read Pigs -> ko, restricted to employees
        self.assertRaises(except_orm, self.mail_group.read,
            cr, user_bert_id, [self.group_pigs_id])
        # Do: Raoul read Pigs -> ok, belong to employees
        self.mail_group.read(cr, user_raoul_id, [self.group_pigs_id])

        # Do: Bert creates a group -> ko, no access rights
        self.assertRaises(except_orm, self.mail_group.create,
            cr, user_bert_id, {'name': 'Test'})
        # Do: Raoul creates a restricted group -> ok
        new_group_id = self.mail_group.create(cr, user_raoul_id, {'name': 'Test'})
        # Do: Bert added in followers, read -> ok, in followers
        self.mail_group.message_subscribe_users(cr, uid, [new_group_id], [user_bert_id])
        self.mail_group.read(cr, user_bert_id, [new_group_id])

        # Do: Raoul reads Priv -> ko, private
        self.assertRaises(except_orm, self.mail_group.read,
            cr, user_raoul_id, [self.group_priv_id])
        # Do: Raoul added in follower, read -> ok, in followers
        self.mail_group.message_subscribe_users(cr, uid, [self.group_priv_id], [user_raoul_id])
        self.mail_group.read(cr, user_raoul_id, [self.group_priv_id])

        # Do: Raoul write on Jobs -> ok
        self.mail_group.write(cr, user_raoul_id, [self.group_priv_id], {'name': 'modified'})
        # Do: Bert cannot write on Private -> ko (read but no write)
        self.assertRaises(except_orm, self.mail_group.write,
            cr, user_bert_id, [self.group_priv_id], {'name': 're-modified'})
        # Test: Bert cannot unlink the group
        self.assertRaises(except_orm,
            self.mail_group.unlink,
            cr, user_bert_id, [self.group_priv_id])
        # Do: Raoul unlinks the group, there are no followers and messages left
        self.mail_group.unlink(cr, user_raoul_id, [self.group_priv_id])
        fol_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', self.group_priv_id)])
        self.assertFalse(fol_ids, 'unlinked document should not have any followers left')
        msg_ids = self.mail_message.search(cr, uid, [('model', '=', 'mail.group'), ('res_id', '=', self.group_priv_id)])
        self.assertFalse(msg_ids, 'unlinked document should not have any followers left')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
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

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
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
        self.assertRaises(except_orm, self.mail_message.read,
            cr, user_bert_id, message_id)
        # Do: message is pushed to Bert
        notif_id = self.mail_notification.create(cr, uid, {'message_id': message_id, 'partner_id': partner_bert_id})
        # Test: Bert reads the message, ok because notification pushed
        self.mail_message.read(cr, user_bert_id, message_id)
        # Test: Bert downloads attachment, ok because he can read message
        self.mail_message.download_attachment(cr, user_bert_id, message_id, attachment_id)
        # Do: remove notification
        self.mail_notification.unlink(cr, uid, notif_id)
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        self.assertRaises(except_orm, self.mail_message.read,
            cr, self.user_bert_id, message_id)
        # Test: Bert downloads attachment, crash because he can't read message
        self.assertRaises(except_orm, self.mail_message.download_attachment,
            cr, user_bert_id, message_id, attachment_id)
        # Do: Bert is now the author
        self.mail_message.write(cr, uid, [message_id], {'author_id': partner_bert_id})
        # Test: Bert reads the message, ok because Bert is the author
        self.mail_message.read(cr, user_bert_id, message_id)
        # Do: Bert is not the author anymore
        self.mail_message.write(cr, uid, [message_id], {'author_id': partner_raoul_id})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        self.assertRaises(except_orm, self.mail_message.read,
            cr, user_bert_id, message_id)
        # Do: message is attached to a document Bert can read, Jobs
        self.mail_message.write(cr, uid, [message_id], {'model': 'mail.group', 'res_id': self.group_jobs_id})
        # Test: Bert reads the message, ok because linked to a doc he is allowed to read
        self.mail_message.read(cr, user_bert_id, message_id)
        # Do: message is attached to a document Bert cannot read, Pigs
        self.mail_message.write(cr, uid, [message_id], {'model': 'mail.group', 'res_id': self.group_pigs_id})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        self.assertRaises(except_orm, self.mail_message.read,
            cr, user_bert_id, message_id)

        # ----------------------------------------
        # CASE2: create
        # ----------------------------------------

        # Do: Bert creates a message on Pigs -> ko, no creation rights
        self.assertRaises(except_orm, self.mail_message.create,
            cr, user_bert_id, {'model': 'mail.group', 'res_id': self.group_pigs_id, 'body': 'Test'})
        # Do: Bert create a message on Jobs -> ko, no creation rights
        self.assertRaises(except_orm, self.mail_message.create,
            cr, user_bert_id, {'model': 'mail.group', 'res_id': self.group_jobs_id, 'body': 'Test'})
        # Do: Bert create a private message -> ko, no creation rights
        self.assertRaises(except_orm, self.mail_message.create,
            cr, user_bert_id, {'body': 'Test'})

        # Do: Raoul creates a message on Jobs -> ok, write access to the related document
        self.mail_message.create(cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_jobs_id, 'body': 'Test'})
        # Do: Raoul creates a message on Priv -> ko, no write access to the related document
        self.assertRaises(except_orm, self.mail_message.create,
            cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_priv_id, 'body': 'Test'})
        # Do: Raoul creates a private message -> ok
        self.mail_message.create(cr, user_raoul_id, {'body': 'Test'})
        # Do: Raoul creates a reply to a message on Priv -> ko
        self.assertRaises(except_orm, self.mail_message.create,
            cr, user_raoul_id, {'model': 'mail.group', 'res_id': self.group_priv_id, 'body': 'Test', 'parent_id': priv_msg_id})
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
        self.assertTrue(notif.read, 'mail_notification read failed')
        self.assertFalse(msg.to_read, 'mail_message read failed')

        # Do: Raoul reads msg
        self.mail_message.set_message_read(cr, self.user_raoul_id, [msg.id], True)
        msg_raoul.refresh()
        # Test: notification exists
        notif_ids = self.mail_notification.search(cr, uid, [('partner_id', '=', self.partner_raoul_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notif_ids), 1, 'mail_message set_message_read: more than one notification created')
        # Test: notification read
        notif = self.mail_notification.browse(cr, uid, notif_ids[0])
        self.assertTrue(notif.read, 'mail_notification starred failed')
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

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
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
        self.mail_group.read(cr, user_bert_id, self.group_jobs_id, ['name', 'description'])
        # Do: Bert reads Jobs messages, ok because read access on the group => read access on its messages
        jobs_message_ids = self.mail_group.read(cr, user_bert_id, self.group_jobs_id, ['message_ids'])['message_ids']
        self.mail_message.read(cr, user_bert_id, jobs_message_ids)
        # Do: Bert browses Jobs, ok (no direct browse of partners), ok for messages, ko for followers (accessible to employees or partner manager)
        bert_jobs = self.mail_group.browse(cr, user_bert_id, self.group_jobs_id)
        trigger_read = bert_jobs.name
        for message in bert_jobs.message_ids:
            trigger_read = message.subject
        for partner in bert_jobs.message_follower_ids:
            with self.assertRaises(except_orm):
                trigger_read = partner.name
        # Do: Bert comments Jobs, ko because no creation right
        self.assertRaises(except_orm,
                          self.mail_group.message_post,
                          cr, user_bert_id, self.group_jobs_id, body='I love Pigs')

        # Do: Bert writes on its own profile, ko because no message create access
        with self.assertRaises(except_orm):
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
            {'default_composition_mode': 'reply', 'default_parent_id': pigs_msg_id})
        mail_compose.send_mail(cr, user_raoul_id, [compose_id])
