from unittest.mock import patch

from odoo.addons.partner_autocomplete.models.iap_autocomplete_api import IapAutocompleteApi
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestAutocompleteAddressExtended(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env['ir.module.module']._get('base_address_extended').state != 'installed':
            cls.skipTest(cls, "base_address_extended is required for these tests.")

        cls.country = cls.env['res.country'].create({
            'name': "Fake country",
            'code': 'YY',
            'enforce_cities': True,
        })
        cls.state = cls.env['res.country.state'].create({
            'name': 'Fake state',
            'code': 'FST',
            'country_id': cls.country.id,
        })
        cls.city_1 = cls.env['res.city'].create({
            'name': 'Fake city 1',
            'zipcode': '1000',
            'country_id': cls.country.id,
            'state_id': cls.state.id,
        })
        cls.city_2 = cls.env['res.city'].create({
            'name': 'Fake city 2',
            'zipcode': '2000',
            'country_id': cls.country.id,
        })

    def test_city_matched_by_zip(self):
        """When a zip is provided and matches a res.city, it is replaced by city_id."""
        iap_data = {
            'country_code': 'YY',
            'state_code': 'FST',
            'zip': '1000',
            'city': 'Fake city 1',
        }
        result = self.env['res.partner']._iap_replace_location_codes(iap_data)
        self.assertEqual(result.get('city_id', {}).get('id'), self.city_1.id)
        self.assertEqual(result.get('zip'), self.city_1.zipcode)
        self.assertNotIn('city', result)

    def test_city_matched_by_name_when_zip_unknown(self):
        """When the zip does not match but the name does, the city is still resolved."""
        iap_data = {
            'country_code': 'YY',
            'city': 'Fake city 2',
        }
        result = self.env['res.partner']._iap_replace_location_codes(iap_data)
        self.assertEqual(result.get('city_id', {}).get('id'), self.city_2.id)
        self.assertNotIn('city', result)

    def test_city_matched_by_name_only(self):
        """When no zip is provided but a name is, the city is resolved by name."""
        iap_data = {
            'country_code': 'YY',
            'city': 'Fake city 2',
        }
        result = self.env['res.partner']._iap_replace_location_codes(iap_data)
        self.assertEqual(result.get('city_id', {}).get('id'), self.city_2.id)
        self.assertNotIn('city', result)

    def test_no_city_match_keeps_raw_zip_and_city(self):
        """When neither the zip nor the name match a known res.city, the raw values are kept."""
        iap_data = {
            'country_code': 'YY',
            'zip': '9999',
            'city': 'Atlantis',
        }
        result = self.env['res.partner']._iap_replace_location_codes(iap_data)
        self.assertNotIn('city_id', result)
        self.assertEqual(result.get('zip'), '9999')
        self.assertEqual(result.get('city'), 'Atlantis')

    def test_country_without_enforce_cities_is_skipped(self):
        """When the country does not enforce cities, no res.city lookup is performed."""
        self.country.enforce_cities = False
        iap_data = {
            'country_code': 'YY',
            'zip': '1000',
            'city': 'Fake city 1',
        }
        result = self.env['res.partner']._iap_replace_location_codes(iap_data)
        self.assertNotIn('city_id', result)
        self.assertEqual(result.get('zip'), '1000')
        self.assertEqual(result.get('city'), 'Fake city 1')

    def test_enrich_by_domain_resolves_city_id(self):
        """Full flow: an IAP enrichment response gets its zip/city collapsed into a city_id."""
        def _contact_iap(local_endpoint, action, params, timeout):
            return {'data': {
                'name': 'Fake Company',
                'country_code': 'YY',
                'state_code': 'FST',
                'zip': '1000',
                'city': 'Fake city 1',
                'street': 'Fake street 1',
            }}

        with patch.object(IapAutocompleteApi, '_contact_iap', side_effect=_contact_iap):
            result = self.env['res.partner'].enrich_by_domain('fake.com')

        self.assertFalse(result.get('error'))
        self.assertEqual(result.get('name'), 'Fake Company')
        self.assertEqual(result.get('street'), 'Fake street 1')
        self.assertEqual(result.get('country_id', {}).get('id'), self.country.id)
        self.assertEqual(result.get('state_id', {}).get('id'), self.state.id)
        self.assertEqual(result.get('city_id', {}).get('id'), self.city_1.id)
        self.assertEqual(result.get('zip'), self.city_1.zipcode)
        self.assertNotIn('city', result)

        partner = self.env['res.partner'].create({
            'name': result['name'],
            'street': result['street'],
            'country_id': result['country_id']['id'],
            'state_id': result['state_id']['id'],
            'city_id': result['city_id']['id'],
        })
        self.assertEqual(partner.city_id, self.city_1)
        self.assertFalse(partner.zip)
        self.assertFalse(partner.city)
