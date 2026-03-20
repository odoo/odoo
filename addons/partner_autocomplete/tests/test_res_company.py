from unittest.mock import patch
from odoo.tests import common, tagged
from odoo.addons.partner_autocomplete.tests.common import MockIAPPartnerAutocomplete


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
        company_1 = self.env['res.company'].create({'name': "Test Company 1"})

        company_1.website = 'http://www.info.proximus.be/faq/test'
        self.assertEqual(company_1._get_company_domain(), "proximus.be")

        company_1.email = 'info@waterlink.be'
        self.assertEqual(company_1._get_company_domain(), "waterlink.be")

        company_1.website = False
        company_1.email = False
        self.assertEqual(company_1._get_company_domain(), False)

        company_1.email = "at@"
        self.assertEqual(company_1._get_company_domain(), False)

        company_1.website = "http://superFalsyWebsiteName"
        self.assertEqual(company_1._get_company_domain(), False)

        company_1.website = "http://www.superwebsite.com"
        self.assertEqual(company_1._get_company_domain(), 'superwebsite.com')

        company_1.website = "http://superwebsite.com"
        self.assertEqual(company_1._get_company_domain(), 'superwebsite.com')

        company_1.website = "http://localhost:8069/%7Eguido/Python.html"
        self.assertEqual(company_1._get_company_domain(), False)

        company_1.website = "http://runbot.odoo.com"
        self.assertEqual(company_1._get_company_domain(), 'odoo.com')

        company_1.website = "http://www.example.com/biniou"
        self.assertEqual(company_1._get_company_domain(), False)

        company_1.website = "http://www.cwi.nl:80/%7Eguido/Python.html"
        self.assertEqual(company_1._get_company_domain(), "cwi.nl")

    def test_enrich_by_duns_with_incorrect_vat(self):
        """
        Ensure the VAT number is removed when the partner autocomplete return an incorrect VAT number
        """
        if self.env['ir.module.module']._get('base_vat').state != 'installed':
            self.skipTest("The module base vat is required to run this test.")

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
            result = self.env['res.partner'].with_context(enriched_company_data=be_company_data).enrich_by_duns('BE1234567')
            self.assertEqual(result.get('vat'), '')
