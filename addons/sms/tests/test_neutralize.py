# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSmsNeutralize(TransactionCase):

    def test_sms_neutralize(self):
        sms_key = 'sms.endpoint'
        self.env['ir.config_parameter'].create({
            'key': sms_key,
            'value': 'fake test sms endpoint'
        })

        self.env['iap.account']._neutralize()
        self.assertEqual(self.env['ir.config_parameter'].get_param(sms_key), 'https://iap-services-test.odoo.com')
