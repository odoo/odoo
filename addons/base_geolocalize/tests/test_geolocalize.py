# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError
from unittest.mock import patch

import requests

import odoo.tests
from odoo.addons.base_geolocalize.models.base_geocoder import GeoCodingError


@odoo.tests.tagged('external', '-standard')
@tagged('at_install', '-post_install')  # LEGACY at_install
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
        self.env['ir.config_parameter'].set_str('base_geolocalize.geo_provider', google_map)
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

        with patch.object(self.env.registry['bus.bus'], '_sendone') as mock_send:
            partner1 = partner.create({'name': 'Test A'})
            partner1.with_context(force_geo_localize=True).geo_localize()
            mock_send.assert_called_with(self.env.user, 'simple_notification', {
                'type': 'danger',
                'title': "Warning",
                'message': "No match found for Test A address(es).",
            })
            mock_send.reset_mock()

            partner2 = partner.create({'name': "", 'parent_id': partner1.id, 'type': 'other'})
            partner2.with_context(force_geo_localize=True).geo_localize()
            mock_send.assert_called_with(self.env.user, 'simple_notification', {
                'type': 'danger',
                'title': "Warning",
                'message': "No match found for Test A, Other address(es).",
            })
            mock_send.reset_mock()

    def test_write_triggers_regeolocalization_on_address_change(self):
        """ Changing an address field on several already-geolocalized partners at once
        flags them for re-geolocalization and triggers the cron. Further, partners that
        were not previously geolocalized should not be geolocalized on address change. """
        partners = self.env['res.partner'].create([
            {
                'name': f'Test Partner {i}',
                'street': f'{i} Test Street',
                'partner_latitude': 10.0,
                'partner_longitude': 20.0,
            }
            for i in range(2)
        ])
        self.assertFalse(partners.filtered('should_be_geolocalized'))

        with patch.object(self.env.registry['ir.cron'], '_trigger') as mock_trigger:
            # unrelated field: no flag, no trigger
            partners.write({'email': 'test@test.example.com'})
            self.assertFalse(any(partners.mapped('should_be_geolocalized')))
            mock_trigger.assert_not_called()

            # coordinates written directly: no flag, no trigger
            partners.write({'partner_latitude': 11.0, 'partner_longitude': 21.0})
            self.assertFalse(any(partners.mapped('should_be_geolocalized')))
            mock_trigger.assert_not_called()

            # address field change on already-geolocalized partners: flagged + cron triggered
            partners.write({'street': 'New Street'})
            self.assertTrue(all(partners.mapped('should_be_geolocalized')))
            mock_trigger.assert_called_once()

        # once the cron re-geolocalizes them, the flag is cleared again
        with patch.object(self.env.registry['res.partner'], '_geo_localize', return_value=(1.0, 2.0)):
            partners.with_context(force_geo_localize=True).geo_localize()

        self.assertFalse(partners.filtered('should_be_geolocalized'))

    def test_write_address_change_without_coordinates_does_not_flag(self):
        """ A partner that was never geolocalized must not be re-geolocalized. """
        partner = self.env['res.partner'].create({'name': 'Test Partner', 'street': '1 Test Street'})
        partner.write({'street': '2 Test Street'})
        self.assertFalse(partner.should_be_geolocalized)

    def test_geo_localize_stores_error_for_partners_without_match(self):
        """ Partners whose address cannot be resolved are flagged with an error
        and not retried until their address changes. """
        partner = self.env['res.partner'].create({
            'name': "Test A", 'street': "1 Fake Street", 'zip': "1000", 'city': "Bucarest",
            'should_be_geolocalized': True,
        })
        with patch(
            'odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize',
            return_value=None,
        ):
            partner.with_context(force_geo_localize=True).geo_localize()
        self.assertEqual(
            partner.geo_localization_error,
            "No match found for address: 1 Fake Street, 1000 Bucarest",
        )
        self.assertFalse(partner.should_be_geolocalized)

    def test_geo_localize_clears_error_for_partners_with_match(self):
        """ Partners whose address is resolved are not flagged with an error anymore. """
        partner = self.env['res.partner'].create({
            'name': "Test A", 'geo_localization_error': "No match found for this address.",
        })
        with patch(
            'odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize',
            return_value=(44.4323, 26.1063),
        ):
            partner.with_context(force_geo_localize=True).geo_localize()
        self.assertFalse(partner.geo_localization_error)

    def test_editing_the_address_clears_the_error(self):
        """ Fixing a typo in the address allows a new geolocation attempt. """
        partner = self.env['res.partner'].create({
            'name': "Test A", 'city': "Bucarest", 'geo_localization_error': "No match found for this address.",
        })
        partner.city = "Bucharest"
        self.assertFalse(partner.geo_localization_error)

    def test_geo_localize_stores_error_when_server_fails(self):
        """ A provider failure is saved on the partner instead of aborting the
        transaction, no fallback query is made and the partner is not retried. """
        partner = self.env['res.partner'].create({'name': "Test A", 'city': "Bucharest", 'should_be_geolocalized': True})
        with patch(
            'odoo.addons.base_geolocalize.models.base_geocoder.BaseGeocoder.geo_find',
            side_effect=GeoCodingError("Error with geolocation server: timeout"),
        ) as mock_geo_find:
            partner.with_context(force_geo_localize=True).geo_localize()
        mock_geo_find.assert_called_once()
        self.assertEqual(partner.geo_localization_error, "Error with geolocation server: timeout")
        self.assertFalse(partner.date_localization)
        self.assertFalse(partner.should_be_geolocalized)

    def test_openstreetmap_errors(self):
        """ "No match" is returned as None, every other failure raises a
        GeoCodingError describing what went wrong. """
        def response(status_code, content):
            res = requests.Response()
            res.status_code = status_code
            res._content = content
            return res

        def call_openstreetmap(**requests_get_mock):
            with patch('odoo.addons.base_geolocalize.models.base_geocoder.time'), \
                 patch('requests.get', **requests_get_mock):
                return self.env['base.geocoder']._call_openstreetmap("1 Fake Street")

        for requests_get_mock, reason in [
            ({'side_effect': requests.Timeout()}, "timeout"),
            ({'side_effect': requests.ConnectionError()}, "server not reached"),
            ({'return_value': response(429, b"<html></html>")}, "server answered with HTTP status 429"),
            ({'return_value': response(200, b"<html></html>")}, "unexpected response format"),
            ({'return_value': response(200, b'[{"lat": "x"}]')}, "unexpected response format"),
        ]:
            with self.subTest(reason=reason), self.assertRaises(GeoCodingError) as e:
                call_openstreetmap(**requests_get_mock)
            self.assertEqual(str(e.exception), f"Error with geolocation server: {reason}")

        self.assertIsNone(call_openstreetmap(return_value=response(200, b"[]")))
        self.assertEqual(
            call_openstreetmap(return_value=response(200, b'[{"lat": "44.4", "lon": "26.1"}]')),
            (44.4, 26.1),
        )
