import logging
import requests

from odoo import _
from odoo.addons.sms.tools.sms_api import SmsApiBase
from odoo.addons.sms_twilio.tools.sms_twilio import get_twilio_from_number, get_twilio_status_callback_url

_logger = logging.getLogger(__name__)


class SmsApiTwilio(SmsApiBase):
    PROVIDER_TO_SMS_FAILURE_TYPE = SmsApiBase.PROVIDER_TO_SMS_FAILURE_TYPE | {
        'twilio_acc_unverified': 'sms_acc',
        'twilio_authentication': 'sms_credit',
        'twilio_callback': 'twilio_callback',
        'twilio_from_missing': 'twilio_from_missing',
        'twilio_from_to': 'twilio_from_to',
    }

    def _sms_twilio_send_request(self, session, to_number, body, uuid):
        company_sudo = (self.company or self.env.company).sudo()
        company_sudo._assert_twilio_sid()
        from_number = get_twilio_from_number(company_sudo, to_number)
        data = {
            'From': from_number.number or '',  # avoid 'False', to have clear missing From error
            'To': to_number,
            'Body': body,
            'StatusCallback': get_twilio_status_callback_url(company_sudo, uuid),
        }
        try:
            return session.post(
                f'https://api.twilio.com/2010-04-01/Accounts/{company_sudo.sms_twilio_account_sid}/Messages.json',
                data=data,
                auth=(company_sudo.sms_twilio_account_sid, company_sudo.sms_twilio_auth_token),
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            _logger.warning('Twilio SMS API error: %s', str(e))
        return None

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        """ Send a batch of SMS using twilio.
        See params and returns in original method sms/tools/sms_api.py
        In addition to the uuid and state, we add the sms_twilio_sid to the returns (one per sms)
        """
        # Use a session as we have to sequentially call twilio, might save time
        session = requests.Session()

        res = []
        for message in messages:
            body = message.get('content') or ''
            for number_info in message.get('numbers') or []:
                uuid = number_info['uuid']
                response = self._sms_twilio_send_request(session, number_info['number'], body, uuid)
                fields_values = {
                    'failure_reason':  _("Unknown failure at sending, please contact Odoo support"),
                    'state': 'server_error',
                    'uuid': uuid,
                }
                if response is not None:
                    response_json = response.json()
                    if not response.ok or response_json.get('error'):
                        failure_type = self._twilio_error_code_to_odoo_state(response_json)
                        error_message = response_json.get('message') or response_json.get('error_message') or self._get_sms_api_error_messages().get(failure_type)
                        fields_values.update({
                            'failure_reason': error_message,
                            'failure_type': failure_type,
                            'state': failure_type,
                        })
                    else:
                        fields_values.update({
                            'failure_reason': False,
                            'failure_type': False,
                            'sms_twilio_sid': response_json.get('sid'),
                            'state': 'sent',
                        })
                res.append(fields_values)
        return res

    def _twilio_error_code_to_odoo_state(self, response_json):
        error_code = response_json.get('code') or response_json.get('error_code')
        # number issues
        if error_code in (21211, 21614, 21265):  # See https://www.twilio.com/docs/errors/xxxxx
            return "wrong_number_format"
        elif error_code == 21604:
            # A "To" phone number is required
            return "sms_number_missing"
        elif error_code == 21266:
            return "twilio_from_to"
        elif error_code == 21603:
            return "twilio_from_missing"
        # configuration
        elif error_code == 21608:
            return "twilio_acc_unverified"
        elif error_code == 21609:
            # Twilio StatusCallback URL is incorrect
            return "twilio_callback"
        _logger.warning('Twilio SMS: Unknown error "%s" (code: %s)', response_json.get('message'), error_code)
        return "unknown"

    def _get_sms_api_error_messages(self):
        # TDE TODO: clean failure type management
        error_dict = super()._get_sms_api_error_messages()
        error_dict.update({
            'sms_acc': _("Trial Account Limitation"),
            'sms_number_missing': _("A 'To' phone number is required"),
            'twilio_acc_unverified': _("Unverified recipient on Trial Account"),
            'twilio_authentication': _("Twilio Authentication Error"),
            'twilio_callback': _("Twilio StatusCallback URL is incorrect"),
            'twilio_from_missing': ("A 'From' number is required to send a message"),
            'twilio_from_to': _("'To' and 'From' numbers cannot be the same"),
            'wrong_number_format': _("The number you're trying to reach is not correctly formatted"),
            # fallback
            'unknown': _("Unknown error, please contact Odoo support"),
        })
        return error_dict
