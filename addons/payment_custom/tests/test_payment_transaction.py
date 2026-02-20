# Part of Odoo. See LICENSE file for full copyright and licensing details.
import unittest

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment_custom.tests.common import PaymentCustomCommon


@tagged('-at_install', 'post_install')
class TestPaymentTransaction(PaymentCustomCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'product.product' not in cls.env:
            raise unittest.SkipTest("requires product")

        cls.provider = cls._prepare_provider(code='custom', custom_mode='wire_transfer')
        cls.product = cls.env['product.product'].create({
            'name': "test product", 'list_price': cls.amount
        })

    def test_communication_based_on_transaction_reference(self):
        """ Test that the payment communication falls back to the transaction reference when there
        is no linked invoice or sales order. """
        tx = self._create_transaction(flow='direct', reference="test")

        self.assertEqual(tx._get_communication(), "test")

    def test_communication_for_invoice(self):
        """ Test that the communication displayed is the invoice payment reference. """
        account_payment_module = self.env['ir.module.module']._get('account_payment')
        if account_payment_module.state != 'installed':
            self.skipTest("account_payment module is not installed")

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product.id, 'quantity': 1})],
        })
        invoice.action_post()
        tx = self._create_transaction(flow='direct', invoice_ids=[invoice.id])

        invoice.payment_reference = "test"
        self.assertEqual(tx._get_communication(), "test")

    def test_communication_for_sale_order(self):
        """ Test that the communication displayed is the sale order reference. """
        sale_module = self.env['ir.module.module']._get('sale')
        if sale_module.state != 'installed':
            self.skipTest("sale module is not installed")

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_uom_qty': 1})],
        })
        sale_order.action_confirm()
        tx = self._create_transaction(flow='direct', sale_order_ids=[sale_order.id])

        sale_order.reference = "test"
        self.assertEqual(tx._get_communication(), "test")

    def test_matching_statement_line_confirms_wire_transfer_transaction(self):
        """Test that wire transfer transactions are confirmed when a matching bank statement line
        is found."""
        tx = self._create_transaction(
            flow='direct', reference="S00099", state='pending', currency_id=self.currency_usd.id,
        )
        tx.payment_method_id.code = 'wire_transfer'
        absl = self.env['account.bank.statement.line'].create({
            'payment_ref': tx.reference,
            'partner_id': self.partner.id,
            'amount': tx.amount,
        })
        absl._cron_confirm_wire_transfer_transactions()
        self.assertEqual(tx.state, 'done')

    def test_non_matching_statement_line_does_not_confirm_wire_transfer_transaction(self):
        """Test that wire transfer transactions are not confirmed with a non-matching bank statement
        line."""
        tx = self._create_transaction(
            flow='direct', reference="S00099", state='pending', currency_id=self.currency_usd.id,
        )
        tx.payment_method_id.code = 'wire_transfer'
        absl = self.env['account.bank.statement.line'].create({
            'payment_ref': 'S00098',  # non-matching reference
            'partner_id': self.partner.id,
            'amount': tx.amount,
        })
        absl._cron_confirm_wire_transfer_transactions()
        self.assertEqual(tx.state, 'pending')
