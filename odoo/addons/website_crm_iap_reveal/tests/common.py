# -*- coding: utf-8 -*-

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.crm.models.crm_lead import Lead
from odoo.addons.iap.tests.common import MockIAPEnrich
from odoo.addons.website_crm_iap_reveal.models.crm_reveal_rule import CRMRevealRule


class MockIAPReveal(MockIAPEnrich):

    @classmethod
    def setUpClass(cls):
        super(MockIAPReveal, cls).setUpClass()
        cls._new_leads = cls.env['crm.lead'].sudo()
        cls.rules = False
        cls.views = False

    @contextmanager
    def mock_IAP_reveal(self, ip_to_rules, name_list=None, default_data=None, sim_error=None):
        self._new_leads = self.env['crm.lead'].sudo()
        crm_lead_create_origin = Lead.create

        def _crm_lead_create(model, *args, **kwargs):
            res = crm_lead_create_origin(model, *args, **kwargs)
            self._new_leads += res.sudo()
            return res

        def _iap_contact_reveal(params, timeout):
            if sim_error and sim_error == 'credit':
                return {'credit_error': True, 'reveal_data': []}
            if sim_error and sim_error == 'jsonrpc_exception':
                raise exceptions.AccessError(
                    'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was [STRIPPED]'
                )
            if sim_error and sim_error == 'no_result':
                return {'credit_error': False, 'reveal_data': []}

            response = []
            for counter, ip_values in enumerate(ip_to_rules):
                ip, rule = ip_values['ip'], ip_values['rules']
                if name_list:
                    base_name = name_list[counter % len(name_list)]
                else:
                    base_name = 'heinrich_%d' % counter

                iap_payload = {
                    'ip': ip,
                    'ip_time_zone': 'Europe/Berlin',
                    'not_found': False,
                    'rule_id': rule.id,
                }
                company_data = self._get_iap_company_data(base_name, service='reveal', add_values={'ip': ip, 'rule': rule})
                if default_data:
                    company_data.update(default_data)
                iap_payload['clearbit_id'] = company_data['clearbit_id']
                iap_payload['reveal_data'] = company_data

                if rule.lead_for == 'people':
                    people_data = self._get_iap_contact_data(base_name, service='reveal')
                    iap_payload['people_data'] = people_data

                iap_payload['credit'] = 1 + (len(people_data) if rule.lead_for == 'people' else 0)

                response.append(iap_payload)

            return {
                'reveal_data': response,
                'credit_error': False
            }

        with patch.object(CRMRevealRule, '_iap_contact_reveal', side_effect=_iap_contact_reveal), \
             patch.object(Lead, 'create', autospec=True, wraps=Lead, side_effect=_crm_lead_create):
            yield

    def _get_iap_company_data(self, base_name, service=None, add_values=None):
        company_data = super(MockIAPReveal, self)._get_iap_company_data(base_name, service=service, add_values=add_values)
        if service == 'reveal':
            company_data['phone'] = company_data['phone_numbers'][0]
            company_data['sector'] = 'Sector Info'
        return company_data
