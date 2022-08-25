# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPartnerAutocompleteNeutralize(TransactionCase):

    def test_partner_autocomplete_neutralize(self):
        iap_key = 'iap.partner_autocomplete.endpoint'
        self.env['ir.config_parameter'].create({
            'key': iap_key,
            'value': 'fake test iap partner autocomplete endpoint'
        })

        self.env['iap.account']._neutralize()
        self.assertEqual(self.env['ir.config_parameter'].get_param(iap_key), 'https://iap-services-test.odoo.com')
