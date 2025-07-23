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
                response.append(company_data)

            return {
                'data': response,
                'credit_error': False
            }

        with patch.object(CRMLeadMiningRequest, '_iap_contact_mining', side_effect=_iap_contact_mining), \
             patch.object(Lead, 'create', autospec=True, wraps=Lead, side_effect=_crm_lead_create):
            yield

    def _get_iap_company_data(self, base_name, service=None, add_values=None):
        company_data = super()._get_iap_dnb_company_data(base_name, service=service, add_values=add_values)
        return company_data

    def assertMineCallParams(self, params):
        self.assertTrue(bool(params['account_token']))
        self.assertTrue(bool(params['db_uuid']))
