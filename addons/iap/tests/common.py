# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.iap.tools import iap_tools
from odoo.addons.iap.models.iap_autocomplete_api import IapAutocompleteEnrichAPI
from odoo.addons.iap.models.iap_enrich_api import IapEnrichAPI
from odoo.tests import common


class MockIAPEnrich(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(MockIAPEnrich, cls).setUpClass()
        cls._init_iap_mock()

    @contextmanager
    def mockIAPEnrichGateway(self, name_list=None, default_data=None, email_data=None, sim_error=None):

        def _contact_iap(local_endpoint, params):
            self.assertEqual(local_endpoint, '/iap/clearbit/1/lead_enrichment_email')

            response = {}
            for counter, (lead_id, email) in enumerate(params['domains'].items()):
                if sim_error and sim_error == 'credit':
                    raise iap_tools.InsufficientCreditError('InsufficientCreditError')
                if sim_error and sim_error == 'jsonrpc_exception':
                    raise exceptions.AccessError(
                        'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + local_endpoint
                    )

                if name_list:
                    base_name = name_list[counter % len(name_list)]
                else:
                    base_name = 'heinrich_%d' % counter
                iap_payload = self._get_iap_company_data(base_name, service='enrich')
                if default_data:
                    iap_payload.update(default_data)
                if email_data and email in email_data:
                    if email_data[email] is False:
                        iap_payload = False
                    else:
                        iap_payload.update(email_data[email])
                response[str(lead_id)] = dict(iap_payload)

            return response

        with patch.object(IapEnrichAPI, '_contact_iap', side_effect=_contact_iap) as _contact_iap_mock:
            self._contact_iap_mock = _contact_iap_mock
            yield

    @classmethod
    def _init_iap_mock(cls):
        cls.base_de = cls.env.ref('base.de')
        cls.de_state_st = cls.env['res.country.state'].create({
            'name': 'DE ST State',
            'code': 'st',
            'country_id': cls.base_de.id
        })
        cls.base_be = cls.env.ref('base.be')
        cls.be_state_bw = cls.env['res.country.state'].create({
            'name': 'Béwééé dis',
            'code': 'bw',
            'country_id': cls.base_be.id
        })

    def _get_iap_company_data(self, base_name, service=None, add_values=None):
        return {
            'domain': '%s.de' % base_name,
            'clearbit_id': '123_ClearbitID_%s' % base_name,

            # Company Info
            'name': '%s GmbH' % base_name,
            'legal_name': '%s GmbH legal_name' % base_name,
            'description': '%s GmbH description' % base_name,
            'founded_year': '1930',
            'logo': 'https://logo.clearbit.com/%slogo.com' % base_name,
            'company_type': 'private',

            # Contacts
            'phone_numbers': ['+4930499193937', '+4930653376208'],
            'email': [
                'info@%s.example.com' % base_name,
                'info2@%s.example.com' % base_name
            ],

            # Timezone
            'timezone': 'Europe/Berlin',
            'timezone_url': 'https://time.is/Berlin',

            # Social
            'facebook': "%s Facebook Handle" % base_name,
            'linkedin': "%s Linkedin Handle" % base_name,
            'crunchbase': "organization/%s" % base_name,

            # Twitter
            'twitter': '%s Twitter Handle' % base_name,
            'twitter_bio': '%s Twitter Bio' % base_name,
            'twitter_followers': 1250,
            'twitter_location': 'Berlin',

            # Metrics
            'estimated_annual_revenue': '1000000',
            'employees': 3.14,
            'market_cap': 6.28,
            'raised': 15000,
            'annual_revenue': 1000000,

            # Category
            'sector': '%s sector' % base_name,
            'sector_primary': '%s sector_primary' % base_name,
            'industry': '%s industry' % base_name,
            'industry_group': '%s industry_group' % base_name,
            'sub_industry': '%s sub_industry' % base_name,
            'tag': ['Automation', 'Construction'],
            'tech': ['3d_cart', 'nginx'],

            # Site
            'website_title': '%s Website Title' % base_name,

            # GEO Data
            'location': 'Mennrather Str. 123456',
            'street_number': '123456',
            'street_name': 'Mennrather Str.',
            'sub_premise': 'sub premise',
            'postal_code': '41179',
            'city': 'Mönchengladbach',
            'state_code': self.de_state_st.code,
            'state_name': self.de_state_st.name,
            'country_code': self.base_de.code,
            'country_name': self.base_de.name,
        }

    def _get_iap_contact_data(self, base_name, service=None, add_values=None):
        people_data = []
        for index in range(2):
            payload = {
                'full_name': 'Contact %s %s' % (base_name, index),
                'email': 'test.contact.%s@%s.example.com' % (index, base_name),
                'phone': '+49 30 548406496',
                'seniority': 'manager',
                'title': 'Doing stuff',
                'role': 'health_professional',
            }
            people_data.append(payload)
        return people_data

    @contextmanager
    def mockPartnerAutocomplete(self, name_list=None, default_data=None, sim_error=None):
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
        def _contact_iap(local_endpoint, action, params, timeout):
            self.assertEqual(action, "enrich")

            if sim_error and sim_error == 'credit':
                return {
                    'company_data': False,
                    'credit_error': True,
                    'request_code': 200,
                    'total_cost': 0,
                }
            if sim_error and sim_error == 'jsonrpc_exception':
                raise exceptions.AccessError(
                    'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + local_endpoint
                )
            if sim_error and sim_error == 'token':
                raise ValueError('No account token')

            if name_list:
                base_name = name_list[0]
            else:
                base_name = 'heinrich'
            iap_payload = self._get_iap_company_data_autocomplete(base_name, service='enrich')
            if default_data:
                iap_payload.update(default_data)

            return {
                'company_data': iap_payload,
                'credit_error': False,
                'request_code': 200,
                'total_cost': 1,
            }

        with patch.object(IapAutocompleteEnrichAPI, '_contact_iap', side_effect=_contact_iap) as _contact_iap_mock:
            self._contact_iap_mock = _contact_iap_mock
            yield

    def _get_iap_company_data_autocomplete(self, base_name, service=None, add_values=None):
        base_info = {
            # Autocomplete info
            'partner_gid': '9876',
            'website': '%s.de' % base_name,
            'ignored': '',

            # Vat
            'vat': '',

            # Company Info
            'name': '%s GmbH' % base_name,
            'logo': 'https://logo.clearbit.com/%slogo.com' % base_name,
        }
        if service == 'search':
            return base_info

        iap_payload = dict(base_info, **{
            # Contacts
            'phone': '+4930499193937',
            'email': 'info@%s.example.com' % base_name,

            # GEO Data
            'street': 'Mennrather Str. 123456',
            'zip': '41179',
            'city': 'Mönchengladbach',
            'state_code': self.de_state_st.code,
            'state_name': self.de_state_st.name,
            'country_code': self.base_de.code,
            'country_name': self.base_de.name,

            # Children
            'child_ids': self._get_iap_contact_data_autocomplete(
                base_name, service=service, add_values=add_values
            ),

            # Bank accounts,
            'bank_ids': [
                {'acc_number': 'BE012012012',
                 'acc_holder_name': 'MyWebsite'},
                {'acc_number': 'BE012012024',
                 'acc_holder_name': 'MyWebsite Online'}
            ],

            # Infamous additional information
            'additional_info': {
                # Company Info
                'name': '%s GmbH' % base_name,
                'description': '%s GmbH description' % base_name,
                'founded_year': '1930',
                'logo': 'https://logo.clearbit.com/%slogo.com' % base_name,
                'company_type': 'private',

                # Contacts
                'phone_numbers': ['+4930499193937', '+4930653376208'],
                'emails': [
                    'info@%s.example.com' % base_name,
                    'info2@%s.example.com' % base_name
                ],

                # Timezone
                'timezone': 'Europe/Berlin',
                'timezone_url': 'https://time.is/Berlin',

                # Social
                'facebook': "%s Facebook Handle" % base_name,
                'linkedin': "%s Linkedin Handle" % base_name,
                'crunchbase': "organization/%s" % base_name,

                # Twitter
                'twitter': '%s Twitter Handle' % base_name,
                'twitter_bio': '%s Twitter Bio' % base_name,
                'twitter_followers': 1250,

                # Metrics
                'estimated_annual_revenue': '1000000',
                'employees': 3.14,
                'annual_revenue': 1000000,

                # Category
                'sector': ['%s sector' % base_name],
                'sector_primary': '%s sector_primary' % base_name,
                'industry': '%s industry' % base_name,
                'industry_group': '%s industry_group' % base_name,
                'sub_industry': '%s sub_industry' % base_name,
                'tech': ['3d_cart', 'nginx'],
            }
        })
        return iap_payload

    def _get_iap_contact_data_autocomplete(self, base_name, service=None, add_values=None):
        people_data = []
        for index in range(2):
            payload = {
                'city': 'Mönchengladbach',
                'country_code': self.base_de.code,
                'country_name': self.base_de.name,
                'email': 'test.contact.%s@%s.example.com' % (index, base_name),
                'is_company': '',
                'name': 'Contact %s %s' % (base_name, index),
                'phone': '+49 30 548406496',
                'state_code': self.de_state_st.code,
                'state_name': self.de_state_st.name,
                'street': 'Mennrather Str. 123456',
                'type': 'contact',
                'zip': '41179',
            }
            people_data.append(payload)
        return people_data