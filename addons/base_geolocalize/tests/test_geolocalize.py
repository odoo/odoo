# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError
from unittest.mock import patch

import odoo.tests


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

    def test_write_on_mono_record_geolocalizes_synchronously(self):
        """ Changing an address field on a single already-geolocalized partner
        re-geolocalizes it right away instead of delegating it to the cron. """
        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'street': '1 Test Street',
            'partner_latitude': 10.0,
            'partner_longitude': 20.0,
        })

        with patch.object(self.env.registry['ir.cron'], '_trigger') as mock_trigger, \
             patch.object(self.env.registry['res.partner'], 'geo_localize') as mock_geo_localize:
            partner.write({'street': '2 Test Street'})
            mock_geo_localize.assert_called_once()
            mock_trigger.assert_not_called()

        self.assertFalse(partner.should_be_geolocalized)

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
