# -*- coding: utf-8 -*-
import time

from odoo import fields
from odoo.tests.common import TransactionCase, Form

class TestAccountBankStatement(TransactionCase):
    """
    In order to test Bank Statement feature of account I create a bank
    statement line and confirm it and check it's move created
    """
    def test_basic(self):
        env = self.env(context=dict(self.env.context, journal_type='bank'))

        # select the period and journal for the bank statement
        journal = env['account.bank.statement'].with_context(
            date=time.strftime("%Y/%m/%d"),  # ???
        )._default_journal()
        self.assertTrue(journal, 'Journal has not been selected')

        f = Form(env['account.bank.statement'])
        # necessary as there may be existing bank statements with a non-zero
        # closing balance which will be used to initialise this one.
        f.balance_start = 0.0
        f.balance_end_real = 0.0
        with f.line_ids.new() as line:
            line.name = 'EXT001'
            line.amount = 1000
            line.partner_id = env.ref('base.res_partner_4')

        statement_id = f.save()

        # process the bank statement line
        account = env['account.account'].create({
            'name': 'toto',
            'code': 'bidule',
            'user_type_id': env.ref('account.data_account_type_fixed_assets').id
        })
        statement_id.line_ids[0].process_reconciliation(new_aml_dicts=[{
            'credit': 1000,
            'debit': 0,
            'name': 'toto',
            'account_id': account.id,
        }])

        with Form(statement_id) as f:
            # modify the bank statement and set the Ending Balance.
            f.balance_end_real = 1000.0

        # confirm the bank statement using Validate button
        statement_id.button_confirm_bank()

        self.assertEqual(statement_id.state, 'confirm')

class TestAccountInvoice(TransactionCase):
    def test_state(self):
        # In order to test Confirm Draft Invoice wizard I create an invoice
        # and confirm it with this wizard
        f = Form(self.env['account.invoice'])
        f.partner_id = self.env.ref('base.res_partner_12')
        with f.invoice_line_ids.new() as l:
            l.product_id = self.env.ref('product.product_product_3')
        invoice = f.save()

        # I check that Initially customer invoice state is "Draft"
        self.assertEqual(invoice.state, 'draft')

        # I called the "Confirm Draft Invoices" wizard
        w = Form(self.env['account.invoice.confirm']).save()
        # I clicked on Confirm Invoices Button
        w.with_context(
            active_model='account.invoice',
            active_id=invoice.id,
            active_ids=invoice.ids,
            type='out_invoice',
        ).invoice_confirm()

        # I check that customer invoice state is "Open"
        self.assertEqual(invoice.state, 'open')

        # I check the journal associated and put this journal as not
        moves = self.env['account.move.line'].search([
            ('invoice_id', '=', invoice.id)
        ])
        self.assertGreater(len(moves), 0, 'You should have multiple moves')
        moves[0].journal_id.write({'update_posted': True})

        # I cancelled this open invoice using the button on invoice
        invoice.action_invoice_cancel()
        # I check that customer invoice is in the cancel state
        self.assertEqual(invoice.state, 'cancel')
