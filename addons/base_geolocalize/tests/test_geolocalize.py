# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase
from odoo.exceptions import UserError


class TestGeoLocalize(TransactionCase):

    def test_default_openstreetmap(self):
        """ Test that openstreetmap localize service works. """
        test_partner = self.env.ref('base.res_partner_2')
        test_partner.geo_localize()
        self.assertTrue(test_partner.partner_longitude)
        self.assertTrue(test_partner.partner_latitude)
        self.assertTrue(test_partner.date_localization)

    def test_google_without_api_key(self):
        """ Without providing API key to google maps,
        the service doesn't work."""
        test_partner = self.env.ref('base.res_partner_address_4')
        self.env['ir.config_parameter'].set_param('base_geolocalize.provider',
                                                  'google')
        with self.assertRaises(UserError):
            test_partner.geo_localize()
        self.assertFalse(test_partner.partner_longitude)
        self.assertFalse(test_partner.partner_latitude)
        self.assertFalse(test_partner.date_localization)
