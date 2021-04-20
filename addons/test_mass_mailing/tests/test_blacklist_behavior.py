# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.addons.test_mass_mailing.tests import common
from odoo.tests.common import users


class TestAutoBlacklist(common.TestMassMailCommon):

    @users('user_marketing')
    def test_mailing_bounce_w_auto_bl(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        target = self._create_mailing_test_records()[0]
        mailing.write({'mailing_domain': [('id', 'in', target.ids)]})

        # create bounced history of 4 statistics
        for idx in range(4):
            new_mailing = mailing.copy()
            self._create_bounce_trace(new_mailing, target, dt=datetime.datetime.now() - datetime.timedelta(weeks=idx+2))
            self.gateway_mail_bounce(new_mailing, target)

        # mass mail record: ok, not blacklisted yet
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test.record.00@test.example.com'}],
            mailing, target,
            check_mail=True
        )

        # call bounced
        self.gateway_mail_bounce(mailing, target)

        # check blacklist
        blacklist_record = self.env['mail.blacklist'].sudo().search([('email', '=', target.email_normalized)])
        self.assertEqual(len(blacklist_record), 1)
        self.assertTrue(target.is_blacklisted)

        # mass mail record: ko, blacklisted
        new_mailing = mailing.copy()
        new_mailing.write({'mailing_domain': [('id', 'in', target.ids)]})
        new_mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            new_mailing._process_mass_mailing_queue()
        self.assertMailTraces(
            [{'email': 'test.record.00@test.example.com', 'state': 'ignored'}],
            new_mailing, target, check_mail=True
        )
