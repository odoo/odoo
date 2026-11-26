# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from urllib.parse import quote as url_quote

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(MercadoPagoCommon, PaymentHttpCommon):
    def test_no_item_missing_from_preference_request_payload(self):
        """Test that the request values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")
        request_payload = tx._mercado_pago_prepare_preference_request_payload()
        self.maxDiff = 10000  # Allow comparing large dicts.
        return_url = self._build_url("/payment/mercado_pago/return")
        webhook_url = self._build_url("/payment/mercado_pago/webhook")
        sanitized_reference = url_quote(tx.reference)
        self.assertDictEqual(
            request_payload,
            {
                "external_reference": tx.reference,
                "notification_url": f"{webhook_url}/{sanitized_reference}",
                "statement_descriptor": tx.company_id.name,
                "auto_return": "all",
                "back_urls": {"failure": return_url, "pending": return_url, "success": return_url},
                "items": [
                    {
                        "currency_id": tx.currency_id.name,
                        "quantity": 1,
                        "title": tx.reference,
                        "unit_price": tx.amount,
                    }
                ],
                "payer": {
                    "name": tx.partner_name,
                    "email": tx.partner_email,
                    "phone": {"number": tx.partner_phone},
                    "address": {"street_name": tx.partner_address, "zip_code": tx.partner_zip},
                },
            },
        )

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        with patch(
            "odoo.addons.payment_mercado_pago.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={"api_url": "https://dummy.com", "http_method": "get", "url_param": {}},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "get")
        self.assertDictEqual(form_info["inputs"], {})

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.verification_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_mercado_pago.models.payment_transaction")
    def test_apply_updates_rejects_transaction(self):
        """Test that the transaction state is set to 'error' when the payment data indicate a status
        of 404 error payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(
            self.verification_data_for_error_state
        )
        self.assertEqual(tx.state, "error")

    def test_cop_currency_rounding(self):
        """Ensure COP payments get sent as integer amounts to Mercado Pago."""
        self.currency = (
            self
            .env["res.currency"]
            .with_context(active_test=False)
            .search([("name", "=", "COP")], limit=1)
        )
        self.amount = 999.99
        tx = self._create_transaction(flow="redirect")
        request_payload = tx._mercado_pago_prepare_preference_request_payload()
        self.assertEqual(
            request_payload["items"][0]["unit_price"],
            999,
            "COP payment amounts should be rounded down in the payload sent to Mercado Pago",
        )

    def test_items_payload_with_taxes_included_unit_prices(self):
        """Test that the items are sent with their taxes included unit prices."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=23.0)
        line_items = {
            "line": {
                "name": "Chair",
                "description": "Oak chair",
                "quantity": 2,
                "total": 23.0,
                "image_url": "https://example.com/chair.png",
            }
        }
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            items = tx._mercado_pago_prepare_items_payload()
        self.assertListEqual(
            items,
            [
                {
                    "title": "Chair",
                    "quantity": 2,
                    "unit_price": 11.5,
                    "description": "Oak chair",
                    "picture_url": "https://example.com/chair.png",
                }
            ],
        )

    def test_items_payload_falls_back_to_single_quantity(self):
        """Test that an item with a fractional quantity is sent with a quantity of 1."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=10.0)
        line_items = {"line": {"name": "Desk", "description": "", "quantity": 1.5, "total": 10.0}}
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            item = tx._mercado_pago_prepare_items_payload()[0]
        self.assertEqual((item["quantity"], item["unit_price"]), (1, 10.0))

    def test_items_payload_skips_non_https_images(self):
        """Test that the image is only sent if it is served over HTTPS."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=10.0)
        line_items = {
            "line": {
                "name": "Desk",
                "description": "",
                "quantity": 1,
                "total": 10.0,
                "image_url": "http://example.com/desk.png",
            }
        }
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            item = tx._mercado_pago_prepare_items_payload()[0]
        self.assertNotIn("picture_url", item)

    def _assert_default_items(self, tx, line_items):
        PaymentTransaction = self.env.registry["payment.transaction"]
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            items = tx._mercado_pago_prepare_items_payload()
        self.assertListEqual(
            items, [{"title": tx.reference, "quantity": 1, "unit_price": tx.amount}]
        )

    def test_default_items_with_negative_line(self):
        """Test that a single item is sent for the whole amount when a line item is negative."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_items(
            tx,
            {
                "line": {"name": "Desk", "description": "", "quantity": 1, "total": 20.0},
                "discount": {"name": "Promo", "description": "", "quantity": 1, "total": -5.0},
            },
        )

    def test_default_items_with_nameless_line(self):
        """Test that a single item is sent for the whole amount when a line item has no name."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_items(
            tx, {"line": {"name": "", "description": "", "quantity": 1, "total": 15.0}}
        )

    def test_default_items_for_partial_payment(self):
        """Test that a single item is sent for the whole amount when the line items do not add up
        to the transaction amount."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_items(
            tx, {"line": {"name": "Desk", "description": "", "quantity": 1, "total": 20.0}}
        )

    def test_default_items_without_line_items(self):
        """Test that a single item is sent for the whole amount when there are no line items."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_items(tx, {})

    def test_extract_amount_data_sums_items(self):
        """Test that the amount of a redirect payment is the sum of its items."""
        tx = self._create_transaction(flow="redirect", amount=362.99)
        payment_data = {
            "currency_id": tx.currency_id.name,
            "additional_info": {
                "items": [
                    {"title": "Desk", "quantity": "2", "unit_price": "121.00"},
                    {"title": "Chair", "quantity": "3", "unit_price": "40.33"},
                ]
            },
        }
        self.assertAlmostEqual(tx._extract_amount_data(payment_data)["amount"], 362.99)
