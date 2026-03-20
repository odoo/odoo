import hmac
import logging
import re

from odoo.addons.sms_twilio.tools.sms_twilio import generate_twilio_sms_callback_signature
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
    def update_sms_status(self, uuid, SmsStatus=None, ErrorCode=None, ErrorMessage=None, **kwargs):
        # Verify Odoo Sms Uuid Validity
        if not re.match(r'^[0-9a-f]{32}$', uuid):
            _logger.warning("Twilio SMS: update_sms_status received a non-valid uuid='%s'", uuid)
            raise request.not_found()

        # Verify Twilio Status
        if SmsStatus not in TWILIO_TO_SMS_STATE:
            _logger.warning("Twilio SMS: update_sms_status received unknown twilio_status='%s'", SmsStatus)
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

        if SmsStatus in TWILIO_TO_SMS_STATE_ERRORS:
            sms_tracker_sudo._action_update_from_twilio_error(SmsStatus, ErrorCode, ErrorMessage)
        else:
            sms_tracker_sudo._action_update_from_sms_state(TWILIO_TO_SMS_STATE[SmsStatus])

        # Mark Sms as to be deleted
        request.env['sms.sms'].sudo().search([('uuid', '=', uuid), ('to_delete', '=', False)]).to_delete = True

        return "OK"

    def _validate_twilio_signature(self, request, uuid):
        company_sudo = request.env['sms.sms'].sudo().search([('uuid', '=', uuid)])._get_sms_company().sudo()
        computed_signature = generate_twilio_sms_callback_signature(
            company_sudo,
            uuid,
            request.httprequest.form.to_dict()
        )
        x_twilio_signature = request.httprequest.headers.get('X-Twilio-Signature', '')
        return hmac.compare_digest(computed_signature, x_twilio_signature)
