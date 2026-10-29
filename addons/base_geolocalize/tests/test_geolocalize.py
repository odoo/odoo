# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.tests import TransactionCase
from odoo.exceptions import UserError
from odoo.tools import mute_logger
from unittest.mock import patch

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


@odoo.tests.tagged('-at_install', 'post_install')
class TestPartnerGeoLocalization(TransactionCase):

    def test_geo_localization_notification(self):
        """ Warning message is sent to the user when geolocation fails. """
        partner = self.env['res.partner']
        user_partner = self.env.user.partner_id

        with patch.object(self.env.registry['bus.bus'], '_sendone') as mock_send:
            partner1 = partner.create({'name': 'Test A'})
            partner1.with_context(force_geo_localize=True).geo_localize()
            mock_send.assert_called_with(user_partner, 'simple_notification', {
                'type': 'danger',
                'title': "Warning",
                'message': "No match found for Test A address(es).",
            })
            mock_send.reset_mock()

            partner2 = partner.create({'name': "", 'parent_id': partner1.id, 'type': 'other'})
            partner2.with_context(force_geo_localize=True).geo_localize()
            mock_send.assert_called_with(user_partner, 'simple_notification', {
                'type': 'danger',
                'title': "Warning",
                'message': "No match found for Test A, Other Address address(es).",
            })
            mock_send.reset_mock()

    def _clear_osm_rate_limiter(self):
        if hasattr(self.env.registry, '_geocoding_last_calls'):
            self.env.registry._geocoding_last_calls.pop('osm', None)

    @mute_logger('odoo.addons.base_geolocalize.models.base_geocoder')
    def test_01_rate_limit_trigger(self):
        """ Test that calling the service twice immediately raises UserError """
        self._clear_osm_rate_limiter()
        self.env["base.geocoder"]._check_geocoding_rate_limit('osm')

        with self.assertRaises(UserError):
            self.env["base.geocoder"]._check_geocoding_rate_limit('osm')

    def test_02_system_parameter_respect(self):
        """ Test that the limiter respects the 'geocoder.osm.minimum_delta' parameter """
        self._clear_osm_rate_limiter()
        self.env['ir.config_parameter'].sudo().set_param('geocoder.osm.minimum_delta', 0.0)

        # This should not raise an error because delta is 0
        self.env["base.geocoder"]._check_geocoding_rate_limit('osm')
        self.env["base.geocoder"]._check_geocoding_rate_limit('osm')

    def test_03_cooldown_passing(self):
        """ Test that after waiting the delta, the request is allowed again """
        self._clear_osm_rate_limiter()
        self.env['ir.config_parameter'].sudo().set_param('geocoder.osm.minimum_delta', 0.1)
        self.env["base.geocoder"]._check_geocoding_rate_limit('osm')
        time.sleep(0.15)

        try:
            self.env["base.geocoder"]._check_geocoding_rate_limit('osm')
        except UserError:
            self.fail("_check_geocoding_rate_limit raised UserError even after waiting!")
