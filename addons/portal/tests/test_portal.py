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
# from openerp.tests import common
from openerp.tools import append_content_to_html


class test_portal(test_mail.TestMailMockups):

    def setUp(self):
        super(test_portal, self).setUp()
        self.ir_model = self.registry('ir.model')
        self.mail_group = self.registry('mail.group')
        self.mail_mail = self.registry('mail.mail')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

    def test_00_mail_invite(self):
        cr, uid = self.cr, self.uid
        user_admin = self.res_users.browse(cr, uid, uid)
        self.mail_invite = self.registry('mail.wizard.invite')
        base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='')
        portal_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'portal', 'portal')
        portal_id = portal_ref and portal_ref[1] or False

        # 0 - Admin
        p_a_id = user_admin.partner_id.id
        # 1 - Bert Tartopoils, with email, should receive emails for comments and emails
        p_b_id = self.res_partner.create(cr, uid, {'name': 'Bert Tartopoils', 'email': 'b@b'})

        # ----------------------------------------
        # CASE1: invite Bert
        # ----------------------------------------

        _sent_email_subject = 'Invitation to follow Pigs'
        _sent_email_body = append_content_to_html('<div>You have been invited to follow Pigs.</div>',
            base_url + '/login?action=signin&partner_id=%s&group=%s&key=%s' % (p_b_id, portal_id, 1234))

        # Do: create a mail_wizard_invite, validate it
        self._init_mock_build_email()
        mail_invite_id = self.mail_invite.create(cr, uid, {'partner_ids': [(4, p_b_id)]}, {'default_res_model': 'mail.group', 'default_res_id': self.group_pigs_id})
        self.mail_invite.add_followers(cr, uid, [mail_invite_id])
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Test: Pigs followers should contain Admin and Bert
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(set(follower_ids), set([p_a_id, p_b_id]), 'Pigs followers after invite is incorrect')
        # Test: sent email subject, body
        self.assertEqual(len(self._build_email_kwargs_list), 1, 'sent email number incorrect, should be only for Bert')
        for sent_email in self._build_email_kwargs_list:
            self.assertEqual(sent_email.get('subject'), _sent_email_subject, 'sent email subject incorrect')
            self.assertEqual(sent_email.get('body'), _sent_email_body, 'sent email body incorrect')
