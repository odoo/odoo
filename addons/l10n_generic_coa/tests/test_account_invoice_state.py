# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestAccountInvoiceState(TransactionCase):

    def test_00_account_invoice_state_flow(self):
        """Test Account Invoice State"""

        # Create an invoice and confirm it with this wizard
        default_get_vals = self.env['account.invoice'].default_get(list(self.env['account.invoice'].fields_get()))
        account_invoice = self.env['account.invoice'].new(default_get_vals)
        account_invoice._onchange_journal_id()
        account_invoice.partner_id = self.ref('base.res_partner_12')
        account_invoice._onchange_partner_id()
        account_invoice.invoice_line_ids = [(0, 0, {
            'name': 'Computer SC234',
            'price_unit': 450.0,
            'quantity': 1.0,
            'product_id': self.ref('product.product_product_3'),
            'uom_id': self.ref('product.product_uom_unit'),
            'invoice_id': account_invoice,  # This value is required for '_onchange_product_id' to work correctly
        })]
        account_invoice.invoice_line_ids._onchange_product_id()
        account_invoice._onchange_invoice_line_ids()
        vals = account_invoice._convert_to_write(account_invoice._cache)
        account_invoice = self.env['account.invoice'].create(vals)

        # Check account invoice state
        self.assertEqual(account_invoice.state, 'draft', 'Account: Invoice state should be draft')

        # Clicked on "Confirm Invoices" Button
        self.env['account.invoice.confirm'].with_context({
            "lang": 'en_US',
            "tz": False,
            "active_model": "account.invoice",
            "active_ids": [account_invoice.id],
            "type": "out_invoice",
            "active_id": account_invoice.id
        }).invoice_confirm()

        # Check that customer invoice state is "Open"
        self.assertEqual(account_invoice.state, 'open', 'Account: invoice state should be open')

        # Check the journal associated and put this journal as not
        moves_line = self.env['account.move.line'].search([
            ('invoice_id', '=', account_invoice.id)
        ])
        # Check you have multiple move lines
        self.assertEqual(len(moves_line), 2, 'You should have multiple move lines')

        moves_line[0].journal_id.write({'update_posted': True})

        # I cancelled this open invoice using the button on invoice
        account_invoice.action_invoice_cancel()

        # Check that customer invoice is in the cancel state
        self.assertEqual(account_invoice.state, 'cancel', 'Account: invoice state should be cancelled')
