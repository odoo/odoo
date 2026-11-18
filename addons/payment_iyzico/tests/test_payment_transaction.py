# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.urls import url_encode

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_iyzico import const
from odoo.addons.payment_iyzico.tests.common import IyzicoCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(IyzicoCommon, PaymentHttpCommon):
    def test_no_item_missing_from_cf_initialize_payload(self):
        """Test that the request values are conform to the transaction fields."""
        tx = self._create_transaction("redirect")
        request_payload = tx._iyzico_prepare_cf_initialize_payload()
        first_name, last_name = payment_utils.split_partner_name(tx.partner_name)
        return_url = self._build_url(
            f"{const.PAYMENT_RETURN_ROUTE}?{url_encode({'tx_ref': tx.reference})}"
        )
        self.assertDictEqual(
            request_payload,
            {
                "basketItems": [
                    {
                        "id": tx.id,
                        "price": tx.amount,
                        "name": "Odoo purchase",
                        "category1": "Service",
                        "itemType": "VIRTUAL",
                    }
                ],
                "billingAddress": {
                    "address": tx.partner_address,
                    "contactName": tx.partner_name,
                    "city": tx.partner_city,
                    "country": tx.partner_country_id.name,
                },
                "buyer": {
                    "id": tx.partner_id.id,
                    "name": first_name,
                    "surname": last_name,
                    "identityNumber": str(tx.partner_id.id).zfill(5),
                    "email": tx.partner_email,
                    "registrationAddress": tx.partner_address,
                    "city": tx.partner_city,
                    "country": tx.partner_country_id.name,
                    "ip": "0",
                },
                "callbackUrl": return_url,
                "basketId": tx.reference,
                "currency": tx.currency_id.name,
                "locale": "tr" if tx.env.lang == "tr_TR" else "en",
                "paidPrice": tx.amount,
                "paymentSource": "ODOO",
                "price": tx.amount,
            },
        )

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment_iyzico.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={"api_url": "https://dummy.com", "http_method": "get", "url_param": {}},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "get")
        self.assertDictEqual(form_info["inputs"], {})

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction(flow="redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "iyzico", {"reference": tx.reference}
        )
        self.assertEqual(tx.reference, reference)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is set when processing the payment data."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, self.payment_data["paymentId"])

    def test_apply_updates_sets_card_payment_method(self):
        """Test that the card payment method brand is updated from the payment data."""
        self.payment_data.update({"cardType": "CREDIT_CARD", "cardAssociation": "MASTER_CARD"})
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.payment_method_id.code, "mastercard")

    def test_apply_updates_sets_bank_transfer_payment_method(self):
        """Test that the bank transfer payment method is set if found in the payment data."""
        self.payment_data.update({"bankName": "dummy"})
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.payment_method_id.code, "bank_transfer")

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_fails_transaction(self):
        """Test that the transaction state is set to 'error' when the payment data indicate a
        payment failure."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates({"paymentStatus": "FAILURE"})
        self.assertEqual(tx.state, "error")

    def test_basket_items_payload_with_quantities_in_names(self):
        """Test that the basket items are sent with their line totals, and their quantity in their
        name."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=38.5)
        line_items = {
            "chair": {"name": "Chair", "description": "", "quantity": 2, "total": 23.0},
            "desk": {"name": "Desk", "description": "", "quantity": 1, "total": 10.0},
            "fabric": {"name": "Fabric", "description": "", "quantity": 1.5, "total": 5.5},
        }
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            basket_items = tx._iyzico_prepare_basket_items_payload()
        self.assertListEqual(
            [(item["id"], item["name"], item["price"]) for item in basket_items],
            [("1", "2 x Chair", 23.0), ("2", "Desk", 10.0), ("3", "1.5 x Fabric", 5.5)],
        )

    def test_basket_items_payload_skips_free_items(self):
        """Test that free items are not sent, as Iyzico rejects them."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=10.0)
        line_items = {
            "desk": {"name": "Desk", "description": "", "quantity": 1, "total": 10.0},
            "delivery": {"name": "Free delivery", "description": "", "quantity": 1, "total": 0.0},
        }
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            basket_items = tx._iyzico_prepare_basket_items_payload()
        self.assertListEqual([item["name"] for item in basket_items], ["Desk"])

    def _assert_default_basket_items(self, tx, line_items):
        PaymentTransaction = self.env.registry["payment.transaction"]
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            basket_items = tx._iyzico_prepare_basket_items_payload()
        self.assertListEqual(
            basket_items,
            [
                {
                    "id": tx.id,
                    "price": tx.amount,
                    "name": "Odoo purchase",
                    "category1": "Service",
                    "itemType": "VIRTUAL",
                }
            ],
        )

    def test_default_basket_items_with_negative_line(self):
        """Test that a single item is sent for the whole amount when a line item is negative."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_basket_items(
            tx,
            {
                "line": {"name": "Desk", "description": "", "quantity": 1, "total": 20.0},
                "discount": {"name": "Promo", "description": "", "quantity": 1, "total": -5.0},
            },
        )

    def test_default_basket_items_with_nameless_line(self):
        """Test that a single item is sent for the whole amount when a line item has no name."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_basket_items(
            tx, {"line": {"name": "", "description": "", "quantity": 1, "total": 15.0}}
        )

    def test_default_basket_items_for_partial_payment(self):
        """Test that a single item is sent for the whole amount when the line items do not add up
        to the transaction amount."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_basket_items(
            tx, {"line": {"name": "Desk", "description": "", "quantity": 1, "total": 20.0}}
        )

    def test_default_basket_items_without_line_items(self):
        """Test that a single item is sent for the whole amount when there are no line items."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_basket_items(tx, {})
