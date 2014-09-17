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
from openerp.tools.misc import mute_logger


class test_portal(TestMail):

    def setUp(self):
        super(test_portal, self).setUp()
        cr, uid = self.cr, self.uid

        # Find Portal group
        group_portal = self.registry('ir.model.data').get_object(cr, uid, 'base', 'group_portal')
        self.group_portal_id = group_portal.id

        # Create Chell (portal user)
        self.user_chell_id = self.res_users.create(cr, uid, {'name': 'Chell Gladys', 'login': 'chell', 'email': 'chell@gladys.portal', 'groups_id': [(6, 0, [self.group_portal_id])]})
        self.user_chell = self.res_users.browse(cr, uid, self.user_chell_id)
        self.partner_chell_id = self.user_chell.partner_id.id

        # Create a PigsPortal group
        self.group_port_id = self.mail_group.create(cr, uid,
                        {'name': 'PigsPortal', 'public': 'groups', 'group_public_id': self.group_portal_id},
                        {'mail_create_nolog': True})

        # Set an email address for the user running the tests, used as Sender for outgoing mails
        self.res_users.write(cr, uid, uid, {'email': 'test@localhost'})

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_mail_access_rights(self):
        """ Test basic mail_message and mail_group access rights for portal users. """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')

        # Prepare group: Pigs and PigsPortal
        pigs_msg_id = self.mail_group.message_post(cr, uid, self.group_pigs_id, body='Message')
        port_msg_id = self.mail_group.message_post(cr, uid, self.group_port_id, body='Message')

        # Do: Chell browses Pigs -> ko, employee group
        chell_pigs = self.mail_group.browse(cr, self.user_chell_id, self.group_pigs_id)
        with self.assertRaises(except_orm):
            trigger_read = chell_pigs.name

        # Do: Chell posts a message on Pigs, crash because can not write on group or is not in the followers
        with self.assertRaises(AccessError):
            self.mail_group.message_post(cr, self.user_chell_id, self.group_pigs_id, body='Message')

        # Do: Chell is added into Pigs followers and browse it -> ok for messages, ko for partners (no read permission)
        self.mail_group.message_subscribe_users(cr, uid, [self.group_pigs_id], [self.user_chell_id])
        chell_pigs = self.mail_group.browse(cr, self.user_chell_id, self.group_pigs_id)
        trigger_read = chell_pigs.name
        for message in chell_pigs.message_ids:
            trigger_read = message.subject
        for partner in chell_pigs.message_follower_ids:
            if partner.id == self.partner_chell_id:
                # Chell can read her own partner record
                continue
            with self.assertRaises(except_orm):
                trigger_read = partner.name

        # Do: Chell comments Pigs, ok because he is now in the followers
        self.mail_group.message_post(cr, self.user_chell_id, self.group_pigs_id, body='I love Pigs')
        # Do: Chell creates a mail.compose.message record on Pigs, because he uses the wizard
        compose_id = mail_compose.create(cr, self.user_chell_id,
            {'subject': 'Subject', 'body': 'Body text', 'partner_ids': []},
            {'default_composition_mode': 'comment', 'default_model': 'mail.group', 'default_res_id': self.group_pigs_id})
        mail_compose.send_mail(cr, self.user_chell_id, [compose_id])
        # Do: Chell replies to a Pigs message using the composer
        compose_id = mail_compose.create(cr, self.user_chell_id,
            {'subject': 'Subject', 'body': 'Body text'},
            {'default_composition_mode': 'comment', 'default_parent_id': pigs_msg_id})
        mail_compose.send_mail(cr, self.user_chell_id, [compose_id])

        # Do: Chell browses PigsPortal -> ok because groups security, ko for partners (no read permission)
        chell_port = self.mail_group.browse(cr, self.user_chell_id, self.group_port_id)
        trigger_read = chell_port.name
        for message in chell_port.message_ids:
            trigger_read = message.subject
        for partner in chell_port.message_follower_ids:
            with self.assertRaises(except_orm):
                trigger_read = partner.name

    def test_10_mail_invite(self):
        cr, uid = self.cr, self.uid
        mail_invite = self.registry('mail.wizard.invite')
        base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='')
        # Carine Poilvache, with email, should receive emails for comments and emails
        partner_carine_id = self.res_partner.create(cr, uid, {'name': 'Carine Poilvache', 'email': 'c@c'})

        # Do: create a mail_wizard_invite, validate it
        self._init_mock_build_email()
        context = {'default_res_model': 'mail.group', 'default_res_id': self.group_pigs_id}
        mail_invite_id = mail_invite.create(cr, uid, {'partner_ids': [(4, partner_carine_id)], 'send_mail': True}, context)
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
            self.assertEqual(sent_email.get('subject'), 'Invitation to follow Discussion group: Pigs',
                             'invite: subject of invitation email is incorrect')
            self.assertIn('Administrator invited you to follow Discussion group document: Pigs', sent_email.get('body'),
                          'invite: body of invitation email is incorrect')
            self.assertIn(partner_carine.signup_token, sent_email.get('body'),
                          'invite: body of invitation email does not contain signup token')

    def test_20_notification_url(self):
        """ Tests designed to test the URL added in notification emails. """
        cr, uid, group_pigs = self.cr, self.uid, self.group_pigs

        # Partner data
        partner_raoul = self.res_partner.browse(cr, uid, self.partner_raoul_id)
        partner_bert_id = self.res_partner.create(cr, uid, {'name': 'bert'})
        partner_bert = self.res_partner.browse(cr, uid, partner_bert_id)
        # Mail data
        mail_mail_id = self.mail_mail.create(cr, uid, {'state': 'exception'})
        mail = self.mail_mail.browse(cr, uid, mail_mail_id)

        # Test: link for nobody -> None
        url = self.mail_mail._get_partner_access_link(cr, uid, mail)
        self.assertEqual(url, None,
                        'notification email: mails not send to a specific partner should not have any URL')

        # Test: link for partner -> signup URL
        url = self.mail_mail._get_partner_access_link(cr, uid, mail, partner=partner_bert)
        self.assertIn(partner_bert.signup_token, url,
                        'notification email: mails send to a not-user partner should contain the signup token')

        # Test: link for user -> signin
        url = self.mail_mail._get_partner_access_link(cr, uid, mail, partner=partner_raoul)
        self.assertIn('action=mail.action_mail_redirect', url,
                        'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % partner_raoul.user_ids[0].login, url,
                        'notification email: link should contain the user login')

    @mute_logger('openerp.addons.mail.mail_thread', 'openerp.models')
    def test_21_inbox_redirection(self):
        """ Tests designed to test the inbox redirection of emails notification URLs. """
        cr, uid, user_admin, group_pigs = self.cr, self.uid, self.user_admin, self.group_pigs
        model, act_id = self.ir_model_data.get_object_reference(cr, uid, 'mail', 'action_mail_inbox_feeds')
        model, port_act_id = self.ir_model_data.get_object_reference(cr, uid, 'portal', 'action_mail_inbox_feeds_portal')
        # Data: post a message on pigs
        msg_id = self.group_pigs.message_post(body='My body', partner_ids=[self.partner_bert_id, self.partner_chell_id], type='comment', subtype='mail.mt_comment')

        # No specific parameters -> should redirect to Inbox
        action = self.mail_thread.message_redirect_action(cr, self.user_raoul_id, {'params': {}})
        self.assertEqual(action.get('type'), 'ir.actions.client',
                        'URL redirection: action without parameters should redirect to client action Inbox')
        self.assertEqual(action.get('id'), act_id,
                        'URL redirection: action without parameters should redirect to client action Inbox')

        # Bert has read access to Pigs -> should redirect to form view of Pigs
        action = self.mail_thread.message_redirect_action(cr, self.user_raoul_id, {'params': {'message_id': msg_id}})
        self.assertEqual(action.get('type'), 'ir.actions.act_window',
                        'URL redirection: action with message_id for read-accredited user should redirect to Pigs')
        self.assertEqual(action.get('res_id'), group_pigs.id,
                        'URL redirection: action with message_id for read-accredited user should redirect to Pigs')

        # Bert has no read access to Pigs -> should redirect to Inbox
        action = self.mail_thread.message_redirect_action(cr, self.user_bert_id, {'params': {'message_id': msg_id}})
        self.assertEqual(action.get('type'), 'ir.actions.client',
                        'URL redirection: action without parameters should redirect to client action Inbox')
        self.assertEqual(action.get('id'), act_id,
                        'URL redirection: action without parameters should redirect to client action Inbox')

        # Chell has no read access to pigs -> should redirect to Portal Inbox
        action = self.mail_thread.message_redirect_action(cr, self.user_chell_id, {'params': {'message_id': msg_id}})
        self.assertEqual(action.get('type'), 'ir.actions.client',
                        'URL redirection: action without parameters should redirect to client action Inbox')
        self.assertEqual(action.get('id'), port_act_id,
                        'URL redirection: action without parameters should redirect to client action Inbox')

    def test_30_message_read(self):
        cr, uid, group_port_id = self.cr, self.uid, self.group_port_id

        # Data: custom subtypes
        mt_group_public_id = self.mail_message_subtype.create(cr, uid, {'name': 'group_public', 'description': 'Group changed'})
        self.ir_model_data.create(cr, uid, {'name': 'mt_group_public', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_group_public_id})
        # Data: post messages with various subtypes
        msg1_id = self.mail_group.message_post(cr, uid, group_port_id, body='Body1', type='comment', subtype='mail.mt_comment')
        msg2_id = self.mail_group.message_post(cr, uid, group_port_id, body='Body2', type='comment', subtype='mail.mt_group_public')
        msg3_id = self.mail_group.message_post(cr, uid, group_port_id, body='Body3', type='comment', subtype='mail.mt_comment')
        msg4_id = self.mail_group.message_post(cr, uid, group_port_id, body='Body4', type='comment')
        # msg5_id = self.mail_group.message_post(cr, uid, group_port_id, body='Body5', type='notification')

        # Do: Chell search messages: should not see internal notes (comment without subtype)
        msg_ids = self.mail_message.search(cr, self.user_chell_id, [('model', '=', 'mail.group'), ('res_id', '=', group_port_id)])
        self.assertEqual(set(msg_ids), set([msg1_id, msg2_id, msg3_id]),
                        'mail_message: portal user has access to messages he should not read')

        # Do: Chell read messages she can read
        self.mail_message.read(cr, self.user_chell_id, msg_ids, ['body', 'type', 'subtype_id'])

        # Do: Chell read a message she should not be able to read
        with self.assertRaises(except_orm):
            self.mail_message.read(cr, self.user_chell_id, [msg4_id], ['body', 'type', 'subtype_id'])
