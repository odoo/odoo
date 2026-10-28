from unittest.mock import patch
from odoo.tests import common, tagged
from odoo.addons.partner_autocomplete.tests.common import MockIAPPartnerAutocomplete
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestResCompany(common.TransactionCase, MockIAPPartnerAutocomplete):

    @classmethod
    def setUpClass(cls):
        super(TestResCompany, cls).setUpClass()
        cls._init_mock_partner_autocomplete()

    def test_enrich(self):
        company = self.env['res.company'].create({'name': "Test Company 1"})
        with self.mockPartnerAutocomplete():
            res = company._enrich()
            self.assertFalse(res)

        company.write({'email': 'friedrich@heinrich.de'})
        with self.mockPartnerAutocomplete():
            # asserts are synchronized with default mock values
            res = company._enrich()
            self.assertTrue(res)
            self.assertEqual(company.country_id, self.env.ref('base.de'))

    def test_extract_company_domain(self):
        company_1 = self.add_company('base.test_company', {'name': "Test Company 1"})

        company_1.website = 'http://www.info.proximus.be/faq/test'
        self.assertEqual(company_1.partner_id._get_partner_domain(), "proximus.be")

        company_1.email = 'info@waterlink.be'
        self.assertEqual(company_1.partner_id._get_partner_domain(), "waterlink.be")

        company_1.website = False
        company_1.email = False
        self.assertEqual(company_1.partner_id._get_partner_domain(), False)

        company_1.email = "at@"
        self.assertEqual(company_1.partner_id._get_partner_domain(), False)

        company_1.website = "http://superFalsyWebsiteName"
        self.assertEqual(company_1.partner_id._get_partner_domain(), False)

        company_1.website = "http://www.superwebsite.com"
        self.assertEqual(company_1.partner_id._get_partner_domain(), 'superwebsite.com')

        company_1.website = "http://superwebsite.com"
        self.assertEqual(company_1.partner_id._get_partner_domain(), 'superwebsite.com')

        company_1.website = "http://localhost:8069/%7Eguido/Python.html"
        self.assertEqual(company_1.partner_id._get_partner_domain(), False)

        company_1.website = "http://runbot.odoo.com"
        self.assertEqual(company_1.partner_id._get_partner_domain(), 'odoo.com')

        company_1.website = "http://www.example.com/biniou"
        self.assertEqual(company_1.partner_id._get_partner_domain(), False)

        company_1.website = "http://www.cwi.nl:80/%7Eguido/Python.html"
        self.assertEqual(company_1.partner_id._get_partner_domain(), "cwi.nl")

    def test_enrich_by_duns_with_incorrect_vat(self):
        """
        Ensure the VAT number is removed when the partner autocomplete return an incorrect VAT number
        """

        # Mock the company details from the JS call `enrichCompany(company)`
        be_company_data = {
            'city': 'Brussels',
            'duns': 'BE1234567',
            'name': 'Test BE Company',
            'country_id': {
                'id': self.ref('base.be'), 'display_name': 'Belgium'
            },
            'query': 'BE Comp',
            'description': 'Belgium'
        }

        original_method = self.env.registry['iap.autocomplete.api']._request_partner_autocomplete

        def patched_request(self_api, endpoint, params, timeout=15):
            response, error = original_method(self_api, endpoint, params, timeout=timeout)

            response = {'request_code': 200, 'total_cost': 0, 'credit_error': True, 'data': {'vat': 'BE1234567'}}
            return response, error

        with patch.object(self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete', patched_request):
            result = self.env['res.partner'].enrich_by_duns('BE1234567', company_data=be_company_data)
            self.assertEqual(result.get('vat'), '')

    @mute_logger('odoo.addons.base.models.res_partner')
    def test_enrich_by_duns_with_incorrect_additional_identifiers(self):
        """
        Ensure the additional identifiers are removed when the partner autocomplete returns an invalid value
        (e.g. the Croatian MB instead of a GLN in HR_EN)
        """
        hr_company_data = {
            'duns': '672827474',
            'name': 'Test HR Company',
            'country_id': {
                'id': self.ref('base.hr'), 'display_name': 'Croatia'
            },
        }

        def patched_request(self_api, endpoint, params, timeout=15):
            return {'data': {'additional_identifiers': {'DUNS': '672827474', 'HR_EN': '02342359'}}}, False

        with patch.object(self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete', patched_request):
            result = self.env['res.partner'].enrich_by_duns('672827474', company_data=hr_company_data)
        self.assertEqual(result.get('additional_identifiers'), {'DUNS': '672827474'})

    def test_enrich_with_industry_id(self):
        """Test that the industry ID is extracted from the enrichment data."""
        company = self.env['res.company'].create({
            'name': "Test Company 1",
            'email': 'demo@testmail.com',
        })
        contact = self.env['res.partner'].create({
            'name': "Test Contact",
            'parent_id': company.partner_id.id,
        })

        industry = self.env.ref('base.res_partner_industry_Q')
        company_data = {'industry_id': {'display_name': industry.display_name, 'id': industry.id}}

        with patch.object(self.env.registry['res.partner'], 'enrich_by_domain', return_value=company_data):
            self.assertTrue(company._enrich())

        self.assertRecordValues(company.partner_id | contact, [{'industry_id': industry.id}] * 2)

    def test_enrich_by_duns_vat_from_query(self):
        """Ensure the VAT number is taken from the query when the company was found from it."""
        for country_code, query, expected_vat in (
            ('BE', 'BE0477472701', 'BE0477472701'),
            ('BE', 'NotOdoo 2024', None),
            ('US', '94-2404110', None),  # there is no validation for US TIN
        ):
            # The suggestion found from the query, which the enrichment completes without VAT number
            company_data = {'name': 'Test Company', 'duns': '123456789', 'country_code': country_code}
            suggestion = self.env['res.partner']._format_data_company({**company_data, 'query': query})
            with (
                self.subTest(query=query),
                patch(
                    'odoo.addons.partner_autocomplete.models.iap_autocomplete_api.IapAutocompleteApi._contact_iap',
                    return_value={'data': company_data},
                ),
            ):
                result = self.env['res.partner'].enrich_by_duns('123456789', company_data=suggestion)
                self.assertEqual(result.get('vat'), expected_vat)

    def test_autocomplete_by_field_name_like_vat(self):
        """Ensure a name that looks like a VAT number is searched both as a VAT number and as a name."""
        def contact_iap(local_endpoint, action, params, timeout=15):
            return {'data': [{'name': f"{action}: {params['query']}"}]}

        for query, expected_names in (
            ('Odoo', ['search_by_name: Odoo']),
            ('BE0477472701', ['search_by_vat: BE0477472701', 'search_by_name: BE0477472701']),
            ('Odoo 2024', ['search_by_name: Odoo 2024']),  # not a Belgian VAT number
        ):
            with (
                self.subTest(query=query),
                patch(
                    'odoo.addons.partner_autocomplete.models.iap_autocomplete_api.IapAutocompleteApi._contact_iap',
                    side_effect=contact_iap,
                ),
            ):
                suggestions = self.env['res.partner'].autocomplete_by_field('name', query, self.base_be.id)
                self.assertEqual([suggestion['name'] for suggestion in suggestions], expected_names)

    def test_autocomplete_by_vat_vies(self):
        """Ensure VIES is only checked for the VAT numbers of the EU, when IAP does not find the company."""
        for country, vat, expected_vies_vat in (
            (self.base_be, '0477472701', 'BE0477472701'),
            (self.env.ref('base.us'), '94-2404110', None),
        ):
            with (
                self.subTest(vat=vat),
                patch(
                    'odoo.addons.partner_autocomplete.models.iap_autocomplete_api.IapAutocompleteApi._contact_iap',
                    return_value={'error': 'Not found'},
                ),
                patch(
                    'odoo.addons.partner_autocomplete.models.res_partner.check_vies',
                    return_value={'valid': True, 'name': 'Odoo', 'address': 'Rue de Ramillies 1\n1367 Ramillies', 'countryCode': 'BE'},
                ) as check_vies_mock,
            ):
                suggestions = self.env['res.partner'].autocomplete_by_vat(vat, country.id)
                if expected_vies_vat:
                    check_vies_mock.assert_called_once_with(expected_vies_vat, timeout=15)
                    self.assertEqual([suggestion['vat'] for suggestion in suggestions], [expected_vies_vat])
                else:
                    check_vies_mock.assert_not_called()
                    self.assertFalse(suggestions)
