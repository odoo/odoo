# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import requests

from odoo import models, api
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class IapEnrichAPI(models.AbstractModel):
    _name = 'iap.enrich.api'
    _description = 'IAP Lead Enrichment API'
    _DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'

    @api.model
    def _contact_iap(self, local_endpoint, params):
        account = self.env['iap.account'].get('reveal')
        params['account_token'] = account.account_token
        params['dbuuid'] = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        base_url = self.env['ir.config_parameter'].sudo().get_param('enrich.endpoint', self._DEFAULT_ENDPOINT)
        return iap_tools.iap_jsonrpc(base_url + local_endpoint, params=params, timeout=30)

    @api.model
    def _request_enrich(self, domains):
        """ Contact endpoint to get enrichment data.

        :param domains: dict{key: domain} where key can be whatever caller wants
          and will be used to organize returned data;

        :return: dict{key: company data or False};

        :raise: InsufficientCreditError: {
            "credit": 4.0,
            "service_name": "reveal",
            "base_url": "https://iap.odoo.com/iap/1/credit",
            "message": "You don't have enough credits on your account to use this service."
          }
        """
        return self._contact_iap('/iap/clearbit/1/lead_enrichment_email', params={
            'domains': domains,
        })

    @api.model
    def _get_contact_vals_from_response(self, iap_payload, include_logo=False):
        """ Get contact values from iap payload after performing a call to
        enrich API. This notably computed country, state, email and phone
        as well as controllable image update. """
        country = self.env['res.country'].search([('code', '=', iap_payload['country_code'])])
        emails = iter(iap_payload['email'] or [])
        phones = iter(iap_payload['phone_numbers'] or [])

        contact_vals = {
            'city': iap_payload['city'],
            'country_id': country.id,
            'email_from': next(emails, ''),
            'name': iap_payload['name'] or iap_payload['domain'],
            'phone': next(phones, ''),
            'reveal_id': iap_payload['clearbit_id'],
            'state_id': self._find_state(iap_payload['state_code'], country).id,
            'street': iap_payload['location'],
            'website': 'https://www.%s' % iap_payload['domain'] if iap_payload['domain'] else False,
            'zip': iap_payload['postal_code'],
        }
        contact_vals['mobile'] = next(phones, '')

        logo_url = iap_payload['logo']
        if logo_url and include_logo:
            contact_vals['image_1920'] = False
            try:
                response = requests.get(logo_url, timeout=2)
                if response.ok:
                    contact_vals['image_1920'] = base64.b64encode(response.content)
            except Exception as e:
                _logger.warning('Download of image for contact or company %s failed, error %s', contact_vals['name'], e)

        return contact_vals

    @api.model
    def _find_state(self, state_code, country):
        return self.env['res.country.state'].search([
            ('code', '=', state_code),
            ('country_id', '=', country.id)
        ])
