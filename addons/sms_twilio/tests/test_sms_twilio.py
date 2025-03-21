from contextlib import contextmanager
from unittest.mock import patch

from odoo.tools import mute_logger
from odoo.tests import common, tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.sms.tests.common import SMSCase

from odoo.addons.sms.models.sms_sms import SmsSms
from odoo.addons.sms_twilio.tools.sms_api import SmsApiTwilio
from odoo.addons.sms_twilio.controllers.controllers import SmsTwilioController


class MockedTwilioResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    @property
    def ok(self):
        return self.status_code in (200, 201)

    def json(self):
        return self.json_data


class MockSmsTwilioApi(common.BaseCase):
    """
    This test takes inspiration from sms/tests/{common,test_sms_composer}
    """
    def setUp(self):
        super().setUp()
        self.valid_phone_number = "+12202154155"
        self.invalid_phone_number = "+3212312312"
        self.valid_partner = self.env['res.partner'].create({
            'name': 'TestingPartner',
            'mobile': self.valid_phone_number,
        })
        self.invalid_partner = self.env['res.partner'].create({
            'name': 'TestingPartner',
            'mobile': self.invalid_phone_number,
        })

    def tearDown(self):
        super().tearDown()
        self._clear_sms_sent()

    def _sms_twilio_send_request(self, record, to_number, body, uuid):
        ok_json = {
            "account_sid": "ACfake",
            "api_version": "2010-04-01",
            "body": body,
            "date_created": "Mon, 14 Apr 2025 09:27:41 +0000",
            "date_sent": None,
            "date_updated": "Mon, 14 Apr 2025 09:27:41 +0000",
            "direction": "outbound-api",
            "error_code": None,
            "error_message": None,
            "from": "+12212341234",
            "messaging_service_sid": None,
            "num_media": "0",
            "num_segments": "1",
            "price": None,
            "price_unit": "USD",
            "sid": "SMfake",
            "status": "queued",
            "subresource_uris": {
                "media": "/2010-04-01/Accounts/ACfake/Messages/SMfake/Media.json"
            },
            "to": to_number,
            "uri": "/2010-04-01/Accounts/ACfake/Messages/SMfake.json",
        }
        nok_json = {
            'code': 21211,
            'message': "Invalid 'To' Phone Number: +324863XXXX",
            'more_info': 'https://www.twilio.com/docs/errors/21211',
            'status': 400,
        }
        if to_number == self.invalid_phone_number:
            response = MockedTwilioResponse(json_data=nok_json, status_code=400)
        else:
            response = MockedTwilioResponse(json_data=ok_json, status_code=201)

        self._sms += [{
            'number': to_number,
            'body': body,
        }]
        return response

    def _validate_twilio_signature_mocked(self, model, *args, **kwargs):
        return True

    @contextmanager
    def mock_sms_twilio_gateway(self):
        self.env.company.sudo().sms_provider = "twilio"  # Setting this needs admin mode

        self._clear_sms_sent()
        sms_create_origin = SmsSms.create

        def _sms_sms_create(model, *args, **kwargs):
            res = sms_create_origin(model, *args, **kwargs)
            self._new_sms += res.sudo()
            return res

        try:
            with (
                patch.object(SmsSms, 'create', autospec=True, wraps=SmsSms, side_effect=_sms_sms_create),
                patch.object(SmsApiTwilio, '_sms_twilio_send_request', autospec=True, side_effect=self._sms_twilio_send_request),
                patch.object(SmsTwilioController, '_validate_twilio_signature', autospec=True, side_effect=self._validate_twilio_signature_mocked),
            ):
                yield
        finally:
            pass


