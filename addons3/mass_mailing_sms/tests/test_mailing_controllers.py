# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo.tests.common import users
from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.tests import HttpCase

class TestMailingListSms(HttpCase, MassSMSCommon):

    @users('user_marketing')
    def test_controller_unsubscribe(self):
        """ Test unsubscribe controller from a phone number, including phone
        formatting and validation """
        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'phone': '+91 1234657890',
        })

        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'body_plaintext': 'Coucou hibou',
            'mailing_type': 'sms',
            'mailing_model_id': self.env['ir.model']._get_id('res.partner'),
            'mailing_domain': [('id', '=', partner.id)],
            'subject': 'Test',
            'sms_allow_unsubscribe': True,
        })
        mailing.action_send_sms()

        trace = mailing.mailing_trace_ids.filtered(lambda t: t.res_id == partner.id)
        self.assertTrue(trace, 'Trace not found for the partner')

        unsubscribe_url = werkzeug.urls.url_join(mailing.get_base_url(), f'/sms/{mailing.id}/unsubscribe/{trace.sms_code}')
        response = self.opener.get(url=unsubscribe_url, data={'sms_number': trace.sms_number})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(partner.phone_blacklisted, 'Partner not unsubscribed')
