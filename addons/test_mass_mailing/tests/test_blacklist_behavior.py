# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.addons.test_mass_mailing.tests import common
from odoo.tests.common import users


class TestAutoBlacklist(common.TestMassMailCommon):

    @users('user_marketing')
    def test_mailing_bounce_w_auto_bl(self):
        mailing = self.mailing_bl.with_user(self.env.user)
        base_parsed_values = {
            'email_from': 'toto@yaourth.com', 'to': 'tata@yaourth.com', 'message_id': '<123.321@yaourth.com>',
            'bounced_partner': self.env['res.partner'].sudo(), 'bounced_message': self.env['mail.message'].sudo()
        }

        target = self._create_test_blacklist_records()[0]
        # create bounced history of 4 statistics
        for idx in range(4):
            trace = self._create_bounce_trace(target, dt=datetime.datetime.now() - datetime.timedelta(weeks=idx+2))
            base_parsed_values.update({
                'bounced_email': target.email_normalized,
                'bounced_msg_id': [trace.message_id],
            })
            self.env['mail.thread']._routing_handle_bounce(False, base_parsed_values)

        # mass mail record: ok, not blacklisted yet
        mailing.write({'mailing_domain': [('id', 'in', target.ids)]})
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test.record.00@test.example.com'}],
            mailing, target,
            check_mail=True
        )

        # call bounced
        trace = self._create_bounce_trace(target, dt=datetime.datetime.now())
        base_parsed_values.update({
            'bounced_email': target.email_normalized,
            'bounced_msg_id': [trace.message_id],
        })
        self.env['mail.thread']._routing_handle_bounce(False, base_parsed_values)

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
