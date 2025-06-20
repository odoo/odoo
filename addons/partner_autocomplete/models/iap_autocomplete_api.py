# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, exceptions, _, release
from odoo.addons.iap.tools import iap_tools
from requests.exceptions import HTTPError

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
            'db_version': release.version,
            'db_lang': self.env.lang,
            'account_token': account.account_token,
            'country_code': self.env.company.country_id.code,
            'zip': self.env.company.zip,
        })
        base_url = self.env['ir.config_parameter'].sudo().get_param('iap.partner_autocomplete.endpoint', self._DEFAULT_ENDPOINT)
        return iap_tools.iap_jsonrpc(base_url + local_endpoint + '/' + action, params=params, timeout=timeout)

    @api.model
    def _request_partner_autocomplete(self, action, params, timeout=15):
        """ Contact endpoint to get autocomplete data.

        :return tuple: results, error code
        """
        try:
            results = self._contact_iap('/api/dnb/1', action, params, timeout=timeout)
        except exceptions.ValidationError:
            return False, 'Insufficient Credit'
        except (ConnectionError, HTTPError, exceptions.AccessError, exceptions.UserError) as exception:
            _logger.warning('Autocomplete API error: %s', str(exception))
            return False, str(exception)
        except iap_tools.InsufficientCreditError as exception:
            _logger.warning('Insufficient Credits for Autocomplete Service: %s', str(exception))
            return False, 'Insufficient Credit'
        except ValueError:
            return False, 'No account token'
        return results, False
