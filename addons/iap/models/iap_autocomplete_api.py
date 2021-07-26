# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests

from requests.exceptions import HTTPError

from odoo import api, exceptions, models, tools, _
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class IapAutocompleteEnrichAPI(models.AbstractModel):
    _name = 'iap.autocomplete.api'
    _description = 'IAP Partner Autocomplete API'
    _DEFAULT_ENDPOINT = 'https://partner-autocomplete.odoo.com'

    @api.model
    def _contact_iap(self, local_endpoint, action, params, timeout=15):
        if self.env.registry.in_test_mode():
            raise exceptions.ValidationError(_('Test mode'))

        account = self.env['iap.account'].get('partner_autocomplete')
        if not account.account_token:
            raise ValueError(_('No account token'))
        params.update({
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'account_token': account.account_token,
            'country_code': self.env.company.country_id.code,
            'zip': self.env.company.zip,
        })
        base_url = self.env['ir.config_parameter'].sudo().get_param('iap.partner_autocomplete.endpoint', self._DEFAULT_ENDPOINT)
        return iap_tools.iap_jsonrpc(base_url + local_endpoint + '/' + action, params=params, timeout=timeout)

    @api.model
    def _request_partner_autocomplete(self, action, params, timeout=15):
        """ Contact endpoint to get autocomplete data.

        :param params: {
            'domain': company_domain,
            'partner_gid': partner_gid,
            'vat': vat,
        },

        :return tuple: results, error code
        """
        try:
            results = self._contact_iap('/iap/partner_autocomplete', action, params, timeout=timeout)
        except exceptions.ValidationError:
            return False, 'Insufficient Credit'
        except (ConnectionError, HTTPError, exceptions.AccessError, exceptions.UserError) as exception:
            _logger.error('Autocomplete API error: %s', str(exception))
            return False, str(exception)
        except iap_tools.InsufficientCreditError as exception:
            _logger.warning('Insufficient Credits for Autocomplete Service: %s', str(exception))
            return False, 'Insufficient Credit'
        except ValueError:
            return False, 'No account token'
        return results, False

    @api.model
    def _get_contact_vals_from_response_js(self, iap_payload, include_logo=False):
        self._replace_location_codes(iap_payload)

        if iap_payload.get('child_ids'):
            for child_vals in iap_payload['child_ids']:
                self._replace_location_codes(child_vals)

        if iap_payload.get('additional_info'):
            iap_payload['additional_info'] = json.dumps(iap_payload['additional_info'])

        logo_url = iap_payload['logo']
        if logo_url and include_logo:
            iap_payload['image_1920'] = False
            try:
                response = requests.get(logo_url, timeout=2)
                if response.ok:
                    iap_payload['image_1920'] = base64.b64encode(response.content)
            except Exception as e:
                _logger.warning('Download of image for contact or company %s failed, error %s', iap_payload['name'], e)
            # avoid keeping falsy images (may happen that a blank page is returned that leads to an incorrect image)
            if iap_payload['image_1920']:
                try:
                    tools.base64_to_image(iap_payload['image_1920'])
                except Exception:
                    iap_payload.pop('image_1920')
        return iap_payload

    @api.model
    def _get_contact_vals_from_response(self, iap_payload, include_logo=False):
        iap_payload = self._get_contact_vals_from_response_js(iap_payload, include_logo=include_logo)

        contact_data = {
            field: value for field, value in iap_payload.items()
            if field in self.env['res.partner']._fields and value
        }
        child_commands = []
        for child_vals in iap_payload.get('child_ids') or []:
            child_vals['country_id'] = child_vals['country_id']['id'] if child_vals.get('country_id') else False
            child_vals['state_id'] = child_vals['state_id']['id'] if child_vals.get('state_id') else False
            child_commands.append((0, 0, child_vals))
        contact_data['child_ids'] = child_commands
        contact_data['bank_ids'] = [(0, 0, bank_vals) for bank_vals in iap_payload.get('bank_ids') or []]
        contact_data['country_id'] = contact_data['country_id']['id'] if contact_data.get('country_id') else False
        contact_data['state_id'] = contact_data['state_id']['id'] if contact_data.get('state_id') else False

        return contact_data

    @api.model
    def _replace_location_codes(self, iap_payload):
        country_code, country_name = iap_payload.pop('country_code', False), iap_payload.pop('country_name', False)
        state_code, state_name = iap_payload.pop('state_code', False), iap_payload.pop('state_name', False)

        country, state = None, None
        if country_code:
            country = self.env['res.country'].search([['code', '=ilike', country_code]])
        if not country and country_name:
            country = self.env['res.country'].search([['name', '=ilike', country_name]])

        if country:
            if state_code:
                state = self.env['res.country.state'].search([
                    ('country_id', '=', country.id), ('code', '=ilike', state_code)
                ], limit=1)
            if not state and state_name:
                state = self.env['res.country.state'].search([
                    ('country_id', '=', country.id), ('name', '=ilike', state_name)
                ], limit=1)
        else:
            _logger.info('Country code not found: %s', country_code)

        if country:
            iap_payload['country_id'] = {'id': country.id, 'display_name': country.display_name}
        if state:
            iap_payload['state_id'] = {'id': state.id, 'display_name': state.display_name}

        return country, state
