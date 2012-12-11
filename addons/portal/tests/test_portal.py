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
from openerp.tools.misc import mute_logger


class test_portal(TestMailBase):

    def setUp(self):
        super(test_portal, self).setUp()
        cr, uid = self.cr, self.uid

        # Find Portal group
        group_portal = self.registry('ir.model.data').get_object(cr, uid, 'portal', 'group_portal')
        self.group_portal_id = group_portal.id

        # Create Chell (portal user)
        self.user_chell_id = self.res_users.create(cr, uid, {'name': 'Chell Gladys', 'login': 'chell', 'groups_id': [(6, 0, [self.group_portal_id])]})
        user_chell = self.res_users.browse(cr, uid, self.user_chell_id)
        self.partner_chell_id = user_chell.partner_id.id

        # Set an email address for the user running the tests, used as Sender for outgoing mails
        self.res_users.write(cr, uid, uid, {'email': 'test@localhost'})

    @mute_logger('openerp.addons.base.ir.ir_model')
    def test_00_access_rights(self):
        """ Test basic mail_message and mail_group access rights for portal users. """
        cr, uid = self.cr, self.uid

        # Prepare group: Pigs (portal)
        self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
        self.mail_group.write(cr, uid, [self.group_pigs_id], {'name': 'Jobs', 'public': 'groups', 'group_public_id': self.group_portal_id})

        # ----------------------------------------
        # CASE1: Chell will use the Chatter
        # ----------------------------------------

        # Do: Chell reads Pigs messages, ok because restricted to portal group
        message_ids = self.mail_group.read(cr, self.user_chell_id, self.group_pigs_id, ['message_ids'])['message_ids']
        self.mail_message.read(cr, self.user_chell_id, message_ids)

        # Do: Chell posts a message on Pigs, crash because can not write on group or is not in the followers
        with self.assertRaises(except_orm):
            self.mail_group.message_post(cr, self.user_chell_id, self.group_pigs_id, body='Message')

        # Do: Chell is added to Pigs followers
        self.mail_group.message_subscribe(cr, uid, [self.group_pigs_id], [self.partner_chell_id])

        # Test: Chell posts a message on Pigs, ok because in the followers
        self.mail_group.message_post(cr, self.user_chell_id, self.group_pigs_id, body='Message')

    def test_50_mail_invite(self):
        cr, uid = self.cr, self.uid
        mail_invite = self.registry('mail.wizard.invite')
        base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='')
        # Carine Poilvache, with email, should receive emails for comments and emails
        partner_carine_id = self.res_partner.create(cr, uid, {'name': 'Carine Poilvache', 'email': 'c@c'})

        # Do: create a mail_wizard_invite, validate it
        self._init_mock_build_email()
        context = {'default_res_model': 'mail.group', 'default_res_id': self.group_pigs_id}
        mail_invite_id = mail_invite.create(cr, uid, {'partner_ids': [(4, partner_carine_id)]}, context)
        mail_invite.add_followers(cr, uid, [mail_invite_id])

        # Test: Pigs followers should contain Admin and Bert
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(set(follower_ids), set([self.partner_admin_id, partner_carine_id]), 'Pigs followers after invite is incorrect')

        # Test: partner must have been prepared for signup
        partner_carine = self.res_partner.browse(cr, uid, partner_carine_id)
        self.assertTrue(partner_carine.signup_valid, 'partner has not been prepared for signup')
        self.assertTrue(base_url in partner_carine.signup_url, 'signup url is incorrect')
        self.assertTrue(cr.dbname in partner_carine.signup_url, 'signup url is incorrect')
        self.assertTrue(partner_carine.signup_token in partner_carine.signup_url, 'signup url is incorrect')

        # Test: (pretend to) send email and check subject, body
        self.assertEqual(len(self._build_email_kwargs_list), 1, 'sent email number incorrect, should be only for Bert')
        for sent_email in self._build_email_kwargs_list:
            self.assertEqual(sent_email.get('subject'), 'Invitation to follow Pigs',
                             'subject of invitation email is incorrect')
            self.assertTrue('You have been invited to follow Pigs' in sent_email.get('body'),
                            'body of invitation email is incorrect')
            self.assertTrue(partner_carine.signup_url in sent_email.get('body'),
                            'body of invitation email does not contain signup url')
