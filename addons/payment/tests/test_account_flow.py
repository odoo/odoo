# -*- coding: utf-8 -*-

from odoo.addons.account.tests.test_payment import TestPayment

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestAccountFlow(TestPayment):
    def test_invoice_state_flow(self):
        invoice = self.create_invoice(amount=200.0)

        acquirer = self.env['payment.acquirer'].search([], limit=1)

        transaction = invoice.create_payment_transaction({'acquirer_id': acquirer.id})

        transaction._set_transaction_posted()

        self.assertEqual(transaction.state, 'posted')
        self.assertEqual(invoice.state, 'paid')
