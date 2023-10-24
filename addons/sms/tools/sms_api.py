# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.iap.tools import iap_tools


class SmsApi:
    DEFAULT_ENDPOINT = 'https://sms.api.odoo.com'

    def __init__(self, env):
        self.env = env

    def _contact_iap(self, local_endpoint, params, timeout=15):
        account = self.env['iap.account'].get('sms')
        params['account_token'] = account.account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', self.DEFAULT_ENDPOINT)
        return iap_tools.iap_jsonrpc(endpoint + local_endpoint, params=params, timeout=timeout)

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        """ Send SMS using IAP in batch mode

        :param list messages: list of SMS (grouped by content) to send:
          formatted as ```[
              {
                  'content' : str,
                  'numbers' : [
                      { 'uuid' : str, 'number' : str },
                      { 'uuid' : str, 'number' : str },
                      ...
                  ]
              }, ...
          ]```
        :param str delivery_reports_url: url to route receiving delivery reports
        :return: response from the endpoint called, which is a list of results
          formatted as ```[
              {
                  uuid: UUID of the request,
                  state: ONE of: {
                      'success', 'processing', 'server_error', 'unregistered', 'insufficient_credit',
                      'wrong_number_format', 'duplicate_message', 'country_not_supported', 'registration_needed',
                  },
                  credit: Optional: Credits spent to send SMS (provided if the actual price is known)
              }, ...
          ]```
        """
        return self._contact_iap('/iap/sms/3/send', {'messages': messages, 'webhook_url': delivery_reports_url})

    def _get_sms_api_error_messages(self):
        """Return a mapping of `_send_sms_batch` errors to an error message.

        We prefer a dict instead of a message-per-error-state based method so that we only call
        config parameters getters once and avoid extra RPC calls."""
        buy_credits_url = self.env['iap.account'].sudo().get_credits_url(service_name='sms')
        buy_credits = f'<a href="{buy_credits_url}" target="_blank">%s</a>' % _('Buy credits.')

        sms_endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', self.DEFAULT_ENDPOINT)
        sms_account_token = self.env['iap.account'].sudo().get('sms').account_token
        register_now = f'<a href="{sms_endpoint}/1/account?account_token={sms_account_token}" target="_blank">%s</a>' % (
            _('Register now.')
        )

        return {
            'unregistered': _("You don't have an eligible IAP account."),
            'insufficient_credit': ' '.join([_("You don't have enough credits on your IAP account."), buy_credits]),
            'wrong_number_format': _("The number you're trying to reach is not correctly formatted."),
            'duplicate_message': _("This SMS has been removed as the number was already used."),
            'country_not_supported': _("The destination country is not supported."),
            'incompatible_content': _("The content of the message violates rules applied by our providers."),
            'registration_needed': ' '.join([_("Country-specific registration required."), register_now]),
        }
