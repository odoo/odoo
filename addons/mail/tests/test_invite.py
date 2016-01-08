# -*- coding: utf-8 -*-

from .common import TestMail
from openerp.tools import mute_logger


class TestInvite(TestMail):

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_invite_email(self):
        test_group = self.env['mail.channel'].sudo(self.user_employee.id).with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_channel_noautofollow': True,
        }).create({
            'name': 'Test Group',
            'public': 'private',
        })
        mail_invite = self.env['mail.wizard.invite'].with_context({
            'default_res_model': 'mail.channel',
            'default_res_id': test_group.id
        }).sudo(self.user_employee.id).create({
            'partner_ids': [(4, self.user_portal.partner_id.id), (4, self.partner_1.id)],
            'send_mail': True})
        mail_invite.add_followers()

        # Test: Test Group followers should contain Admin, Bert
        self.assertEqual(test_group.message_partner_ids,
                         self.user_portal.partner_id | self.partner_1,
                         'invite wizard: Test Group followers after invite is incorrect, should be Admin + added follower')
        self.assertEqual(test_group.message_follower_ids.mapped('channel_id'),
                         self.env['mail.channel'],
                         'invite wizard: Test Group followers after invite is incorrect, should not have channels')

        # Test: (pretend to) send email and check subject, body
        self.assertEqual(len(self._mails), 2, 'invite wizard: sent email number incorrect, should be only for Bert')
        self.assertEqual(self._mails[0].get('subject'), 'Invitation to follow Discussion channel: Test Group',
                         'invite wizard: subject of invitation email is incorrect')
        self.assertEqual(self._mails[1].get('subject'), 'Invitation to follow Discussion channel: Test Group',
                         'invite wizard: subject of invitation email is incorrect')
        self.assertIn('%s invited you to follow Discussion channel document: Test Group' % self.user_employee.name,
                      self._mails[0].get('body'),
                      'invite wizard: body of invitation email is incorrect')
        self.assertIn('%s invited you to follow Discussion channel document: Test Group' % self.user_employee.name,
                      self._mails[1].get('body'),
                      'invite wizard: body of invitation email is incorrect')
