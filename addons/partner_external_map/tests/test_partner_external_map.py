# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import common

from ..hooks import set_default_map_settings


class TestPartnerExternalMap(common.TransactionCase):
    def setUp(self):
        super(TestPartnerExternalMap, self).setUp()
        self.user = self.env["res.users"].create(
            {
                "name": "Test user",
                "login": "test_login",
                "context_map_website_id": self.ref("partner_external_map.google_maps"),
                "context_route_map_website_id": self.ref(
                    "partner_external_map.google_maps"
                ),
            }
        )
        self.user.partner_id.city = "Tomelloso"
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test partner",
                "city": "Madrid",
                "street": "street_test",
                "street2": "street2_test",
                "state_id": self.ref("base.state_es_m"),
                "country_id": self.ref("base.es"),
            }
        )

    def test_post_init_hook(self):
        # Call this again for coverage purposes, but it has been already run
        set_default_map_settings(self.cr, self.registry)
        usrs = self.env["res.users"].search([])
        self.assertTrue(all([u.context_map_website_id.id for u in usrs]))
        self.assertTrue(all([u.context_route_map_website_id.id for u in usrs]))
        self.assertEqual(
            self.env.user.partner_id, self.env.user.context_route_start_partner_id
        )

    def test_create_user(self):
        self.assertEqual(self.user.partner_id, self.user.context_route_start_partner_id)

    def test_open_map(self):
        action = self.partner.with_user(self.user.id).open_map()
        self.assertEqual(
            action["url"],
            "https://www.google.com/maps?ie=UTF8"
            "&q=street_test street2_test Madrid Madrid Spain",
        )

    def test_open_route_map(self):
        action = self.partner.with_user(self.user.id).open_route_map()
        self.assertEqual(
            action["url"],
            "https://www.google.com/maps?saddr=Tomelloso"
            "&daddr=street_test street2_test Madrid Madrid "
            "Spain&directionsmode=driving",
        )

    def test_open_map_with_coordinates(self):
        # Simulate that we have the base_geolocalize module installed creating
        # by hand the variables - This can't be done with routes
        partner = self.partner.with_user(self.user.id)
        partner.partner_latitude = 39.15837
        partner.partner_longitude = -3.02145
        action = partner.open_map()
        self.assertTrue(action["url"].startswith("https://www.google.com/maps?z="))
        self.assertIn("39.15837", action["url"])
        self.assertIn("-3.02145", action["url"])

    def test_exception_no_addr(self):
        self.partner.write(
            {
                "city": False,
                "street": False,
                "street2": False,
                "state_id": False,
                "country_id": False,
            }
        )
        with self.assertRaises(UserError):
            self.partner.with_user(self.user.id).open_route_map()

    def test_exception_no_map_website(self):
        self.user.context_map_website_id = False
        with self.assertRaises(UserError):
            self.partner.with_user(self.user.id).open_map()

    def test_exception_no_map_route_website(self):
        self.user.context_route_start_partner_id = False
        with self.assertRaises(UserError):
            self.partner.with_user(self.user.id).open_route_map()

    def test_exception_no_starting_partner(self):
        self.user.context_route_map_website_id = False
        with self.assertRaises(UserError):
            self.partner.with_user(self.user.id).open_route_map()

    def test_exception_no_address_url(self):
        self.user.context_map_website_id.address_url = False
        with self.assertRaises(UserError):
            self.partner.with_user(self.user.id).open_map()

    def test_exception_no_route_address_url(self):
        self.user.context_map_website_id.route_address_url = False
        with self.assertRaises(UserError):
            self.partner.with_user(self.user.id).open_route_map()
