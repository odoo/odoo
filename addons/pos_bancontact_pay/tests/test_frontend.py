import json
from contextlib import contextmanager
from unittest.mock import patch

from requests import Response

from odoo.tests.common import tagged

from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.tests.common import TestBancontactPay


# Keep the tour running even if an RPC error is raised
# e.g. we mock an error response from Bancontact API when creating a payment
def error_checker_bancontact_failed_rpc_request(message):
    return "RPC_ERROR" not in message


@tagged("post_install", "-at_install")
class TestFrontend(TestBancontactPay):

    def test_bancontact_can_send_request(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call():
            self.start_pos_tour("bancontact_pay_can_send_request")

    def test_bancontact_show_qr_code(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_bancontact_call(prefix="bancontact_show_qr_code_"):
            self.start_pos_tour("bancontact_pay_show_qr_code")

    @contextmanager
    def mock_bancontact_call(self, prefix="bancontact_", post_status_code=200, delete_status_code=200):
        counter = {"post": -1}

        def mock_post(url, **kwargs):
            counter["post"] += 1
            response = Response()

            if "merchant.api.preprod.bancontact.net/v3/payments" not in url:
                response.status_code = 404
                return response

            if 200 <= post_status_code < 300:
                response._content = json.dumps(
                    {
                        "paymentId": prefix + str(counter["post"]),
                        "_links": {"qrcode": {"href": "https://example.com/bancontact_qrcode"}},
                    },
                ).encode()

            response.status_code = post_status_code
            return response

        def mock_delete(url, **kwargs):
            response = Response()
            if "merchant.api.preprod.bancontact.net/v3/payments" not in url:
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
