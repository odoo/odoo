# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSnailMailNeutralize(TransactionCase):

    def test_snailmail_neutralize(self):
        key = 'snailmail.endpoint'
        self.env['ir.config_parameter'].create({
            'key': key,
            'value': 'fake test snailmail endpoint'
        })

        self.env['iap.account']._neutralize()
        self.assertEqual(self.env['ir.config_parameter'].get_param(key), 'https://iap-services-test.odoo.com')
