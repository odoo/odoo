# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import Form, tagged, TransactionCase
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

    def test_geo_localize_flags_partners_without_match(self):
        """ Partners whose address cannot be resolved are flagged as failed. """
        partner = self.env['res.partner'].create({'name': "Test A"})
        with patch(
            'odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize',
            return_value=None,
        ):
            partner.with_context(force_geo_localize=True).geo_localize()
        self.assertTrue(partner.geo_localization_failed)

    def test_geo_localize_unflags_partners_with_match(self):
        """ Partners whose address is resolved are not flagged as failed anymore. """
        partner = self.env['res.partner'].create({
            'name': "Test A", 'geo_localization_failed': True,
        })
        with patch(
            'odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize',
            return_value=(44.4323, 26.1063),
        ):
            partner.with_context(force_geo_localize=True).geo_localize()
        self.assertFalse(partner.geo_localization_failed)

    def test_editing_the_address_clears_the_failure_flag(self):
        """ Fixing a typo in the address allows a new geolocation attempt. """
        partner = self.env['res.partner'].create({
            'name': "Test A", 'city': "Bucarest", 'geo_localization_failed': True,
        })
        with Form(partner) as partner_form:
            partner_form.city = "Bucharest"
        self.assertFalse(partner.geo_localization_failed)
