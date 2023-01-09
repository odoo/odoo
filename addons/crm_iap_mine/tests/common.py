# -*- coding: utf-8 -*-

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.crm.models.crm_lead import Lead
from odoo.addons.crm_iap_mine.models.crm_iap_lead_mining_request import CRMLeadMiningRequest
from odoo.addons.iap.tests.common import MockIAPEnrich
from odoo.addons.iap.tools import iap_tools


class MockIAPReveal(MockIAPEnrich):

    @classmethod
    def setUpClass(cls):
        super(MockIAPReveal, cls).setUpClass()
        cls._new_leads = cls.env['crm.lead'].sudo()
        cls.mine = False

    @contextmanager
    def mock_IAP_mine(self, mine, name_list=None, default_data=None, sim_error=None):
        self._new_leads = self.env['crm.lead'].sudo()
        self.mine = mine
        crm_lead_create_origin = Lead.create

        def _crm_lead_create(model, *args, **kwargs):
            res = crm_lead_create_origin(model, *args, **kwargs)
            self._new_leads += res.sudo()
            return res

        def _iap_contact_mining(params, timeout):
            self.assertMineCallParams(params)
            self.assertMinePayload(mine, params['data'])

            if sim_error and sim_error == 'credit':
                raise iap_tools.InsufficientCreditError('InsufficientCreditError')
            if sim_error and sim_error == 'jsonrpc_exception':
                raise exceptions.AccessError(
                    'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was [STRIPPED]'
                )
            if sim_error and sim_error == 'no_result':
                return {'credit_error': False, 'data': []}

            response = []
            for counter in range(0, mine.lead_number):
                if name_list:
                    base_name = name_list[counter % len(name_list)]
                else:
                    base_name = 'heinrich_%d' % counter

                iap_payload = {}
                company_data = self._get_iap_company_data(base_name, service='mine')
                if default_data:
                    company_data.update(default_data)
                iap_payload['company_data'] = company_data

                if mine.search_type == 'people':
                    people_data = self._get_iap_contact_data(base_name, service='mine')
                    iap_payload['people_data'] = people_data

                response.append(iap_payload)

            return {
                'data': response,
                'credit_error': False
            }

        with patch.object(CRMLeadMiningRequest, '_iap_contact_mining', side_effect=_iap_contact_mining), \
             patch.object(Lead, 'create', autospec=True, wraps=Lead, side_effect=_crm_lead_create):
            yield

    def _get_iap_company_data(self, base_name, service=None, add_values=None):
        company_data = super(MockIAPReveal, self)._get_iap_company_data(base_name, service=service, add_values=add_values)
        if service == 'mine':
            company_data['phone'] = company_data['phone_numbers'][0]
            company_data['sector'] = 'Sector Info'
        return company_data

    def assertMineCallParams(self, params):
        self.assertTrue(bool(params['account_token']))
        self.assertTrue(bool(params['dbuuid']))

    def assertMinePayload(self, mine, payload):
        if mine.search_type == 'people':
            self.assertEqual(payload['contact_number'], mine.contact_number)
        else:
            self.assertTrue('contact_number' not in payload)
        self.assertEqual(payload['countries'], mine.mapped('country_ids.code'))
        self.assertEqual(payload['lead_number'], mine.lead_number)
        self.assertEqual(payload['search_type'], mine.search_type)
