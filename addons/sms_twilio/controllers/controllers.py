import base64
import hashlib
import hmac
import logging
import re

from odoo.addons.sms_twilio.tools.sms_api import get_twilio_status_callback_url
from odoo.http import Controller, request, route


TWILIO_TO_SMS_STATE_ERRORS = {
    'failed': 'error',
    'undelivered': 'error',
}

TWILIO_TO_SMS_STATE = {
    # https://www.twilio.com/docs/messaging/api/message-resource#message-status-values
    'queued': 'outgoing',
    'sending': 'process',
    'sent': 'pending',
    'delivered': 'sent',
    'receiving': 'process',
    'received': 'pending',
    'accepted': 'outgoing',
    'scheduled': 'outgoing',
    'canceled': 'canceled',
    **TWILIO_TO_SMS_STATE_ERRORS,
}

_logger = logging.getLogger(__name__)


class SmsTwilioController(Controller):
    @route('/sms_twilio/status/<string:uuid>', type='http', auth='public', methods=['POST'], csrf=False)
    def update_sms_status(self, uuid, **kwargs):
        # Verify Odoo Sms Uuid Validity
        if not re.match(r'^[0-9a-f]{32}$', uuid):
            _logger.warning("Twilio SMS: update_sms_status received a non-valid uuid='%s'", uuid)
            raise request.not_found()

        # Verify Twilio Status
        twilio_status = kwargs.get('SmsStatus')
        if twilio_status not in TWILIO_TO_SMS_STATE:
            _logger.warning("Twilio SMS: update_sms_status received unknown twilio_status='%s'", twilio_status)
            raise request.not_found()

        # Verify Twilio Signature
        if not self._validate_twilio_signature(request, uuid):
            _logger.warning("Twilio SMS: update_sms_status could not validate Twilio signature with uuid='%s'", uuid)
            raise request.not_found()

        # Update the tracker with the state
        sms_tracker_sudo = request.env['sms.tracker'].sudo().search([('sms_uuid', '=', uuid)])
        if not sms_tracker_sudo:
            _logger.warning("Twilio SMS: update_sms_status could not find a matching SMS tracker for sms_uuid=%s", uuid)
            return

        if twilio_status in TWILIO_TO_SMS_STATE_ERRORS:
            sms_tracker_sudo._action_update_from_twilio_error(twilio_status, kwargs.get("ErrorCode"), kwargs.get("ErrorMessage"))
        else:
            sms_tracker_sudo._action_update_from_sms_state(TWILIO_TO_SMS_STATE[twilio_status])

        # Mark Sms as to be deleted
        request.env['sms.sms'].sudo().search([('uuid', '=', uuid), ('to_delete', '=', False)]).to_delete = True

        return "OK"

    def _validate_twilio_signature(self, request, uuid):
        company_sudo = request.env['sms.sms'].sudo().search([('uuid', '=', uuid)])._get_sms_company().sudo()
        auth_token = company_sudo.sms_twilio_auth_token
        x_twilio_signature = request.httprequest.headers.get('X-Twilio-Signature', '')
        url = get_twilio_status_callback_url(company_sudo, uuid)
        params = request.httprequest.form.to_dict()

        # Sort the POST parameters by key and concatenate them to URL
        sorted_params = ''.join(f"{k}{v}" for k, v in sorted(params.items()))
        data = url + sorted_params

        # Compute HMAC-SHA1 digest and then base64 encode
        computed_signature = base64.b64encode(
            hmac.new(
                auth_token.encode(),
                data.encode(),
                hashlib.sha1
            ).digest()
        ).decode()
        return hmac.compare_digest(computed_signature, x_twilio_signature)
