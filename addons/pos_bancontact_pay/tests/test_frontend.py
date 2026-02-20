import json
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from requests import Response

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.tests.common import TestBancontactPay


# Keep the tour running even if an RPC error is raised
# e.g. we mock an error response from Bancontact API when creating a payment
def error_checker_bancontact_failed_rpc_request(message):
    return "RPC_ERROR" not in message


@tagged("post_install", "-at_install")
class TestFrontend(TestBancontactPay):

    @mute_logger("odoo.http")
    def test_bancontact_failed_to_create_payment(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with (self.mock_bancontact_call(post_status_code=401)):
            self.start_pos_tour("bancontact_pay_failed_to_create_payment", error_checker=error_checker_bancontact_failed_rpc_request)

    def test_bancontact_can_send_request(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call():
            self.start_pos_tour("bancontact_pay_can_send_request")

    def test_bancontact_show_qr_code(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call():
            self.start_pos_tour("bancontact_pay_show_qr_code")

    def test_bancontact_success_payment(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call():
            self.start_pos_tour("bancontact_pay_success_payment")

    def test_bancontact_failed_payment(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call():
            self.start_pos_tour("bancontact_pay_failed_payment")

    @mute_logger("odoo.http")
    def test_bancontact_failed_to_cancel_payment_error_422(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call(delete_status_code=422):
            self.start_pos_tour("bancontact_pay_failed_to_cancel_payment_error_422")

    @mute_logger("odoo.http")
    def test_bancontact_failed_to_cancel_payment_error_429(self):
        # It could be any other error code different than 422
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call(delete_status_code=429):
            self.start_pos_tour("bancontact_pay_failed_to_cancel_payment_error_429")

    @contextmanager
    def mock_bancontact_call(self, is_sticker=False, post_status_code=200, delete_status_code=200):
        def mock_post(url, **kwargs):
            response = Response()

            if (not is_sticker and "merchant.api.preprod.bancontact.net/v3/payments" not in url) or \
               (is_sticker and "merchant.api.preprod.bancontact.net/v3/payments/pos" not in url):
                response.status_code = 404
                return response

            if 200 <= post_status_code < 300:
                payment_id = "bancontact_" + str(uuid.uuid4())
                response._content = json.dumps(
                    {
                        "paymentId": payment_id,
                        "_links": {"qrcode": {"href": "https://example.com/bancontact_qrcode"}},
                    },
                ).encode()

            response.status_code = post_status_code
            return response

        def mock_delete(url, **kwargs):
            response = Response()
            if "merchant.api.preprod.bancontact.net/v3/payments/" not in url:
                response.status_code = 404
                return response

            response.status_code = delete_status_code
            return response

        with (patch("odoo.addons.pos_bancontact_pay.models.pos_payment_method.requests.post", mock_post),
              patch("odoo.addons.pos_bancontact_pay.models.pos_payment_method.requests.delete", mock_delete),
              patch("odoo.addons.pos_bancontact_pay.controllers.signature.BancontactSignatureValidation")
                as bancontact_signature_validation_mock):
            instance = bancontact_signature_validation_mock.return_value
            instance.test_mode = True
            instance.bancontact_api_urls = const.API_URLS["preprod"]

            yield