@tagged('post_install', '-at_install')
class TestSmsTwilio(MockSmsTwilioApi, SMSCase, common.TransactionCase):
    def test_send_to_valid_number(self):
        with self.mock_sms_twilio_gateway():
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': "Valid phone number"})
            composer._action_send_sms()
            self.assertSMS(
                self.valid_partner, self.valid_phone_number, "pending",
                failure_type=False,
                content="Valid phone number",
                fields_values={"to_delete": True},
            )

    def test_send_to_invalid_number(self):
        with self.mock_sms_twilio_gateway():
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.invalid_partner,
            ).create({'body': "Invalid phone number"})
            composer._action_send_sms()
            self.assertSMS(
                self.invalid_partner, self.invalid_phone_number, "error",
                failure_type="sms_number_format",
                content="Invalid phone number",
                fields_values={"to_delete": False},  # unlink_failed not set to True
            )

    def test_send_with_non_admin_user(self):
        with (
            self.with_user("demo"),
            self.mock_sms_twilio_gateway()
        ):
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': "Valid phone number"})
            composer._action_send_sms()
            self.assertSMS(
                self.valid_partner, self.valid_phone_number, "pending",
                failure_type=False,
                content="Valid phone number",
                fields_values={"to_delete": True},
            )

    def test_multi_company_diff_providers(self):
        """Test that in a multi company environement, where each company decides how it should send SMS, that we respect this choice"""
        company_twilio = self.env.company
        company_twilio.write({
            "name": "Company 1 (Twilio)",
            "sms_provider": "twilio",
        })
        company_iap = self.env['res.company'].create({
            'name': "Company 2 (IAP)",
            "sms_provider": "iap",
        })
        self.env.user.company_ids |= company_iap

        def patch_send(*args, **kwargs):
            pass  # Don't send so we can allow the cron to do its job (the SMS are therefore created but stay in outgoing state)

        with patch.object(SmsSms, 'send', autospec=True, wraps=SmsSms, side_effect=patch_send):
            self.valid_partner.company_id = company_twilio
            mail_msg_twilio = self.valid_partner._message_sms("SMS by Twilio")  # SMS will be linked to company of the partner (Twilio)
            sms_twilio = self.env['sms.sms'].sudo().search([], limit=1)  # Last one created
            self.valid_partner.company_id = company_iap
            mail_msg_iap = self.valid_partner._message_sms("SMS by IAP")  # SMS will be linked to company of the partner (IAP)
            sms_iap = self.env['sms.sms'].sudo().search([], limit=1)  # Last one created

        self.assertEqual(mail_msg_twilio.record_company_id, company_twilio)
        self.assertEqual(mail_msg_iap.record_company_id, company_iap)
        self.assertRecordValues(sms_twilio, [{"state": "outgoing", "body": "SMS by Twilio"}])
        self.assertRecordValues(sms_iap, [{"state": "outgoing", "body": "SMS by IAP"}])

        with (
            self.mockSMSGateway(),
            # Manually patch the necessary methods for Twilio instead of using the Twilio contextmanager
            # because it will conflict with IAP's since they patch the same methods
            patch.object(SmsApiTwilio, '_sms_twilio_send_request', autospec=True, side_effect=self._sms_twilio_send_request),
            patch.object(SmsTwilioController, '_validate_twilio_signature', autospec=True, side_effect=self._validate_twilio_signature_mocked),
        ):
            self.env['sms.sms'].sudo()._process_queue()  # Simulate cron

        self.assertRecordValues(sms_twilio, [{"state": "pending", "sms_twilio_sid": "SMfake"}])
        self.assertRecordValues(sms_iap, [{"state": "pending", "sms_twilio_sid": False}])


