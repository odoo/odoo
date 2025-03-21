from odoo.addons.sms_twilio.tests.common import MockSmsTwilio
from odoo.addons.sms_twilio.tools import sms_twilio as twilio_tools
from odoo.tools import mute_logger
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install', 'twilio', 'twilio_controller')
class TestSmsTwilioController(MockSmsTwilio, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_sms_twilio(cls.user_admin.company_id)

    @mute_logger('odoo.addons.sms_twilio.controllers.controllers')
    @users('employee')
    def test_sms_twilio_controller_status(self):
        """Test that the controller correctly processes the webhook calls we
        receive from Twilio"""
        # All good
        ok = self.webhook_ok_response.copy()
        # Handle known errors (the ones that we have already mapped)
        invalid_destination = {
            **self.webhook_ok_response,
            "SmsStatus": "undelivered",
            "ErrorCode": 30005,
            "ErrorMessage": "Unknown destination handset",
        }
        # Handle unknown errors (the ones that we not have mapped)
        unknown_error = {
            **self.webhook_ok_response,
            "SmsStatus": "failed",
            "ErrorCode": 12345,
            "ErrorMessage": "Unknown error",
        }
        # Unknown status -> no update
        wrong_status = {
            **self.webhook_ok_response,
            "SmsStatus": "myfakestatus",
            "ErrorCode": 12345,
            "ErrorMessage": "Unknown error",
        }
        with self.mock_sms_twilio_gateway():
            for call_params, expected_data in zip(
                [ok, invalid_destination, unknown_error, wrong_status],
                [{
                    'failure_type': False,
                    'failure_reason': False,
                    'notification_status': 'sent',
                }, {
                    'failure_type': 'sms_invalid_destination',
                    'failure_reason': "Unknown destination handset",
                    'notification_status': 'bounce',
                }, {
                    'failure_type': 'unknown',
                    'failure_reason': "Unknown error",
                    'notification_status': 'exception',
                }, {
                    'failure_type': False,
                    'failure_reason': False,
                    'notification_status': 'pending',
                },
                ],
                strict=True,
            ):
                with self.subTest(call_params=call_params):
                    composer = self.env['sms.composer'].with_context(
                        active_model='res.partner',
                        active_id=self.valid_partner,
                    ).create({'body': "SMS Body"})
                    composer._action_send_sms()
                    sms = self._new_sms[-1]

                    expected_signature = twilio_tools.generate_twilio_sms_callback_signature(
                        self.user_admin.company_id,
                        sms.uuid,
                        call_params,
                    )
                    # Simulate callback webhook called by Twilio
                    _python_versionresponse = self.url_open(
                        f"/sms_twilio/status/{sms.uuid}", call_params,
                        headers={
                            "X-Twilio-Signature": expected_signature,
                        },
                    )
                    self.assertRecordValues(sms.sms_tracker_id.mail_notification_id, [{
                        'notification_status': expected_data["notification_status"],
                        'failure_type': expected_data["failure_type"],
                        'failure_reason': expected_data["failure_reason"],
                    }])

    @mute_logger('odoo.addons.sms_twilio.controllers.controllers')
    @users('employee')
    def test_sms_twilio_controller_status_signature(self):
        """ Check X-Twilio-Signature is effectively checked """
        call_params = self.webhook_ok_response.copy()
        with self.mock_sms_twilio_gateway():
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': "Body msg"})
            composer._action_send_sms()
            sms = self._new_sms[-1]

            # Simulate callback webhook called by Twilio
            response = self.url_open(
                f"/sms_twilio/status/{sms.uuid}", call_params,
                headers={
                    "X-Twilio-Signature": "WrongSignature",
                },
            )
            self.assertEqual(response.status_code, 404)
            # SMS not updated
            self.assertRecordValues(sms.sms_tracker_id.mail_notification_id, [{
                'notification_status': 'pending',
                'failure_type': False,
                'failure_reason': False,
            }])
