# Part of Odoo. See LICENSE file for full copyright and licensing details.

from zoneinfo import ZoneInfo

from odoo.tests import tagged
from odoo.tools import urls

from odoo.addons.payment_ecpay import const
from odoo.addons.payment_ecpay.tests.common import EcpayCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(EcpayCommon):
    def test_reference_uses_only_alphanumeric_chars(self):
        """The computed reference must be alphanumeric."""
        reference = self.env["payment.transaction"]._compute_reference(provider_code="ecpay")
        self.assertRegex(reference, r"^[a-zA-Z0-9]+$")

    def test_reference_length_is_at_most_20_chars(self):
        """The computed reference must be at most 20 characters long."""
        reference = self.env["payment.transaction"]._compute_reference(provider_code="ecpay")
        self.assertTrue(len(reference) <= 20)

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        # Create a transaction with known values
        localhost_url = "http://127.0.0.1:8069"
        self.env["ir.config_parameter"].set_param("web.base.url", localhost_url)

        tx = self._create_transaction(
            "redirect", payment_method_id=self.env.ref("payment.payment_method_card").id
        )
        # The ignored payment methods are computed from the mapping
        all_payment_methods = {
            item for methods in const.PAYMENT_METHODS_MAPPING.values() for item in methods
        }
        ignored_payment_methods = "#".join(
            all_payment_methods.difference(const.PAYMENT_METHODS_MAPPING[tx.payment_method_code])
        )
        expected_values = {
            "MerchantID": self.provider.ecpay_merchant_id,
            "MerchantTradeNo": tx.reference,
            "MerchantTradeDate": (
                tx.create_date
                .replace(tzinfo=ZoneInfo("UTC"))
                .astimezone(ZoneInfo("Asia/Taipei"))
                .strftime("%Y/%m/%d %H:%M:%S")
            ),
            "PaymentType": "aio",
            "TotalAmount": int(tx.amount),
            "TradeDesc": "ECPay from Odoo",
            "ItemName": tx.reference,
            "ReturnURL": urls.urljoin(localhost_url, const.WEBHOOK_ROUTE),
            "ChoosePayment": "ALL",
            "EncryptType": "1",
            "ClientBackURL": urls.urljoin(localhost_url, const.PAYMENT_RETURN_ROUTE),
            "OrderResultURL": urls.urljoin(localhost_url, const.PAYMENT_RETURN_ROUTE),
            "IgnorePayment": ignored_payment_methods,
            "Language": "ENG",
        }
        # The CheckMacValue must be computed using the provider's method
        expected_values["CheckMacValue"] = tx.provider_id._ecpay_calculate_signature(
            expected_values
        )
        expected_values["api_url"] = "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"
        self.assertEqual(tx._get_specific_rendering_values(None), expected_values)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction("redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "ecpay", self.payment_result_data
        )
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.payment_result_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' on successful payment."""
        tx = self._create_transaction("redirect")
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.provider_reference, self.payment_result_data["TradeNo"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.payment_method_id, self.env.ref("payment.payment_method_ipass_money"))
