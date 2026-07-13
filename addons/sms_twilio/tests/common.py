import re

from contextlib import contextmanager
from requests import Response
from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sms.models.sms_sms import SmsSms
from odoo.addons.sms.tests.common import SMSCase
from odoo.addons.sms_twilio.tools import sms_twilio as twilio_tools
from odoo.addons.sms_twilio.tools.sms_api import SmsApiTwilio
from odoo.tests.common import TransactionCase


class MockSmsTwilioApi(SMSCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # some test data
        cls.twilio_valid_phone_number = "+12202154155"
        cls.twilio_invalid_phone_number = "+3212312312"

        # mock control
        cls.mock_error_type = False
        cls.mock_error_number_to_type = {}
        cls.mock_body = False
        if cls.env:  # in 17, classes is quite a bordel
            cls.mock_company = cls.env.company
        cls.mock_number = False
        cls.mock_sms_uuid = 'NA'

        # find details of outgoing requests
        cls.twilio_request_re = re.compile(r"https://api.twilio.com/2010-04-01/Accounts/(AC[\d]{32})/(.*)")

        # typical / expected responses
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
        cls.request_send_ok_json = {
            "account_sid": "AC12345678987654321234567898765432",
            "api_version": "2010-04-01",
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
            "uri": "/2010-04-01/Accounts/ACfake/Messages/SMfake.json",
        }
        cls.request_send_nok_json = {
            'code': 21211,
            'more_info': 'https://www.twilio.com/docs/errors/21211',
            'status': 400,
        }

    @classmethod
    def _request_handler(cls, session, request, **kwargs):
        url = request.url
        matching = cls.twilio_request_re.match(url)
        if matching:
            _sid = matching.group(1)
            right_part = matching.group(2)
            response = Response()
            response.status_code = 200
            if right_part == "IncomingPhoneNumbers.json":
                response.json = lambda: {
                    'incoming_phone_numbers': [
                        {'phone_number': '+32455998877'},
                        {'phone_number': '+32455665544'},
                    ],
                }
                return response
            elif right_part == "Messages.json":
                error_type = cls.mock_error_number_to_type.get(cls.mock_number) or cls.mock_error_type
                if not error_type and not cls.mock_number:
                    error_type = "sms_number_missing"
                error_codes = {
                    'wrong_number_format': 21211,
                    'sms_number_missing': 21604,
                    'twilio_acc_unverified': 21608,
                    'twilio_callback': 21609,
                    'unknown': 1,
                    'other': 1,
                }
                if not error_type:
                    request_send_ok_json = cls.request_send_ok_json.copy()
                    request_send_ok_json['body'] = cls.mock_body or 'body'
                    request_send_ok_json['sid'] = f'twilio_{cls.mock_company.name}_{cls.mock_sms_uuid}' if cls.mock_sms_uuid else 'SMFake'
                    request_send_ok_json['to_number'] = cls.mock_number or 'to_number'
                    response.json = lambda: request_send_ok_json
                else:
                    if error_type not in error_codes:
                        raise ValueError('Unsupported error code')
                    error_code = error_codes.get(error_type) if error_type else False

                    request_send_nok_json = cls.request_send_nok_json.copy()
                    request_send_nok_json['body'] = cls.mock_body or 'body'
                    request_send_nok_json['code'] = error_code
                    request_send_nok_json['to_number'] = cls.mock_number or 'to_number'
                    response.json = lambda: request_send_nok_json
                    response.status_code = 400
                return response
        return super()._request_handler(session, request, **kwargs)

    @classmethod
    def _setup_sms_twilio(cls, company):
        company.sudo().write({
            "sms_provider": "twilio",
            "sms_twilio_account_sid": "AC12345678987654321234567898765432",
            "sms_twilio_auth_token": "grimgorironhide",
            "sms_twilio_number_ids": [
                (5, 0),
                (0, 0, {
                    "country_id": cls.env.ref("base.be").id,
                    "number": "+32455998877",
                    "sequence": 0,
                }),
                (0, 0, {
                    "country_id": cls.env.ref("base.us").id,
                    "number": "+15056998877",
                    "sequence": 1,
                }),
            ],
        })

    @classmethod
    def _update_mock(cls, error_type=None, error_number_to_type=None,
                     body=None, number=False, sms_uuid=False,
                     company=False):
        if error_type is not None:
            cls.mock_error_type = error_type
        if error_number_to_type is not None:
            cls.mock_error_number_to_type = error_number_to_type
        # various data, used notably to forge better simulated responses
        if body is not None:
            cls.mock_body = body
        if company is not False:
            cls.mock_company = company
        if number is not False:
            cls.mock_number = number
        if sms_uuid is not False:
            cls.mock_sms_uuid = sms_uuid

    @contextmanager
    def mock_sms_twilio_send(self, error_type=False, error_number_to_type=None):
        self._clear_sms_sent()
        self._update_mock(
            error_type=error_type,
            error_number_to_type=error_number_to_type,
            company=self.env.company,
        )
        sms_twilio_send_request_origin = SmsApiTwilio._sms_twilio_send_request

        def _sms_api_twilio_sms_twilio_send_request(model, *args, **kwargs):
            (_session, to_number, body, uuid) = args
            self._update_mock(
                error_type=self.mock_error_type,
                error_number_to_type=self.mock_error_number_to_type,
                body=body, number=to_number, sms_uuid=uuid,
                company=model.company,
            )
            res = sms_twilio_send_request_origin(model, *args, **kwargs)
            self._sms += [{
                'body': body,
                'number': to_number,
                'uuid': uuid,
            }]
            return res

        with patch.object(SmsApiTwilio, '_sms_twilio_send_request', autospec=True, side_effect=_sms_api_twilio_sms_twilio_send_request) as _sms_twilio_send_mock:
            self._sms_twilio_send_mock = _sms_twilio_send_mock
            yield

    @contextmanager
    def mock_sms_twilio_gateway(self, error_type=False, error_number_to_type=None):
        self._clear_sms_sent()
        sms_create_origin = SmsSms.create

        def _sms_sms_create(model, *args, **kwargs):
            res = sms_create_origin(model, *args, **kwargs)
            self._new_sms += res.sudo()
            return res

        with (
            patch.object(SmsSms, 'create', autospec=True, wraps=SmsSms, side_effect=_sms_sms_create),
            self.mock_sms_twilio_send(error_type=error_type, error_number_to_type=error_number_to_type),
        ):
            yield

    def simulate_sms_twilio_status(self, sms_batch, company):
        """ Simulate callback webhook called by Twilio """
        for sms in sms_batch:
            expected_signature = twilio_tools.generate_twilio_sms_callback_signature(
                self.user_admin.company_id,
                sms.uuid,
                self.webhook_ok_response,
            )
            _response = self.url_open(
                f"/sms_twilio/status/{sms.uuid}", self.webhook_ok_response,
                headers={
                    "X-Twilio-Signature": expected_signature,
                },
            )


class MockSmsTwilio(MockSmsTwilioApi, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_admin = cls.env.ref('base.user_admin')
        cls.company_admin = cls.user_admin.company_id
        cls.basic_user = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            country_id=cls.env.ref('base.be').id,
            groups='base.group_user,base.group_partner_manager',
            login='employee',
        )

        cls.valid_partner = cls.env['res.partner'].create({
            'name': 'ValidPartner',
            'phone': cls.twilio_valid_phone_number,
        })
        cls.invalid_partner = cls.env['res.partner'].create({
            'name': 'InvalidPartner',
            'phone': cls.twilio_invalid_phone_number,
        })
