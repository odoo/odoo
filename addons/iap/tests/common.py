# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.iap.tools import iap_tools
from odoo.addons.iap.models.iap_enrich_api import IapEnrichAPI
from odoo.tests import common


class MockIAPEnrich(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(MockIAPEnrich, cls).setUpClass()
        cls._init_iap_mock()

    @contextmanager
    def mockIAPEnrichGateway(self, default_data=None, email_data=None, sim_error=None, failing_emails=None):

        def _contact_iap(local_endpoint, params):
            sim_result = {
                'name': 'Simulator INC',
                'location': 'Simulator Street',
                'city': 'SimCity',
                'postal_code': '9876',
                'country_code': 'BE',
                'clearbit_id': 'idontknow',
                'phone_numbers': ['+3269001122', '+32456001122'],
                'twitter': 'testtwitter',
                'facebook': 'testfacebook',
            }
            if default_data:
                sim_result.update(default_data)
            # mock single sms sending
            if local_endpoint == '/iap/clearbit/1/lead_enrichment_email':
                result = {}
                for lead_id, email in params['domains'].items():
                    if sim_error and sim_error == 'credit':
                        raise iap_tools.InsufficientCreditError('InsufficientCreditError')
                    elif sim_error and sim_error == 'jsonrpc_exception':
                        raise exceptions.AccessError(
                            'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + local_endpoint
                        )
                    result[str(lead_id)] = dict(sim_result)
                    if email_data and email_data.get(email):
                        result[str(lead_id)].update(email_data[email])
                return result

        try:
            with patch.object(IapEnrichAPI, '_contact_iap', side_effect=_contact_iap) as contact_iap_mock:
                yield
        finally:
            pass

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
