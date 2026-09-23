import logging

from odoo.http import Controller, request, route

TWILIO_TO_SMS_STATE_ERRORS = {
    "failed": "error",
    "undelivered": "error",
}

TWILIO_TO_SMS_STATE = {
    # https://www.twilio.com/docs/messaging/api/message-resource#message-status-values
    "queued": "outgoing",
    "sending": "process",
    "sent": "pending",
    "delivered": "sent",
    "receiving": "process",
    "received": "pending",
    "accepted": "outgoing",
    "scheduled": "outgoing",
    "canceled": "canceled",
    **TWILIO_TO_SMS_STATE_ERRORS,
}

_logger = logging.getLogger(__name__)


class SmsTwilioController(Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @route(
        "/sms_twilio/status/<string:uuid>",
        type="http",
        auth="receiver",
        receiver="sms.sms:_receiver_for_twilio_status",
        receiver_event="sms_twilio_status",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def update_sms_status(
        self,
        uuid: str,
        SmsStatus: str | None = None,
        ErrorCode: str | None = None,
        ErrorMessage: str | None = None,
        **kwargs,
    ):
        if SmsStatus not in TWILIO_TO_SMS_STATE:
            _logger.warning(
                "Twilio SMS: update_sms_status received unknown twilio_status='%s'",
                SmsStatus,
            )
            raise request.prepare_not_found_error()

        # Update the tracker with the state
        sms_tracker_sudo = (
            request.env["sms.tracker"].sudo().search([("sms_uuid", "=", uuid)])
        )
        if not sms_tracker_sudo:
            _logger.warning(
                "Twilio SMS: update_sms_status could not find a matching SMS tracker for sms_uuid=%s",
                uuid,
            )
            return None

        if SmsStatus in TWILIO_TO_SMS_STATE_ERRORS:
            sms_tracker_sudo._action_update_from_twilio_error(
                SmsStatus, ErrorCode, ErrorMessage
            )
        else:
            sms_tracker_sudo._action_update_from_sms_state(
                TWILIO_TO_SMS_STATE[SmsStatus]
            )

        # Mark Sms as to be deleted
        request.env["sms.sms"].sudo().search(
            [("uuid", "=", uuid), ("to_delete", "=", False)]
        ).to_delete = True
        return "OK"
