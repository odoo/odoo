# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.addons.iap.tools import iap_tools

DEFAULT_ENDPOINT = 'https://iap-sms.odoo.com'


class SmsApi(models.AbstractModel):
    _name = 'sms.api'
    _description = 'SMS API'

    @api.model
    def _contact_iap(self, local_endpoint, params):
        account = self.env['iap.account'].get('sms')
        params['account_token'] = account.account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', DEFAULT_ENDPOINT)
        # TODO PRO, the default timeout is 15, do we have to increase it ?
        return iap_tools.iap_jsonrpc(endpoint + local_endpoint, params=params)

    @api.model
    def _send_sms(self, numbers, message):
        """ Send a single message to several numbers

        :param numbers: list of E164 formatted phone numbers
        :param message: content to send

        :raises ? TDE FIXME
        """
        params = {
            'numbers': numbers,
            'message': message,
        }
        return self._contact_iap('/iap/message_send', params)

    @api.model
    def _send_sms_batch(self, messages, dlr=False):
        """ Send SMS using IAP in batch mode

        :param list messages: list of SMS (grouped by content) to send:
            [
                {
                    'content' : str,
                    'numbers' : [
                        {
                            'uuid' : str,
                            'number' : str,
                        },
                        {
                            'uuid' : str,
                            'number' : str,
                        },
                        ...
                    ]
                },
                {
                    'content' : str,
                    'numbers' : [{...}, {...}, ...]
                },
                ...
            ]
        :param bool dlr: whether to receive delivery reports or not

        :return: return of /iap/sms/1/send controller which is a list of dict [{
            'uuid': string: UUID of sms.sms,
            'state': string: One of the following: {
                'success', 'server_error', 'unregistered', 'insufficient_credit',
                'wrong_number_format', 'duplicate_message', 'no_compatible_provider',
            }
            'credit': integer: number of credits spent to send this SMS (is only
                returned if the definitive amount is known),
        }]

        NOTE: IAP returning 'success' simply means that:
            - the request to send the message has been received by IAP
            - enough credits are available to send the message
            - the given number has the correct format (no guarantee that the number exists)
            - the country the number is registered in is supported by IAP
            - the content is non-empty and conforms to rules applied by IAP's providers
            - the message has NOT YET been sent
            - the message can still be blocked by anti-spam mechanisms

        :raises: normally none
        """
        params = {
            'messages': messages,
            'webhook_url': dlr and (self.get_base_url() + '/sms/status')
        }
        return self._contact_iap('/iap/sms/3/send', params)

    @api.model
    def _get_sms_api_error_messages(self):
        """ Returns a dict containing the error message to display for every known error 'state'
        resulting from the '_send_sms_batch' method.
        We prefer a dict instead of a message-per-error-state based method so we only call
        the 'get_credits_url' once, to avoid extra RPC calls. """

        buy_credits_url = self.sudo().env['iap.account'].get_credits_url(service_name='sms')
        buy_credits = '<a href="%s" target="_blank">%s</a>' % (
            buy_credits_url,
            _('Buy credits.')
        )
        return {
            'unregistered': _("You don't have an eligible IAP account."),
            'insufficient_credit': ' '.join([_('You don\'t have enough credits on your IAP account.'), buy_credits]),
            'wrong_number_format': _("The number you're trying to reach is not correctly formatted."),
            'duplicate_message': _('A SMS has bee removed since it was duplicated.'),
            'country_not_supported': _('The destination country is not supported.'),
            'incompatible_content': _('The content of the message violates rules applied by our providers.')
        }
