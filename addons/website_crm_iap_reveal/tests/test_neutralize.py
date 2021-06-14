# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestIapLeadWebsiteNeutralize(TransactionCase):

    def test_iap_lead_website_neutralize(self):
        ICP = self.env['ir.config_parameter']
        key = 'reveal.endpoint'
        ICP.set_param(key, 'Fake test reveal endpoint')

        self.env['iap.account']._neutralize()
        self.assertEqual(ICP.get_param(key), 'https://iap-services-test.odoo.com')
