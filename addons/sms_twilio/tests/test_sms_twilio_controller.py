from odoo.tools import mute_logger
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.sms.tests.common import SMSCase
from odoo.addons.sms_twilio.tests.common import MockSmsTwilioApi


@tagged('post_install', '-at_install')
class TestSmsTwilioController(MockSmsTwilioApi, SMSCase, HttpCase):
    def test_sms_twilio_controller_flows(self):
        """Test that the controller correctly processes the webhook calls we receive from Twilio"""
        # All good
        ok = {
            "webhook_response": self.webhook_ok_response,
            "expected_webhook_notif_status": "sent",
            "expected_webhook_failure_type": False,
            "expected_webhook_failure_reason": False,
        }
        # Handle known errors (the ones that we have already mapped)
        invalid_destination = {
            "webhook_response": {
                **self.webhook_ok_response,
                "SmsStatus": "undelivered",
                "ErrorCode": 30005,
                "ErrorMessage": "Unknown destination handset",
            },
            "expected_webhook_notif_status": "bounce",
            "expected_webhook_failure_type": "sms_invalid_destination",
            "expected_webhook_failure_reason": "Unknown destination handset",
        }
        # Handle unknown errors (the ones that we not have mapped)
        unknown_error = {
            "webhook_response": {
                **self.webhook_ok_response,
                "SmsStatus": "failed",
                "ErrorCode": 12345,
                "ErrorMessage": "Unknown error",
            },
            "expected_webhook_notif_status": "exception",
            "expected_webhook_failure_type": "unknown",
            "expected_webhook_failure_reason": "Unknown error",
        }
        with self.setup_and_mock_sms_twilio_gateway():
            for test in [ok, invalid_destination, unknown_error]:
                with self.subTest(test=test):
                    composer = self.env['sms.composer'].with_context(
                        active_model='res.partner',
                        active_id=self.valid_partner,
                    ).create({'body': "SMS Body"})
                    composer._action_send_sms()

                    # Simulate callback webhook called by Twilio
                    self.url_open(f"/sms_twilio/status/{self._new_sms[-1].uuid}", test['webhook_response'])
                    self.assertRecordValues(self._new_sms[-1].sms_tracker_id.mail_notification_id, [{
                        'notification_status': test["expected_webhook_notif_status"],
                        'failure_type': test["expected_webhook_failure_type"],
                        'failure_reason': test["expected_webhook_failure_reason"],
                    }])

    def test_sms_twilio_controller_security_status(self):
        webhook_fake_response = {
            **self.webhook_ok_response,
            "SmsStatus": "myfakestatus",
            "ErrorCode": 12345,
            "ErrorMessage": "Unknown error",
        }
        with (
            mute_logger('odoo.addons.sms_twilio.controllers.controllers'),  # mute route "update_sms_status"
            self.setup_and_mock_sms_twilio_gateway(),
        ):
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': "Body msg"})
            composer._action_send_sms()

            # Simulate callback webhook called by Twilio
            response = self.url_open(f"/sms_twilio/status/{self._new_sms[-1].uuid}", webhook_fake_response)
            self.assertEqual(response.status_code, 404)
            # SMS not updated
            self.assertRecordValues(self._new_sms[-1].sms_tracker_id.mail_notification_id, [{
                'notification_status': 'pending',
                'failure_type': False,
                'failure_reason': False,
            }])
