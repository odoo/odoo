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
from openerp.tools import append_content_to_html
from osv.orm import except_orm


class test_portal(test_mail.TestMailMockups):

    def setUp(self):
        super(test_portal, self).setUp()
        cr, uid = self.cr, self.uid
        self.ir_model = self.registry('ir.model')
        self.mail_group = self.registry('mail.group')
        self.mail_mail = self.registry('mail.mail')
        self.mail_message = self.registry('mail.message')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

        # Find Portal group
        group_portal_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_portal_member')
        self.group_portal_id = group_portal_ref and group_portal_ref[1] or False

        # Create Chell (portal user)
        self.user_chell_id = self.res_users.create(cr, uid, {'name': 'Chell Gladys', 'login': 'chell', 'groups_id': [(6, 0, [self.group_portal_id])]})
        self.user_chell = self.res_users.browse(cr, uid, self.user_chell_id)
        self.partner_chell_id = self.user_chell.partner_id.id

    # def test_00_access_rights(self):
    #     """ Test basic mail_message and mail_group access rights for portal users. """
    #     cr, uid = self.cr, self.uid
    #     partner_chell_id = self.partner_chell_id
    #     user_chell_id = self.user_chell_id

    #     # Prepare group: Pigs (portal)
    #     self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
    #     self.mail_group.write(cr, uid, [self.group_pigs_id], {'name': 'Jobs', 'public': 'groups', 'group_public_id': self.group_portal_id})

    #     # ----------------------------------------
    #     # CASE1: Chell will use the Chatter
    #     # ----------------------------------------

    #     # Do: Chell reads Pigs messages, ok because restricted to portal group
    #     message_ids = self.mail_group.read(cr, user_chell_id, self.group_pigs_id, ['message_ids'])['message_ids']
    #     self.mail_message.read(cr, user_chell_id, message_ids)
    #     # Do: Chell posts a message on Pigs, crash because can not write on group or is not in the followers
    #     self.assertRaises(except_orm,
    #                       self.mail_group.message_post,
    #                       cr, user_chell_id, self.group_pigs_id, body='Message')
    #     # Do: Chell is added to Pigs followers
    #     self.mail_group.message_subscribe(cr, uid, [self.group_pigs_id], [partner_chell_id])
    #     # Test: Chell posts a message on Pigs, ok because in the followers
    #     self.mail_group.message_post(cr, user_chell_id, self.group_pigs_id, body='Message')

    # def test_50_mail_invite(self):
    #     cr, uid = self.cr, self.uid
    #     user_admin = self.res_users.browse(cr, uid, uid)
    #     self.mail_invite = self.registry('mail.wizard.invite')
    #     base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='')
    #     portal_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_portal')
    #     portal_id = portal_ref and portal_ref[1] or False

    #     # 0 - Admin
    #     p_a_id = user_admin.partner_id.id
    #     # 1 - Bert Tartopoils, with email, should receive emails for comments and emails
    #     p_b_id = self.res_partner.create(cr, uid, {'name': 'Bert Tartopoils', 'email': 'b@b'})

    #     # ----------------------------------------
    #     # CASE1: generated URL
    #     # ----------------------------------------

    #     url = self.mail_mail._generate_signin_url(cr, uid, p_b_id, portal_id, 1234)
    #     self.assertEqual(url,  base_url + '/login?action=signin&partner_id=%s&group=%s&key=%s' % (p_b_id, portal_id, 1234),
    #         'generated signin URL incorrect')

    #     # ----------------------------------------
    #     # CASE2: invite Bert
    #     # ----------------------------------------

    #     _sent_email_subject = 'Invitation to follow Pigs'
    #     _sent_email_body = append_content_to_html('<div>You have been invited to follow Pigs.</div>', url)

    #     # Do: create a mail_wizard_invite, validate it
    #     self._init_mock_build_email()
    #     mail_invite_id = self.mail_invite.create(cr, uid, {'partner_ids': [(4, p_b_id)]}, {'default_res_model': 'mail.group', 'default_res_id': self.group_pigs_id})
    #     self.mail_invite.add_followers(cr, uid, [mail_invite_id])
    #     group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

    #     # Test: Pigs followers should contain Admin and Bert
    #     follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
    #     self.assertEqual(set(follower_ids), set([p_a_id, p_b_id]), 'Pigs followers after invite is incorrect')
    #     # Test: sent email subject, body
    #     self.assertEqual(len(self._build_email_kwargs_list), 1, 'sent email number incorrect, should be only for Bert')
    #     for sent_email in self._build_email_kwargs_list:
    #         self.assertEqual(sent_email.get('subject'), _sent_email_subject, 'sent email subject incorrect')
    #         self.assertEqual(sent_email.get('body'), _sent_email_body, 'sent email body incorrect')
