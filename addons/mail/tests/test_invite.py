# -*- coding: utf-8 -*-

from .common import TestMail
from openerp.tools import mute_logger


class TestInvite(TestMail):

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_invite_email(self):
        mail_invite = self.env['mail.wizard.invite'].with_context({
            'default_res_model': 'mail.channel',
            'default_res_id': self.group_pigs.id
        }).sudo(self.user_employee.id).create({
            'partner_ids': [(4, self.user_portal.partner_id.id), (4, self.user_employee_2.partner_id.id)],
            'send_mail': True})
        mail_invite.add_followers()

        # Test: Pigs followers should contain Admin, Bert
        self.assertEqual(self.group_pigs.message_follower_ids,
                         self.user_portal.partner_id | self.user_employee_2.partner_id,
                         'invite wizard: Pigs followers after invite is incorrect, should be Admin + added follower')

        # Test: (pretend to) send email and check subject, body
        self.assertEqual(len(self._mails), 2, 'invite wizard: sent email number incorrect, should be only for Bert')
        self.assertEqual(self._mails[0].get('subject'), 'Invitation to follow Discussion group: Pigs',
                         'invite wizard: subject of invitation email is incorrect')
        self.assertEqual(self._mails[1].get('subject'), 'Invitation to follow Discussion group: Pigs',
                         'invite wizard: subject of invitation email is incorrect')
        self.assertIn('%s invited you to follow Discussion group document: Pigs' % self.user_employee.name,
                      self._mails[0].get('body'),
                      'invite wizard: body of invitation email is incorrect')
        self.assertIn('%s invited you to follow Discussion group document: Pigs' % self.user_employee.name,
                      self._mails[1].get('body'),
                      'invite wizard: body of invitation email is incorrect')
