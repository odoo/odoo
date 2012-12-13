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

from openerp.addons.mail.tests import test_mail_mockup
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger


class test_mail_access_rights(test_mail_mockup.TestMailMockups):

    def setUp(self):
        super(test_mail_access_rights, self).setUp()
        cr, uid = self.cr, self.uid
        self.mail_group = self.registry('mail.group')
        self.mail_message = self.registry('mail.message')
        self.attachment = self.registry('ir.attachment')
        self.mail_notification = self.registry('mail.notification')
        self.res_users = self.registry('res.users')
        self.res_groups = self.registry('res.groups')
        self.res_partner = self.registry('res.partner')

        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        self.group_employee_id = group_employee_ref and group_employee_ref[1] or False

        # Create Bert (without groups) and Raoul( employee)
        self.user_bert_id = self.res_users.create(cr, uid, {'name': 'Bert Tartopoils', 'login': 'bert', 'groups_id': [(6, 0, [])]})
        self.user_raoul_id = self.res_users.create(cr, uid, {'name': 'Raoul Grosbedon', 'login': 'raoul', 'groups_id': [(6, 0, [self.group_employee_id])]})
        self.user_bert = self.res_users.browse(cr, uid, self.user_bert_id)
        self.partner_bert_id = self.user_bert.partner_id.id
        self.user_raoul = self.res_users.browse(cr, uid, self.user_raoul_id)
        self.partner_raoul_id = self.user_raoul.partner_id.id

    @mute_logger('openerp.addons.base.ir.ir_model','openerp.osv.orm')
    def test_00_mail_message_search_access_rights(self):
        """ Test mail_message search override about access rights. """
        cr, uid, group_pigs_id = self.cr, self.uid, self.group_pigs_id
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert_id, user_raoul_id = self.user_bert_id, self.user_raoul_id
        # Data: comment subtype for mail.message creation
        ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'mail', 'mt_comment')
        subtype_id = ref and ref[1] or False

        # Data: Birds group, private
        group_birds_id = self.mail_group.create(self.cr, self.uid, {'name': 'Birds', 'public': 'private'})
        # Data: raoul is member of Pigs
        self.mail_group.message_subscribe(cr, uid, [group_pigs_id], [partner_raoul_id])
        # Data: various author_ids, partner_ids, documents
        msg_id1 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A', 'subtype_id': subtype_id})
        msg_id2 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A+B', 'partner_ids': [(6, 0, [partner_bert_id])], 'subtype_id': subtype_id})
        msg_id3 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A Pigs', 'model': 'mail.group', 'res_id': group_pigs_id, 'subtype_id': subtype_id})
        msg_id4 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A+B Pigs', 'model': 'mail.group', 'res_id': group_pigs_id, 'partner_ids': [(6, 0, [partner_bert_id])], 'subtype_id': subtype_id})
        msg_id5 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A+R Pigs', 'model': 'mail.group', 'res_id': group_pigs_id, 'partner_ids': [(6, 0, [partner_raoul_id])], 'subtype_id': subtype_id})
        msg_id6 = self.mail_message.create(cr, uid, {'subject': '_Test', 'body': 'A Birds', 'model': 'mail.group', 'res_id': group_birds_id, 'subtype_id': subtype_id})
        msg_id7 = self.mail_message.create(cr, user_bert_id, {'subject': '_Test', 'body': 'B', 'subtype_id': subtype_id})
        msg_id8 = self.mail_message.create(cr, user_bert_id, {'subject': '_Test', 'body': 'B+R', 'partner_ids': [(6, 0, [partner_raoul_id])], 'subtype_id': subtype_id})

        # Test: Bert: 2 messages that have Bert in partner_ids + 2 messages as author
        msg_ids = self.mail_message.search(cr, user_bert_id, [('subject', 'like', '_Test')])
        self.assertEqual(set([msg_id2, msg_id4, msg_id7, msg_id8]), set(msg_ids), 'mail_message search failed')
        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group)
        msg_ids = self.mail_message.search(cr, user_raoul_id, [('subject', 'like', '_Test'), ('body', 'like', 'A')])
        self.assertEqual(set([msg_id3, msg_id4, msg_id5]), set(msg_ids), 'mail_message search failed')
        # Test: Admin: all messages
        msg_ids = self.mail_message.search(cr, uid, [('subject', 'like', '_Test')])
        self.assertEqual(set([msg_id1, msg_id2, msg_id3, msg_id4, msg_id5, msg_id6, msg_id7, msg_id8]), set(msg_ids), 'mail_message search failed')

    @mute_logger('openerp.addons.base.ir.ir_model','openerp.osv.orm')
    def test_05_mail_message_read_access_rights(self):
        """ Test basic mail_message read access rights. """
        cr, uid = self.cr, self.uid
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert_id, user_raoul_id = self.user_bert_id, self.user_raoul_id

        # Prepare groups: Pigs (employee), Jobs (public)
        self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
        self.group_jobs_id = self.mail_group.create(cr, uid, {'name': 'Jobs', 'public': 'public'})

        # prepare an attachment
        attachment_id = self.attachment.create(cr, uid, {'datas': 'My attachment'.encode('base64'), 'name': 'doc.txt', 'datas_fname': 'doc.txt' })

        # ----------------------------------------
        # CASE1: Bert, basic mail.message read access
        # ----------------------------------------

        # Do: create a new mail.message
        message_id = self.mail_message.create(cr, uid, {'body': 'My Body', 'attachment_ids': [4, attachment_id] })

        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        self.assertRaises(except_orm, self.mail_message.read,
            cr, user_bert_id, message_id)
        # Do: message is pushed to Bert
        notif_id = self.mail_notification.create(cr, uid, {'message_id': message_id, 'partner_id': partner_bert_id})
        # Test: Bert reads the message, ok because notification pushed
        self.mail_message.read(cr, user_bert_id, message_id)
        # Test: Bert download attachment, ok because he can read message
        self.mail_message.download_attachment(cr, user_bert_id, message_id, attachment_id)
        # Do: remove notification
        self.mail_notification.unlink(cr, uid, notif_id)
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        self.assertRaises(except_orm, self.mail_message.read,
            cr, self.user_bert_id, message_id)
        # Test: Bert download attachment, crash because he can't read message
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

    @mute_logger('openerp.addons.base.ir.ir_model','openerp.osv.orm')
    def test_10_mail_flow_access_rights(self):
        """ Test a Chatter-looks alike flow. """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert_id, user_raoul_id = self.user_bert_id, self.user_raoul_id

        # Prepare groups: Pigs (employee), Jobs (public)
        self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
        self.group_jobs_id = self.mail_group.create(cr, uid, {'name': 'Jobs', 'public': 'public'})

        # ----------------------------------------
        # CASE1: Bert, without groups
        # ----------------------------------------
        # Do: Bert creates a group, should crash because perm_create only for employees
        self.assertRaises(except_orm,
                          self.mail_group.create,
                          cr, user_bert_id, {'name': 'Bert\'s Group'})

        # Do: Bert reads Jobs basic fields, ok because public = read access on the group
        self.mail_group.read(cr, user_bert_id, self.group_jobs_id, ['name', 'description'])
        # Do: Bert browse Pigs, ok (no direct browse of partners)
        self.mail_group.browse(cr, user_bert_id, self.group_jobs_id)
        # Do: Bert reads Jobs messages, ok because read access on the group => read access on its messages
        jobs_message_ids = self.mail_group.read(cr, user_bert_id, self.group_jobs_id, ['message_ids'])['message_ids']
        self.mail_message.read(cr, user_bert_id, jobs_message_ids)
        # Do: Bert reads Jobs followers, ko because partner are accessible to employees or partner manager
        jobs_followers_ids = self.mail_group.read(cr, user_bert_id, self.group_jobs_id, ['message_follower_ids'])['message_follower_ids']
        self.assertRaises(except_orm,
                          self.res_partner.read,
                          cr, user_bert_id, jobs_followers_ids)
        # Do: Bert comments Jobs, ko because no write access on the group and not in the followers
        self.assertRaises(except_orm,
                          self.mail_group.message_post,
                          cr, user_bert_id, self.group_jobs_id, body='I love Pigs')
        # Do: add Bert to jobs followers
        self.mail_group.message_subscribe(cr, uid, [self.group_jobs_id], [partner_bert_id])
        # Do: Bert comments Jobs, ok because he is now in the followers
        self.mail_group.message_post(cr, user_bert_id, self.group_jobs_id, body='I love Pigs')

        # Do: Bert reads Pigs, should crash because mail.group security=groups only for employee group
        self.assertRaises(except_orm,
                          self.mail_group.read,
                          cr, user_bert_id, self.group_pigs_id)

        # Do: Bert create a mail.compose.message record, because he uses the wizard
        compose_id = mail_compose.create(cr, user_bert_id,
            {'subject': 'Subject', 'body': 'Body text', 'partner_ids': []},
            # {'subject': 'Subject', 'body_text': 'Body text', 'partner_ids': [(4, p_c_id), (4, p_d_id)]},
            {'default_composition_mode': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_jobs_id})
        mail_compose.send_mail(cr, user_bert_id, [compose_id])

        self.user_demo_id = self.registry('ir.model.data').get_object_reference(self.cr, self.uid, 'base', 'user_demo')[1]
        compose_id = mail_compose.create(cr, self.user_demo_id,
            {'subject': 'Subject', 'body': 'Body text', 'partner_ids': []},
            # {'subject': 'Subject', 'body_text': 'Body text', 'partner_ids': [(4, p_c_id), (4, p_d_id)]},
            {'default_composition_mode': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_jobs_id})
        mail_compose.send_mail(cr, self.user_demo_id, [compose_id])

        # ----------------------------------------
        # CASE2: Raoul, employee
        # ----------------------------------------
        # Do: Bert read Pigs, ok because public
        self.mail_group.read(cr, user_raoul_id, self.group_pigs_id)
        # Do: Bert read Jobs, ok because group_public_id = employee
        self.mail_group.read(cr, user_raoul_id, self.group_jobs_id)
