# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.iap.tools import iap_tools
from odoo.tools.translate import _, LazyTranslate

_lt = LazyTranslate(__name__)

ERROR_MESSAGES = {
    # Errors that could occur while updating sender name
    'format_error': _lt("Your sender name must be between 3 and 11 characters long and only contain alphanumeric characters."),
    'unregistered_account': _lt("Your sms account has not been activated yet."),
    'existing_sender': _lt("This account already has an existing sender name and it cannot be changed."),

    # Errors that could occur while sending the verification code
    'invalid_phone_number': _lt("Invalid phone number. Please make sure to follow the international format, i.e. a plus sign (+), then country code, city code, and local phone number. For example: +1 555-555-555"),
    'verification_sms_delivery': _lt(
        "We were not able to reach you via your phone number. "
        "If you have requested multiple codes recently, please retry later."
    ),
    'closed_feature': _lt("The SMS Service is currently unavailable for new users and new accounts registrations are suspended."),
    'banned_account': _lt("This phone number/account has been banned from our service."),

    # Errors that could occur while verifying the code
    'invalid_code': _lt("The verification code is incorrect."),
    'no_sms_account': _lt("We were not able to find your account in our database."),
    'too_many_attempts': _lt("You tried too many times. Please retry later."),

    # Default error
    'unknown_error': _lt("An unknown error occurred. Please contact Odoo support if this error persists."),
}


class SmsApiBase:
    PROVIDER_TO_SMS_FAILURE_TYPE = {
        'server_error': 'sms_server',
        'sms_number_missing': 'sms_number_missing',
        'wrong_number_format': 'sms_number_format',
    }

    def __init__(self, env, account=None):
        self.env = env
        self.company = env.company

    def _get_sms_api_error_messages(self):
        """Return a mapping of `_send_sms_batch` errors to an error message."""
        return {}

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        raise NotImplementedError()

    def _set_company(self, company):
        self.company = company


class SmsApi(SmsApiBase):  # TODO RIGR in master: rename SmsApi to SmsApiIAP, and  SmsApiBase to SmsApi
    DEFAULT_ENDPOINT = 'https://sms.api.odoo.com'
    PROVIDER_TO_SMS_FAILURE_TYPE = SmsApiBase.PROVIDER_TO_SMS_FAILURE_TYPE | {
        'country_not_supported': 'sms_country_not_supported',
        'insufficient_credit': 'sms_credit',
        'unregistered': 'sms_acc',
    }

    def __init__(self, env, account=None):
        super().__init__(env, account=account)
        self.account = account or self.env['iap.account'].get('sms')

    def _contact_iap(self, local_endpoint, params, timeout=15):
        if not self.env.registry.ready:  # Don't reach IAP servers during module installation
            raise exceptions.AccessError("Unavailable during module installation.")

        params['account_token'] = self.account.account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', self.DEFAULT_ENDPOINT)
        return iap_tools.iap_jsonrpc(endpoint + local_endpoint, params=params, timeout=timeout)

    def _send_sms_batch(self, messages, delivery_reports_url=False):  # TODO RIGR: switch to kwargs in master
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
        :param str delivery_reports_url: url to route receiving delivery reports. Deprecated  # TODO RIGR: remove in master
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
        return self._contact_iap('/api/sms/3/send', {
            'messages': messages,
            'webhook_url': delivery_reports_url,
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        })

    def _get_sms_api_error_messages(self):
        """Return a mapping of `_send_sms_batch` errors to an error message.

        We prefer a dict instead of a message-per-error-state based method so that we only call
        config parameters getters once and avoid extra RPC calls."""
        buy_credits_url = self.env['iap.account'].sudo().get_credits_url(service_name='sms')
        buy_credits = '<a href="{}" target="_blank">{}</a>'.format(buy_credits_url, _("Buy credits."))

        sms_endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', self.DEFAULT_ENDPOINT)
        sms_account_token = self.env['iap.account'].sudo().get('sms').account_token
        register_now = f'<a href="{sms_endpoint}/1/account?account_token={sms_account_token}" target="_blank">%s</a>' % (
            _('Register now.')
        )

        error_dict = super()._get_sms_api_error_messages()
        error_dict.update({
            'unregistered': _("You don't have an eligible IAP account."),
            'insufficient_credit': ' '.join([_("You don't have enough credits on your IAP account."), buy_credits]),
            'wrong_number_format': _("The number you're trying to reach is not correctly formatted."),
            'duplicate_message': _("This SMS has been removed as the number was already used."),
            'country_not_supported': _("The destination country is not supported."),
            'incompatible_content': _("The content of the message violates rules applied by our providers."),
            'registration_needed': ' '.join([_("Country-specific registration required."), register_now]),
        })
        return error_dict

    def _send_verification_sms(self, phone_number):
        return self._contact_iap('/api/sms/1/account/create', {
            'phone_number': phone_number,
        })

    def _verify_account(self, verification_code):
        return self._contact_iap('/api/sms/2/account/verify', {
            'code': verification_code,
        })

    def _set_sender_name(self, sender_name):
        return self._contact_iap('/api/sms/1/account/update_sender', {
            'sender_name': sender_name,
        })
