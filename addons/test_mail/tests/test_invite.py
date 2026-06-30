# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_followers')
class TestInvite(MailCommon):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_invite_email(self):
        test_record = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        test_partner = self.env['res.partner'].with_context(self._test_context).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})

        mail_invite = self.env['mail.followers.edit'].with_context({
            'default_res_model': 'mail.test.simple',
            'default_res_ids': [test_record.id],
        }).with_user(self.user_employee).create({'partner_ids': [(4, test_partner.id), (4, self.user_admin.partner_id.id)],
            'notify': True})
        with self.mock_mail_app(), self.mock_mail_gateway():
            mail_invite.edit_followers()

        # Check added followers and that notifications are sent.
        # Admin notification preference is inbox so the notification must be of inbox type
        # while partner_employee must receive it by email.
        self.assertEqual(test_record.message_partner_ids,
                         test_partner | self.user_admin.partner_id)
        self.assertEqual(len(self._new_msgs), 1)
        self.assertEqual(len(self._mails), 1)
        self.assertSentEmail(self.partner_employee, [test_partner])
        self.assertNotSentEmail([self.partner_admin])
        self.assertNotified(
            self._new_msgs[0],
            [{'partner': self.partner_admin, 'type': 'inbox', 'is_read': False}]
        )

        # Remove followers
        mail_remove = self.env['mail.followers.edit'].with_context({
            'default_res_model': 'mail.test.simple',
            'default_res_ids': [test_record.id],
        }).with_user(self.user_employee).create({
            "operation": "remove",
            'partner_ids': [(4, test_partner.id), (4, self.user_admin.partner_id.id)]})

        with self.mock_mail_app(), self.mock_mail_gateway():
            mail_remove.edit_followers()

        # Check removed followers and that notifications are sent.
        self.assertEqual(test_record.message_partner_ids, self.env["res.partner"])
