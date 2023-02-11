# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.iap.tools import iap_tools
from odoo.addons.partner_autocomplete.models.iap_autocomplete_api import IapAutocompleteEnrichAPI
from odoo.tests import common


class MockIAPPartnerAutocomplete(common.BaseCase):
    """ Mock PartnerAutocomplete IAP calls for testing purpose.

    Example of company_data {
      'partner_gid': 51580, 'website': 'mywebsite.be',
      'additional_info': {
        "name": "Mywebsite",
        "description": "Mywebsite is the largest of Belgium\'s custom companies and part of Mywebsite Group.",
        "facebook": "mywebsitebe", "twitter": "mywebsite", "linkedin": "company/mywebsite",
        "twitter_followers": 99999, "twitter_bio": "This is the official Twitter account of MyWebsite.",
        "industry_group": "Technology Hardware & Equipment", "sub_industry": "Computer Networking",
        "industry": "Communications Equipment",
        "sector": ["Information Technology", "Technology Hardware & Equipment"],
        "sector_primary": "Information Technology"
        "tech": ["Tealium", "Hotjar", "Google Analytics", "Instagram", "Facebook Advertiser", "Facebook Connect", "Google Tag Manager", "Mandrill", "Bazaarvoice", "Mailgun", "Conversio"],
        "email": [], "crunchbase": "organization/mywebsite-group",
        "phone_numbers": ["+32 800 00 000", "+32 800 00 001", "+32 800 00 002"],
        "timezone": "Europe/Brussels", "timezone_url": "https://time.is/Brussels",
        "company_type": "private", "employees": 15000.0, "annual_revenue": 0.0, "estimated_annual_revenue": false, "founded_year": 0,
        "logo": "https://logo.clearbit.com/mywebsite.be"},
      'child_ids': [{
        'is_company': False, 'type': 'contact', 'city': False, 'email': False,
        'name': 'Client support - SMEs', 'street': 'False False', 'phone': '0800 00 500',
        'zip': False, 'country_id': False, 'state_id': False}, {
        'is_company': False, 'type': 'contact', 'city': False, 'email': False,
        'name': 'Client Support - Large Business', 'street': 'False False', 'phone': '0800 00 501',
        'zip': False, 'country_id': False, 'state_id': False}],
      'city': 'Brussel', 'vat': 'BE0202239951',
      'email': False, 'logo': 'https://logo.clearbit.com/mywebsite.be',
      'name': 'Proximus', 'zip': '1000', 'ignored': False, 'phone': '+32 800 00 800',
      'bank_ids': [{
        'acc_number': 'BE012012012', 'acc_holder_name': 'MyWebsite'}, {
        'acc_number': 'BE013013013', 'acc_holder_name': 'MyWebsite Online'}],
      'street': 'Rue Perdues 27',
      'country_code': 'de', 'country_name': 'Germany',
      'state_id': False
    }
    """

    @classmethod
    def _init_mock_partner_autocomplete(cls):
        cls.base_de = cls.env.ref('base.de')
        cls.base_be = cls.env.ref('base.be')
        cls.be_state_bw = cls.env['res.country.state'].create({'name': 'Béwééé dis', 'code': 'bw', 'country_id': cls.base_be.id})

    @contextmanager
    def mockPartnerAutocomplete(self, default_data=None, sim_error=None):
        def _contact_iap(local_endpoint, action, params, timeout):
            sim_result = {
                'partner_gid': '9876', 'website': 'https://www.heinrich.de',
                'additional_info': {},
                'city': 'Mönchengladbach',
                'email': False, 'logo': 'https://logo.clearbit.com/heinrichsroofing.com',
                'name': 'Heinrich', 'zip': '41179', 'ignored': False, 'phone': '+49 0000 112233',
                'street': 'Mennrather Str. 123456',
                'country_code': self.base_de.code, 'country_name': self.base_de.name,
                'state_id': False,
                'child_ids': [{
                    'is_company': False, 'type': 'contact', 'city': 'Orcq',
                    'name': 'Heinrich Support'
                }, {
                    'is_company': False, 'type': 'contact', 'email': 'heinrich.clien@test.example.com',
                    'name': 'Heinrich Client Support', 'street': 'Rue des Bourlottes, 9', 'phone': '0456 00 11 22',
                    'zip': '1367', 'country_code': self.base_be.code, 'country_name': self.base_be.name,
                    'state_code': self.be_state_bw.code, 'state_name': self.be_state_bw.name
                }],
            }
            if default_data:
                sim_result.update(default_data)
            # mock enrich only currently, to update further
            if action == 'enrich':
                if sim_error and sim_error == 'credit':
                    raise iap_tools.InsufficientCreditError('InsufficientCreditError')
                elif sim_error and sim_error == 'jsonrpc_exception':
                    raise exceptions.AccessError(
                        'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + local_endpoint
                    )
                elif sim_error and sim_error == 'token':
                    raise ValueError('No account token')
                return {'company_data': sim_result}

        try:
            with patch.object(IapAutocompleteEnrichAPI, '_contact_iap', side_effect=_contact_iap):
                yield
        finally:
            pass
