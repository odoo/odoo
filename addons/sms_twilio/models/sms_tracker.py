from odoo import models, fields

TWILIO_CODE_TO_FAILURE_TYPE = {
    # https://www.twilio.com/docs/messaging/guides/debugging-tools#error-codes
    '30002': "expired",  # Account suspended
    '30003': "invalid_destination",  # Unreachable destination handset
    '30004': "rejected",  # Message blocked
    '30005': "invalid_destination",  # Unknown destination handset
    '30006': "not_allowed",  # Landline or unreachable carrier
    '30007': "rejected",  # Carrier violation
    '30008': "not_delivered",  # Unknown error
}


class SmsTracker(models.Model):
    _inherit = 'sms.tracker'

    sms_twilio_sid = fields.Char(string='Twilio SMS SID', readonly=True)

    def _action_update_from_twilio_error(self, sms_status, error_code, error_message):
        """Update the SMS tracker with the Twilio Status and Error code/msg"""
        failure_type = (
            TWILIO_CODE_TO_FAILURE_TYPE.get(error_code)
            or (None if sms_status == "failed" else "not_delivered")
        )
        return self.with_context(sms_known_failure_reason=error_message)._action_update_from_provider_error(failure_type)
