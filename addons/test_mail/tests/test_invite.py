# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests import common
from odoo.tools import mute_logger


class TestInvite(common.BaseFunctionalTest, common.MockEmails):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_invite_email(self):
        test_partner = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})

        mail_invite = self.env['mail.wizard.invite'].with_context({
            'default_res_model': 'mail.test.simple',
            'default_res_id': self.test_record.id
        }).sudo(self.user_employee.id).create({
            'partner_ids': [(4, test_partner.id), (4, self.user_admin.partner_id.id)],
            'send_mail': True})
        mail_invite.add_followers()

        # check added followers and that emails were sent
        self.assertEqual(self.test_record.message_partner_ids,
                         test_partner | self.user_admin.partner_id)
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'),
                         self.env['mail.channel'])
        self.assertEqual(len(self._mails), 2)
