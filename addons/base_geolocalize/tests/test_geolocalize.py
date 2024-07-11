# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase
from odoo.exceptions import UserError

import odoo.tests


@odoo.tests.tagged('external', '-standard')
class TestGeoLocalize(TransactionCase):

    def test_default_openstreetmap(self):
        """ Test that openstreetmap localize service works. """
        test_partner = self.env.ref('base.res_partner_2')
        test_partner.geo_localize()
        self.assertTrue(test_partner.partner_longitude)
        self.assertTrue(test_partner.partner_latitude)
        self.assertTrue(test_partner.date_localization)

        # we don't check here that the localization is at right place
        # but just that result is realistic float coordonates
        self.assertTrue(float(test_partner.partner_longitude) != 0.0)
        self.assertTrue(float(test_partner.partner_latitude) != 0.0)

    def test_googlemap_without_api_key(self):
        """ Without providing API key to google maps,
        the service doesn't work."""
        test_partner = self.env.ref('base.res_partner_address_4')
        google_map = self.env.ref('base_geolocalize.geoprovider_google_map').id
        self.env['ir.config_parameter'].set_param('base_geolocalize.geo_provider', google_map)
        with self.assertRaises(UserError):
            test_partner.geo_localize()
        self.assertFalse(test_partner.partner_longitude)
        self.assertFalse(test_partner.partner_latitude)
        self.assertFalse(test_partner.date_localization)
