# Part of Odoo. See LICENSE file for full copyright and licensing details.
import unittest

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment_custom.controllers.main import CustomController
from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


@tagged("-at_install", "post_install")
class TestPaymentTransaction(PaymentCustomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "product.product" not in cls.env:
            msg = "requires product"
            raise unittest.SkipTest(msg)

        cls.product = cls.env["product.product"].create({
            "name": "test product",
            "list_price": cls.amount,
        })

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")

        expected_values = {
            "api_url": CustomController._process_url,
            "url_params": {"reference": tx.reference},
        }

        self.assertEqual(tx._get_specific_rendering_values(None), expected_values)

    def test_no_input_missing_from_redirect_form(self):
        """Test that the no key is not omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], CustomController._process_url)
        self.assertEqual(form_info["method"], "post")
        self.assertDictEqual(form_info["inputs"], {"reference": tx.reference})

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(
            "redirect",
            provider_id=self.pay_on_invoice_provider.id,
            payment_method_id=self.pay_on_invoice_provider.payment_method_ids[:1].id,
        )
        tx.with_context(payment_safe_write=True)._apply_updates(None)
        self.assertEqual(tx.state, "done")

    def test_communication_based_on_transaction_reference(self):
        """Test that the payment communication falls back to the transaction reference when there
        is no linked invoice or sales order."""
        tx = self._create_transaction(flow="direct", reference="Test Transaction Reference")

        self.assertEqual(tx._get_communication(), "Test Transaction Reference")

    def test_communication_for_invoice_returns_invoice_reference(self):
        """Test that the communication displayed is the invoice payment reference."""
        account_payment_module = self.env["ir.module.module"]._get("account_payment")
        if account_payment_module.state != "installed":
            self.skipTest("account_payment module is not installed")

        invoice = self.env["account.move"].create({  # noqa: OLS03001
            "move_type": "in_invoice",
            "partner_id": self.partner.id,
            "invoice_date": fields.Date.from_string("2019-01-01"),
            "currency_id": self.currency.id,
            "invoice_line_ids": [Command.create({"product_id": self.product.id, "quantity": 1})],
        })
        invoice.action_post()
        tx = self._create_transaction(flow="direct", invoice_ids=[invoice.id])

        invoice.payment_reference = "Test Invoice Reference"
        self.assertEqual(tx._get_communication(), "Test Invoice Reference")

    def test_communication_for_sale_order_returns_sale_order_reference(self):
        """Test that the communication displayed is the sale order reference."""
        sale_module = self.env["ir.module.module"]._get("sale")
        if sale_module.state != "installed":
            self.skipTest("sale module is not installed")

        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
        })
        sale_order.action_confirm()
        tx = self._create_transaction(flow="direct", sale_order_ids=[sale_order.id])

        sale_order.reference = "Test Sale Order Reference"
        self.assertEqual(tx._get_communication(), "Test Sale Order Reference")
