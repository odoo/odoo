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
        self.mail_group = self.registry('mail.group')
        self.mail_message = self.registry('mail.message')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

    def test_00_access_rights(self):
        cr, uid = self.cr, self.uid
        self.res_groups = self.registry('res.groups')
        # Prepare groups: Pigs (employee), Jobs (public)
        self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
        self.group_jobs_id = self.mail_group.create(cr, uid, {'name': 'Jobs', 'public': 'public'})

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        group_employee_id = group_employee_ref and group_employee_ref[1] or False
        group_employee = self.res_groups.browse(cr, uid, group_employee_id)

        # Create Bert (without groups) and Raoul( employee)
        user_bert_id = self.res_users.create(cr, uid, {'name': 'Bert Tartopoils', 'login': 'bert', 'groups_id': [(6, 0, [])]})
        user_raoul_id = self.res_users.create(cr, uid, {'name': 'Raoul Grosbedon', 'login': 'raoul', 'groups_id': [(6, 0, [group_employee_id])]})
        user_bert = self.res_users.browse(cr, uid, user_bert_id)
        user_raoul = self.res_users.browse(cr, uid, user_raoul_id)

        # ----------------------------------------
        # CASE1: Bert, without groups
        # ----------------------------------------
        print 'Bert CASE1'
        # Do: Bert creates a group, should crash because perm_create only for employees
        self.assertRaises(except_orm,
                          self.mail_group.create,
                          cr, user_bert_id, {'name': 'Bert\'s Group'})
        # Do: Bert reads Jobs basic fields, ok because public = read access on the group
        self.mail_group.read(cr, user_bert_id, self.group_jobs_id, ['name', 'description'])
        # Do: Bert reads Jobs messages, ok because read access on the group = read access on its messages
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
        self.mail_group.message_subscribe(cr, uid, [self.group_jobs_id], [user_bert.partner_id.id])
        # Do: Bert comments Jobs, ok because he is now in the followers
        self.mail_group.message_post(cr, user_bert_id, self.group_jobs_id, body='I love Pigs')
        # Do: Bert browse Pigs, ok (no direct browse of partners)
        self.mail_group.browse(cr, user_bert_id, self.group_jobs_id)

        # Do: Bert reads Pigs, should crash because mail.group security=groups only for employee group
        self.assertRaises(except_orm,
                          self.mail_group.read,
                          cr, user_bert_id, self.group_pigs_id)

        # ----------------------------------------
        # CASE1: Raoul, employee
        # ----------------------------------------
        print 'Raoul CASE1'
        # Do: Bert read Jobs, ok because public
        self.mail_group.read(cr, user_raoul_id, self.group_pigs_id)
        # Do: Bert read Jobs, ok because public
        self.mail_group.read(cr, user_raoul_id, self.group_jobs_id)
