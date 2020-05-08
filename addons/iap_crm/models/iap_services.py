# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.iap.tools import iap_tools


class IapServices(models.AbstractModel):
    _inherit = 'iap.services'

    # ------------------------------------------------------------
    # LEAD MINING
    # ------------------------------------------------------------

    @api.model
    def _iap_get_endpoint_netloc(self, account_name):
        if account_name == 'reveal':
            return self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', 'https://iap-services.odoo.com')
        return super(IapServices, self)._iap_get_endpoint_netloc(account_name)

    @api.model
    def _iap_get_service_account_match(self, service_name):
        if service_name in('reveal', 'lead_mining_request', 'lead_enrichment_email'):
            return 'reveal'
        return super(IapServices, self)._iap_get_service_account_match(service_name)

    @api.model
    def _iap_get_service_url_scheme(self, service_name):
        if service_name == 'lead_mining_request':
            return 'iap/clearbit/1/lead_mining_request'
        if service_name == 'lead_enrichment_email':
            return 'iap/clearbit/1/lead_enrichment_email'
        if service_name == 'reveal':
            return 'iap/clearbit/1/reveal'
        return super(IapServices, self)._iap_get_service_url_scheme(service_name)

    @api.model
    def _iap_request_enrich(self, domains):
        """ Contact endpoint to get enrichment data.

        :param lead_emails: dict{lead_id: email}
        :return: dict{lead_id: company data or False}
        :raise: several errors, notably
          * InsufficientCreditError: {
            "credit": 4.0,
            "service_name": "reveal",
            "base_url": "https://iap.odoo.com/iap/1/credit",
            "message": "You don't have enough credits on your account to use this service."
            }
        """
        reveal_account = self.env['iap.services']._iap_get_service_account('lead_enrichment_email')
        params = {
            'account_token': reveal_account.account_token,
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'domains': domains
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('lead_enrichment_email'), params=params, timeout=300)

    @api.model
    def _iap_request_lead_mining(self, payload):
        reveal_account = self.env['iap.services']._iap_get_service_account('lead_mining_request')
        params = {
            'account_token': reveal_account.account_token,
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'data': payload
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('lead_mining_request'), params=params, timeout=300)

    @api.model
    def _iap_request_reveal(self, payload):
        reveal_account = self.env['iap.services']._iap_get_service_account('reveal')
        params = {
            'account_token': reveal_account.account_token,
            'data': payload
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('reveal'), params=params, timeout=300)

    # ------------------------------------------------------------
    # CRM HELPERS AND TOOLS
    # ------------------------------------------------------------

    @api.model
    def _iap_get_lead_vals_from_clearbit_data(self, company_data, people_data, **additional_values):
        country_id = self.env['res.country'].search([('code', '=', company_data['country_code'])]).id
        state = self.env['res.country.state'].search([('code', '=', company_data['state_code']), ('country_id', '=', country_id)])
        state_id = state.id if state else False
        website_url = 'https://www.%s' % company_data['domain'] if company_data['domain'] else False
        lead_values = {
            'reveal_id': company_data['clearbit_id'],
            'name': company_data['name'] or company_data['domain'],
            'partner_name': company_data['legal_name'] or company_data['name'],
            'email_from': next(iter(company_data.get('email', [])), ''),
            'phone': company_data['phone'] or (company_data['phone_numbers'] and company_data['phone_numbers'][0]) or '',
            'website': website_url,
            'street': company_data['location'],
            'city': company_data['city'],
            'zip': company_data['postal_code'],
            'country_id': country_id,
            'state_id': state_id,
        }

        # If type is people then add first contact in lead data
        if people_data:
            lead_values.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['title'],
            })

        if additional_values:
            lead_values.udpate(**additional_values)
        return lead_values
