import time

from requests import Response
from unittest.mock import patch

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestRazorPayPoS(TestPointOfSaleHttpCommon):
    external_ref_number = ""
    is_cancel_payment_test = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.currency_id = cls.env.ref("base.INR")
        cls.main_pos_config.use_pricelist = False
        payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "RazorPay",
                "payment_method_type": "terminal",
                "use_payment_terminal": "razorpay",
                "razorpay_tid": "my_razorpay_device_serial_no",
                "razorpay_allowed_payment_modes": "card",
                "razorpay_username": "my_razorpay_username",
                "razorpay_api_key": "my_razorpay_api_key",
                "razorpay_test_mode": True,
                "journal_id": cls.bank_journal.id,
            }
        )
        cls.main_pos_config.write({"payment_method_ids": [(4, payment_method.id)]})

    def _on_razorpay_payment_line_added(self, response, **kwargs):
        json_data = kwargs.get("json", {})
        if not json_data or "externalRefNumber" not in json_data:
            response.json = lambda: {
                "success": False,
                "errorCode": "EZETAP_0000387",
                "errorMessage": "`externalRefNumber` field is empty.",
            }
            return response

        response.json = lambda: {
            "success": True,
            "p2pRequestId": "250102070607078E010040377",
        }
        return json_data.get("externalRefNumber")

    def _is_origP2pRequestId_present(self, json_data, response):
        if not json_data or "origP2pRequestId" not in json_data:
            response.json = lambda: {
                "success": False,
                "errorCode": "MISSING_REQUIRED_PARAMETER",
                "errorMessage": "The 'origP2pRequestId' field is required in the JSON payload.",
            }
            return response

    def _send_status_response(self, response: Response, **kwargs):
        json_data = kwargs.get("json", {})
        res = self._is_origP2pRequestId_present(json_data, response)
        if res:
            return res
        if self.is_cancel_payment_test:
            response.json = lambda: {
                "success": True,
                "messageCode": "P2P_DEVICE_RECEIVED",
            }
        else:
            response.json = lambda: {
                "success": True,
                "status": "AUTHORIZED",
                "messageCode": "P2P_DEVICE_TXN_DONE",
                "authCode": "D12345",
                "cardLastFourDigit": "1234",
                "externalRefNumber": self.external_ref_number,
                "reverseReferenceNumber": "RR6A55BBEA34E2",
                "txnId": "250102070624795E020088174",
                "paymentMode": "CARD",
                "paymentCardBrand": "VISA",
                "paymentCardType": "DEBIT",
                "nameOnCard": "John Doe",
                "acquirerCode": "HDFC",
                "createdTime": int(time.time() * 1000),
                "p2pRequestId": json_data.get("origP2pRequestId"),
                "settlementStatus": "PENDING",
            }

    def _cancel_response(self, response: Response, **kwargs):
        res = self._is_origP2pRequestId_present(kwargs.get("json", {}), response)
        if res:
            return res
        response.json = lambda: {"success": True}

    def _refund_response(self, response: Response, **kwargs):
        response.json = lambda: {
            "success": True,
            "authCode": "D12345",
            "cardLastFourDigit": "1234",
            "externalRefNumber": self.external_ref_number,
            "txnId": "250102070624795E020088174",
            "paymentMode": "CARD",
            "paymentCardBrand": "VISA",
            "paymentCardType": "DEBIT",
            "nameOnCard": "John Doe",
            "acquirerCode": "HDFC",
            "postingDate": int(time.time() * 1000),
        }

    def _not_found_response(self, response: Response):
        response.status_code = 404
        response.json = lambda: {
            "success": False,
            "errorCode": "ERR404",
            "errorMessage": "Endpoint not found",
        }

    def _mock_post(self, url, **kwargs):
        response = Response()
        response.status_code = 200
        response._content = "ok"

        if url == "https://demo.ezetap.com/api/3.0/p2padapter/pay":
            self.external_ref_number = self._on_razorpay_payment_line_added(response, **kwargs)

        elif url == "https://demo.ezetap.com/api/3.0/p2padapter/status":
            self._send_status_response(response, **kwargs)
            self.is_cancel_payment_test = False

        elif url == "https://demo.ezetap.com/api/3.0/p2padapter/cancel":
            self._cancel_response(response, **kwargs)

        elif url == "https://demo.ezetap.com/api/2.0/payment/void":
            self._refund_response(response, **kwargs)

        else:
            self._not_found_response(response)

        return response

    def test_razorpay_basic_order(self):
        with patch("odoo.addons.pos_razorpay.models.razorpay_pos_request.requests.Session.post", self._mock_post):
            self.start_pos_tour("PosRazorpayTour")

    def test_razorpay_cancel_payment(self):
        self.is_cancel_payment_test = True

        with patch("odoo.addons.pos_razorpay.models.razorpay_pos_request.requests.Session.post", self._mock_post):
            self.start_pos_tour("PosRazorpayCancelTour")

    def test_razorpay_refund_order(self):
        with patch("odoo.addons.pos_razorpay.models.razorpay_pos_request.requests.Session.post", self._mock_post):
            self.start_pos_tour("PosRazorpayRefundTour")
