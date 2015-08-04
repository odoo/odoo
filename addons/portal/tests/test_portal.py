# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail
from openerp.tools.misc import mute_logger


class test_portal(TestMail):

    def test_mail_compose_access_rights(self):
        self.group_pigs.write({'group_public_id': self.env.ref('base.group_portal').id})
        port_msg = self.group_pigs.message_post(body='Message')

        # Do: Chell comments Pigs, ok because can write on it (public group)
        self.group_pigs.sudo(self.user_portal).message_post(body='I love Pigs', message_type='comment', subtype='mail.mt_comment')
        # Do: Chell creates a mail.compose.message record on Pigs, because he uses the wizard
        compose = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.channel',
            'default_res_id': self.group_pigs.id
        }).sudo(self.user_portal).create({
            'subject': 'Subject',
            'body': 'Body text',
            'partner_ids': []})
        compose.send_mail()

        # Do: Chell replies to a Pigs message using the composer
        compose = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_parent_id': port_msg.id
        }).sudo(self.user_portal).create({
            'subject': 'Subject',
            'body': 'Body text'})
        compose.send_mail()

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_invite_email_portal(self):
        group_pigs = self.group_pigs
        base_url = self.env['ir.config_parameter'].get_param('web.base.url', default='')
        # Carine Poilvache, with email, should receive emails for comments and emails
        partner_carine = self.env['res.partner'].create({'name': 'Carine Poilvache', 'email': 'c@c'})

        # Do: create a mail_wizard_invite, validate it
        self._init_mock_build_email()
        mail_invite = self.env['mail.wizard.invite'].with_context({
            'default_res_model': 'mail.channel',
            'default_res_id': group_pigs.id}).create({
            'partner_ids': [(4, partner_carine.id)], 'send_mail': True})
        mail_invite.add_followers()
        # Test: Pigs followers should contain Admin and Bert
        self.assertEqual(group_pigs.message_partner_ids, partner_carine)
        # Test: partner must have been prepared for signup
        self.assertTrue(partner_carine.signup_valid, 'partner has not been prepared for signup')
        self.assertTrue(base_url in partner_carine.signup_url, 'signup url is incorrect')
        self.assertTrue(self.env.cr.dbname in partner_carine.signup_url, 'signup url is incorrect')
        self.assertTrue(partner_carine.signup_token in partner_carine.signup_url, 'signup url is incorrect')
        # Test: (pretend to) send email and check subject, body
        self.assertEqual(len(self._mails), 1, 'sent email number incorrect, should be only for Bert')
        for sent_email in self._mails:
            self.assertEqual(
                sent_email.get('subject'), 'Invitation to follow Discussion group: Pigs',
                'invite: subject of invitation email is incorrect')
            self.assertIn(
                'Administrator invited you to follow Discussion group document: Pigs', sent_email.get('body'),
                'invite: body of invitation email is incorrect')
            self.assertIn(
                partner_carine.signup_token, sent_email.get('body'),
                'invite: body of invitation email does not contain signup token')

    def test_mail_notification_url_partner_portal(self):
        # Mail data
        mail = self.env['mail.mail'].create({'state': 'exception'})
        # Test: link for nobody -> None
        url = mail._get_partner_access_link()
        self.assertEqual(url, None,
                         'notification email: mails not send to a specific partner should not have any URL')
        # Test: link for partner -> signup URL
        url = mail._get_partner_access_link(partner=self.partner_1)
        self.assertIn(self.partner_1.signup_token, url,
                      'notification email: mails send to a not-user partner should contain the signup token')
        # Test: link for user -> signin
        url = mail._get_partner_access_link(partner=self.user_employee.partner_id)
        self.assertIn('action=mail.action_mail_redirect', url,
                      'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % self.user_employee.login, url,
                      'notification email: link should contain the user login')

    @mute_logger('openerp.addons.mail.models.mail_mail', 'openerp.models')
    def test_inbox_redirection_portal(self):
        group_pigs = self.group_pigs
        port_act_id = self.ref('portal.mail_message_action_inbox_portal')
        # Data: post a message on pigs
        msg = group_pigs.message_post(body='My body', partner_ids=[self.user_employee.partner_id.id, self.user_portal.partner_id.id], type='comment', subtype='mail.mt_comment')
        # Chell has no read access to pigs -> should redirect to Portal Inbox
        action = self.env['mail.thread'].with_context({'params': {'message_id': msg.id}}).sudo(self.user_portal).message_redirect_action()
        self.assertEqual(action.get('type'), 'ir.actions.act_window',
                        'URL redirection: action without parameters should redirect to act_window Inbox')
        self.assertEqual(action.get('id'), port_act_id,
                        'URL redirection: action without parameters should redirect to act_window Inbox')
