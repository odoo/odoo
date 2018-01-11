# -*- coding: utf-8 -*-

from odoo.addons.account.tests.test_payment import TestPayment

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestAccountFlow(TestPayment):
    def test_invoice_state_flow(self):
        invoice = self.create_invoice(amount=200.0)

        acquirer = self.env['payment.acquirer'].search([], limit=1)

        transaction = self.env['payment.transaction'].create({
            'amount': 200.0,
            'acquirer_id': acquirer.id,
            'currency_id': invoice.currency_id.id,
            'partner_id': invoice.partner_id.id,
            'reference': invoice.number,
            'invoice_ids': [(6, 0, invoice.ids)],
        })

        transaction.post()

        self.assertEqual(transaction.state, 'posted')
        self.assertEqual(invoice.state, 'paid')
