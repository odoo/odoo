# Part of Odoo. See LICENSE file for full copyright and licensing details.
import unittest

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentTransaction(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if 'product.product' not in cls.env:
            raise unittest.SkipTest("requires product")

        cls.provider = cls._prepare_provider(code='custom')
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
