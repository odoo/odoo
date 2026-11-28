# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCityTimezone(TransactionCase):

    def _city(self, name, country_code):
        return self.env['res.city'].search([
            ('name', '=', name),
            ('country_id.code', '=', country_code),
            ('geonames_id', '!=', False),
        ])

    def test_loaded_timezones(self):
        for name, country_code, tz in [
            ('Seattle', 'US', 'America/Los_Angeles'),
            ('El Paso', 'US', 'America/Denver'),
            ('Liège', 'BE', 'Europe/Brussels'),
            ('São Paulo', 'BR', 'America/Sao_Paulo'),
        ]:
            with self.subTest(city=name):
                city = self._city(name, country_code)
                self.assertEqual(len(city), 1)
                self.assertEqual(city.tz, tz)
                self.assertTrue(city.latitude and city.longitude)

    def test_reload_is_idempotent(self):
        City = self.env['res.city'].with_context(active_test=False)
        count = City.search_count([])
        City._load_geonames_cities()
        self.assertEqual(City.search_count([]), count)

    def test_existing_city_is_completed(self):
        """A city created by another module is completed, not duplicated."""
        # Norway: no localization provides cities, so no other "Tromsø" exists
        norway = self.env.ref('base.no')
        City = self.env['res.city']
        tromso = self._city('Tromsø', 'NO')
        geonames_id = tromso.geonames_id
        tromso.unlink()
        existing = City.create({'name': 'Tromso', 'country_id': norway.id})

        City._load_geonames_cities()

        self.assertEqual(existing.geonames_id, geonames_id)
        self.assertEqual(existing.tz, 'Europe/Oslo')
        self.assertEqual(City.search_count([('geonames_id', '=', geonames_id)]), 1)

    def test_get_city_timezone(self):
        City = self.env['res.city']
        us = self.env.ref('base.us')
        self.assertEqual(City._get_city_timezone(us, 'seattle'), 'America/Los_Angeles')
        self.assertEqual(City._get_city_timezone(self.env.ref('base.br'), 'Sao Paulo'), 'America/Sao_Paulo')
        self.assertFalse(City._get_city_timezone(us, 'Nowhere Town'))
        # letters without a decomposed form (ø, ł, ß...) match their plain version
        self.assertEqual(City._get_city_timezone(self.env.ref('base.no'), 'TROMSO'), 'Europe/Oslo')
        # several Springfields in different timezones
        self.assertFalse(City._get_city_timezone(us, 'Springfield'))
