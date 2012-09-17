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

from openerp.addons.mail.tests import test_mail
from osv.orm import except_orm


class test_mail_access_rights(test_mail.TestMailMockups):

    def setUp(self):
        super(test_mail_access_rights, self).setUp()
        cr, uid = self.cr, self.uid
        self.mail_group = self.registry('mail.group')
        self.mail_message = self.registry('mail.message')
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

    def test_00_mail_message_read_access_rights(self):
        """ Test basic mail_message read access rights. """
        cr, uid = self.cr, self.uid
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert_id, user_raoul_id = self.user_bert_id, self.user_raoul_id

        # Prepare groups: Pigs (employee), Jobs (public)
        self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
        self.group_jobs_id = self.mail_group.create(cr, uid, {'name': 'Jobs', 'public': 'public'})

        # ----------------------------------------
        # CASE1: Bert, basic mail.message read access
        # ----------------------------------------

        # Do: create a new mail.message
        message_id = self.mail_message.create(cr, uid, {'body': 'My Body'})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        self.assertRaises(except_orm, self.mail_message.read,
            cr, user_bert_id, message_id)
        # Do: message is pushed to Bert
        notif_id = self.mail_notification.create(cr, uid, {'message_id': message_id, 'partner_id': partner_bert_id})
        # Test: Bert reads the message, ok because notification pushed
        self.mail_message.read(cr, user_bert_id, message_id)
        # Do: remove notification
        self.mail_notification.unlink(cr, uid, notif_id)
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        self.assertRaises(except_orm, self.mail_message.read,
            cr, self.user_bert_id, message_id)
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

    def test_05_mail_message_search_access_rights(self):
        """ Test mail_message search override about access rights. """
        self.assertTrue(1 == 1, 'Test not implemented, do not replace by return True')

    def test_10_mail_flow_access_rights(self):
        """ Test a Chatter-looks alike flow. """
        cr, uid = self.cr, self.uid
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

        # ----------------------------------------
        # CASE1: Raoul, employee
        # ----------------------------------------
        # Do: Bert read Pigs, ok because public
        self.mail_group.read(cr, user_raoul_id, self.group_pigs_id)
        # Do: Bert read Jobs, ok because group_public_id = employee
        self.mail_group.read(cr, user_raoul_id, self.group_jobs_id)