@tagged('post_install', '-at_install')
class TestSmsTwilioController(MockSmsTwilioApi, SMSCase, HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.webhook_ok_response = {
            'AccountSid': 'ACfake',
            'ApiVersion': '2010-04-01',
            'From': '+12212341234',
            'MessageSid': 'SMfake',
            'MessageStatus': 'delivered',
            'RawDlrDoneDate': '2504241615',
            'SmsSid': 'SMfake',
            'SmsStatus': 'delivered',
            'To': '+32486321321',
        }

    def test_sms_twilio_controller_ok(self):
        sms_content = "Valid phone number"
        with self.mock_sms_twilio_gateway():
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': sms_content})
            composer._action_send_sms()
            # The SMS is accepted by Twilio, so it should be in pending state in Odoo
            self.assertSMS(
                self.valid_partner, self.valid_phone_number, "pending",
                failure_type=False,
                content="Valid phone number",
                fields_values={"to_delete": True},
            )

            # Simulate callback webhook called by Twilio
            self.url_open(f"/sms_twilio/status/{self._new_sms[-1].uuid}", self.webhook_ok_response)
            self.assertTrue(self._new_sms[-1].to_delete)  # We don't check the state because it will be deleted anyway
            self.assertRecordValues(self._new_sms[-1].sms_tracker_id.mail_notification_id, [{
                'notification_status': 'sent',
                'failure_type': False,
                'failure_reason': False,
            }])

    def test_sms_twilio_controller_handled_error(self):
        """Test that we correctly handle known errors (the ones that we have mapped)"""
        webhook_nok_response = {
            **self.webhook_ok_response,
            "SmsStatus": "undelivered",
            "ErrorCode": 30005,
            "ErrorMessage": "Unknown destination handset",
        }
        with self.mock_sms_twilio_gateway():
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': "Body msg"})
            composer._action_send_sms()
            # The SMS is accepted by Twilio, so it should be in pending state in Odoo
            self.assertSMS(
                self.valid_partner, self.valid_phone_number, "pending",
                failure_type=False,
                content="Body msg",
                fields_values={"to_delete": True},
            )

            # However, it seems to not reach its destination, we simulate callback webhook called by Twilio
            self.url_open(f"/sms_twilio/status/{self._new_sms[-1].uuid}", webhook_nok_response)
            self.assertSMS(
                self.valid_partner, self.valid_phone_number, "pending",  # State pending and not error because it's not updated since we delete it anyway
                content="Body msg",
                fields_values={"to_delete": True},
            )
            self.assertRecordValues(self._new_sms[-1].sms_tracker_id.mail_notification_id, [{
                'notification_status': 'bounce',
                'failure_type': 'sms_invalid_destination',
                'failure_reason': 'Unknown destination handset',
            }])

    def test_sms_twilio_controller_unknown_error(self):
        """Test that we correctly handle unknown errors (the ones that we not have mapped)"""
        webhook_nok_response = {
            **self.webhook_ok_response,
            "SmsStatus": "failed",
            "ErrorCode": 12345,
            "ErrorMessage": "Unknown error",
        }
        with self.mock_sms_twilio_gateway():
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': "Body msg"})
            composer._action_send_sms()
            # The SMS is accepted by Twilio, so it should be in pending state in Odoo
            self.assertSMS(
                self.valid_partner, self.valid_phone_number, "pending",
                content="Body msg",
                fields_values={"to_delete": True},
            )

            # However, it seems that we receive an unknown error from the callback that we simualte here
            self.url_open(f"/sms_twilio/status/{self._new_sms[-1].uuid}", webhook_nok_response)
            self.assertTrue(self._new_sms[-1].to_delete)
            self.assertRecordValues(self._new_sms[-1].sms_tracker_id.mail_notification_id, [{
                'notification_status': 'exception',
                'failure_type': 'unknown',
                'failure_reason': 'Unknown error',
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
            self.mock_sms_twilio_gateway(),
        ):
            composer = self.env['sms.composer'].with_context(
                active_model='res.partner',
                active_id=self.valid_partner,
            ).create({'body': "Body msg"})
            composer._action_send_sms()
            # The SMS is accepted by Twilio, so it should be in pending state in Odoo
            self.assertSMS(
                self.valid_partner, self.valid_phone_number, "pending",
                content="Body msg",
                fields_values={"to_delete": True},
            )

            # Simulate callback webhook called by Twilio
            response = self.url_open(f"/sms_twilio/status/{self._new_sms[-1].uuid}", webhook_fake_response)
            self.assertEqual(response.status_code, 404)
            # SMS not updated
            self.assertRecordValues(self._new_sms[-1].sms_tracker_id.mail_notification_id, [{
                'notification_status': 'pending',
                'failure_type': False,
                'failure_reason': False,
            }])
