from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.addons.mail.tests.common import mail_new_test_user

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


class MockSmsTwilioApi(TransactionCase):
    """
    This test takes inspiration from sms/tests/{common,test_sms_composer}
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.basic_user = mail_new_test_user(cls.env, login='user_employee', groups='base.group_user')

        cls.twilio_valid_phone_number = "+12202154155"
        cls.twilio_invalid_phone_number = "+3212312312"
        cls.valid_partner = cls.env['res.partner'].create({
            'name': 'ValidPartner',
            'phone': cls.twilio_valid_phone_number,
        })
        cls.invalid_partner = cls.env['res.partner'].create({
            'name': 'InvalidPartner',
            'phone': cls.twilio_invalid_phone_number,
        })

        cls.webhook_ok_response = {
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

    def setUp(self):
        super().setUp()
        self = self.with_user(self.basic_user)  # noqa: PLW0642

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
        if to_number == self.twilio_invalid_phone_number:
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
    def setup_and_mock_sms_twilio_gateway(self):
        self.env.company.sudo().sms_provider = "twilio"  # Setting this needs admin mode

        self._clear_sms_sent()
        sms_create_origin = SmsSms.create

        def _sms_sms_create(model, *args, **kwargs):
            res = sms_create_origin(model, *args, **kwargs)
            self._new_sms += res.sudo()
            return res

        with (
            patch.object(SmsSms, 'create', autospec=True, wraps=SmsSms, side_effect=_sms_sms_create),
            patch.object(SmsApiTwilio, '_sms_twilio_send_request', autospec=True, side_effect=self._sms_twilio_send_request),
            patch.object(SmsTwilioController, '_validate_twilio_signature', autospec=True, side_effect=self._validate_twilio_signature_mocked),
        ):
            yield
