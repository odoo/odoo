# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.iap.tools import iap_tools
from odoo.addons.partner_autocomplete.models.iap_autocomplete_api import IapAutocompleteApi
from odoo.tests import common


class MockIAPPartnerAutocomplete(common.BaseCase):
    """ Mock PartnerAutocomplete IAP calls for testing purpose.

    Example of company_data {
      'website': 'mywebsite.be',
      'city': 'Brussel',
      'vat': 'BE0202239951',
      'email': False,
      'logo': 'https://logo.clearbit.com/mywebsite.be',
      'name': 'Proximus',
      'zip': '1000',
      'phone': '+32 800 00 800',
      'street': 'Rue Perdues 27',
      'country_code': 'de',
      'country_name': 'Germany',
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
                'website': 'https://www.heinrich.de',
                'city': 'Mönchengladbach',
                'email': False,
                'logo': 'https://logo.clearbit.com/heinrichsroofing.com',
                'name': 'Heinrich',
                'zip': '41179',
                'phone': '+49 0000 112233',
                'street': 'Mennrather Str. 123456',
                'country_code': self.base_de.code,
                'country_name': self.base_de.name,
                'state_id': False,
            }
            if default_data:
                sim_result.update(default_data)
            # mock enrich only currently, to update further
            if action == 'enrich_by_domain':
                if sim_error and sim_error == 'credit':
                    raise iap_tools.InsufficientCreditError('InsufficientCreditError')
                elif sim_error and sim_error == 'jsonrpc_exception':
                    raise exceptions.AccessError(
                        'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + local_endpoint
                    )
                elif sim_error and sim_error == 'token':
                    raise ValueError('No account token')
                return {'data': sim_result}

        with patch.object(IapAutocompleteApi, '_contact_iap', side_effect=_contact_iap):
            yield
