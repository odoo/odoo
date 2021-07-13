# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons.iap.tools import iap_tools


class IapRevealAPI(models.AbstractModel):
    _name = 'iap.reveal.api'
    _description = 'IAP Lead Mining/Reveal API'
    _DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'

    @api.model
    def _contact_iap(self, local_endpoint, params):
        account = self.env['iap.account'].get('reveal')
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        params['account_token'] = account.account_token
        params['dbuuid'] = dbuuid
        base_url = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', self._DEFAULT_ENDPOINT)
        return iap_tools.iap_jsonrpc(base_url + local_endpoint, params=params, timeout=300)

    @api.model
    def _request_mine(self, payload):
        """ Contact endpoint to get mining data.

        :param payload: {
            'lead_number': the number of leads to generate
            'search_type': 'people' or 'companies' to indicate if we're looking only for companies or also contacts
            'countries': the list of country codes
            'company_size_min': the minimum size of the company (optional)
            'company_size_max': the maximum size of the company (optional)
            'technology_tags': Clearbit's technology tags (optional)
            'industry_ids': Clearbit's industry (optional)
            # following fields are present only if 'search_type' = 'people'
            'contact_number': the number of contacts to look for, for each company
            'contact_filter_type': 'role' or 'seniority'
            'preferred_role': main role to look for (if 'contact_filter_type' = 'role')
            'other_roles': other roles to look for (if 'contact_filter_type' = 'role', optional)
            'seniority': the seniority (if 'contact_filter_type' = 'seniority')
          }
        :return: {
            'credit_error': bool,  -> always False actually
            'data': a list containing the data of each company and their contacts (if 'search_type' = 'people')
            [{
                'company_data': the data of the company,
                'people_data': the data of the contacts of the company
            }]
          }
        :raise: InsufficientCreditError
        """
        params = {
            'data': payload,
        }
        return self._contact_iap('/iap/clearbit/1/lead_mining_request', params=params)

    @api.model
    def _request_reveal(self, payload):
        """ Contact endpoint to get enrichment data.

        :param payload: {
            ips: {
                <visitor_ip>: [list of rule ids],
            },
            rules: {
                1: {rule_data},
                2: {rule_data},
                3: {rule_data},
                4: {rule_data},
            }
          } where rule_data = {
            'rule_id'
            'lead_for': 'people' or 'companies'
            'countries': list of country codes
            'filter_on_size': boolean
            'company_size_min'
            'company_size_max'
            'industry_tags': list of tag_ids
            'user_country': country_code of the user
            'contact_filter_type': 'role' or 'seniority'
            'preferred_role'
            'other_roles'
            'seniority'
          }

        :return: {
            'credit_error': bool,  # True if user credit is over
            'reveal_data': [{
                    lead_data
                }, {
                    'not_found': True, ## Send if data is not found in reveal
                    'ip': ip
                }]
          }
        :raise: Nope (InsufficientCreditError -> credit_error = True)
        """
        params = {
            'data': payload,
        }
        return self._contact_iap('/iap/clearbit/1/reveal', params=params)

    @api.model
    def _get_lead_vals_from_response(self, iap_response_data):
        company_data = iap_response_data['company_data']
        country = self.env['res.country'].search([('code', '=', company_data['country_code'])])
        emails = iter(company_data['email'] or [])
        phones = iter(company_data['phone_numbers'] or [])

        lead_vals = {
            'city': company_data['city'],
            'country_id': country.id,
            'email_from': next(emails, ''),
            'name': company_data['name'] or company_data['domain'],
            'partner_name': company_data['legal_name'] or company_data['name'],
            'phone': next(phones, ''),
            'reveal_id': company_data['clearbit_id'],
            'state_id': self.env['iap.enrich.api']._find_state(company_data['state_code'], country).id,
            'street': company_data['location'],
            'website': 'https://www.%s' % company_data['domain'] if company_data['domain'] else False,
            'zip': company_data['postal_code'],
        }

        # If type is people then add first contact in lead data
        people_data = iap_response_data.get('people_data')
        if people_data:
            lead_vals.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['title'],
            })
        return lead_vals
