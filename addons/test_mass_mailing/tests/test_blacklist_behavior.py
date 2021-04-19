# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.addons.test_mass_mailing.tests import common
from odoo.tests.common import users
from odoo.addons.mass_mailing.models.mail_thread import BLACKLIST_MAX_BOUNCED_LIMIT


class TestAutoBlacklist(common.TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAutoBlacklist, cls).setUpClass()
        cls.target_rec = cls._create_mailing_test_records()[0]
        cls.mailing_bl.write({'mailing_domain': [('id', 'in', cls.target_rec.ids)]})

    @users('user_marketing')
    def test_mailing_bounce_w_auto_bl(self):
        self._test_mailing_bounce_w_auto_bl(None)

    @users('user_marketing')
    def test_mailing_bounce_w_auto_bl_partner(self):
        bounced_partner = self.env['res.partner'].sudo().create({
            'name': 'Bounced Partner',
            'email': self.target_rec.email_from,
            'message_bounce': BLACKLIST_MAX_BOUNCED_LIMIT,
        })
        self._test_mailing_bounce_w_auto_bl({'bounced_partner': bounced_partner})

    @users('user_marketing')
    def test_mailing_bounce_w_auto_bl_partner_duplicates(self):
        bounced_partners = self.env['res.partner'].sudo().create({
            'name': 'Bounced Partner1',
            'email': self.target_rec.email_from,
            'message_bounce': BLACKLIST_MAX_BOUNCED_LIMIT,
        }) | self.env['res.partner'].sudo().create({
            'name': 'Bounced Partner2',
            'email': self.target_rec.email_from,
            'message_bounce': BLACKLIST_MAX_BOUNCED_LIMIT,
        })
        self._test_mailing_bounce_w_auto_bl({'bounced_partner': bounced_partners})

    def _test_mailing_bounce_w_auto_bl(self, bounce_base_values):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        target = self.env['mailing.test.blacklist'].browse(self.target_rec.ids)

        # create bounced history of 4 statistics
        for idx in range(4):
            new_mailing = mailing.copy()
            self._create_bounce_trace(new_mailing, target, dt=datetime.datetime.now() - datetime.timedelta(weeks=idx+2))
            self.gateway_mail_bounce(new_mailing, target, bounce_base_values)

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
        self.gateway_mail_bounce(mailing, target, bounce_base_values)

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
