# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import unittest
from datetime import timedelta

from odoo import api, fields
from odoo.addons.account.tests.common import TestAccountReconciliationCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestReconciliationExec(TestAccountReconciliationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.currency.rate'].search([]).unlink()

    def test_statement_euro_invoice_usd_transaction_euro_full(self):
        self.env['res.currency.rate'].create({
            'name': '%s-07-01' % time.strftime('%Y'),
            'rate': 1.5289,
            'currency_id': self.currency_usd_id,
        })
        # Create a customer invoice of 50 USD.
        partner = self.env['res.partner'].create({'name': 'test'})
        move = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '%s-07-01' % time.strftime('%Y'),
            'date': '%s-07-01' % time.strftime('%Y'),
            'currency_id': self.currency_usd_id,
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 50.0, 'name': 'test'})
            ],
        })
        move.action_post()

        # Create a bank statement of 40 EURO.
        bank_stmt = self.env['account.bank.statement'].create({
            'journal_id': self.bank_journal_euro.id,
            'date': '%s-01-01' % time.strftime('%Y'),
            'line_ids': [
                (0, 0, {
                    'payment_ref': 'test',
                    'partner_id': partner.id,
                    'amount': 40.0,
                    'date': '%s-01-01' % time.strftime('%Y')
                })
            ],
        })

        # Reconcile the bank statement with the invoice.
        receivable_line = move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        bank_stmt.button_post()
        bank_stmt.line_ids[0].reconcile([
            {'id': receivable_line.id},
            {'name': 'exchange difference', 'balance': -7.3, 'account_id': self.diff_income_account.id},
        ])

        self.assertRecordValues(bank_stmt.line_ids.line_ids, [
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 40.0,    'currency_id': self.currency_euro_id},
            {'debit': 0.0,      'credit': 7.3,      'amount_currency': -7.3,    'currency_id': self.currency_euro_id},
            {'debit': 0.0,      'credit': 32.7,     'amount_currency': -32.7,   'currency_id': self.currency_euro_id},
        ])

        # The invoice should be paid, as the payments totally cover its total
        self.assertEqual(move.payment_state, 'paid', 'The invoice should be paid by now')
        self.assertTrue(receivable_line.reconciled, 'The invoice should be totally reconciled')
        self.assertTrue(receivable_line.full_reconcile_id, 'The invoice should have a full reconcile number')
        self.assertEqual(receivable_line.amount_residual, 0, 'The invoice should be totally reconciled')
        self.assertEqual(receivable_line.amount_residual_currency, 0, 'The invoice should be totally reconciled')

    @unittest.skip('adapt to new accounting')
    def test_balanced_exchanges_gain_loss(self):
        # The point of this test is to show that we handle correctly the gain/loss exchanges during reconciliations in foreign currencies.
        # For instance, with a company set in EUR, and a USD rate set to 0.033,
        # the reconciliation of an invoice of 2.00 USD (60.61 EUR) and a bank statement of two lines of 1.00 USD (30.30 EUR)
        # will lead to an exchange loss, that should be handled correctly within the journal items.
        env = api.Environment(self.cr, self.uid, {})
        # We update the currency rate of the currency USD in order to force the gain/loss exchanges in next steps
        rateUSDbis = env.ref("base.rateUSDbis")
        rateUSDbis.write({
            'name': time.strftime('%Y-%m-%d') + ' 00:00:00',
            'rate': 0.033,
        })
        # We create a customer invoice of 2.00 USD
        invoice = self.account_invoice_model.create({
            'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'name': 'Foreign invoice with exchange gain',
            'account_id': self.account_rcv_id,
            'move_type': 'out_invoice',
            'invoice_date': time.strftime('%Y-%m-%d'),
            'date': time.strftime('%Y-%m-%d'),
            'journal_id': self.bank_journal_usd_id,
            'invoice_line': [
                (0, 0, {
                    'name': 'line that will lead to an exchange gain',
                    'quantity': 1,
                    'price_unit': 2,
                })
            ]
        })
        invoice.action_post()
        # We create a bank statement with two lines of 1.00 USD each.
        statement = self.env['account.bank.statement'].create({
            'journal_id': self.bank_journal_usd_id,
            'date': time.strftime('%Y-%m-%d'),
            'line_ids': [
                (0, 0, {
                    'name': 'half payment',
                    'partner_id': self.partner_agrolait_id,
                    'amount': 1.0,
                    'date': time.strftime('%Y-%m-%d')
                }),
                (0, 0, {
                    'name': 'second half payment',
                    'partner_id': self.partner_agrolait_id,
                    'amount': 1.0,
                    'date': time.strftime('%Y-%m-%d')
                })
            ]
        })

        # We process the reconciliation of the invoice line with the two bank statement lines
        line_id = None
        for l in invoice.line_id:
            if l.account_id.id == self.account_rcv_id:
                line_id = l
                break
        for statement_line in statement.line_ids:
            statement_line.reconcile([{'id': line_id.id}])

        # The invoice should be paid, as the payments totally cover its total
        self.assertEqual(invoice.state, 'paid', 'The invoice should be paid by now')
        reconcile = None
        for payment in invoice.payment_ids:
            reconcile = payment.reconcile_model_id
            break
        # The invoice should be reconciled (entirely, not a partial reconciliation)
        self.assertTrue(reconcile, 'The invoice should be totally reconciled')
        result = {}
        exchange_loss_line = None
        for line in reconcile.line_id:
            res_account = result.setdefault(line.account_id, {'debit': 0.0, 'credit': 0.0, 'count': 0})
            res_account['debit'] = res_account['debit'] + line.debit
            res_account['credit'] = res_account['credit'] + line.credit
            res_account['count'] += 1
            if line.credit == 0.01:
                exchange_loss_line = line
        # We should be able to find a move line of 0.01 EUR on the Debtors account, being the cent we lost during the currency exchange
        self.assertTrue(exchange_loss_line, 'There should be one move line of 0.01 EUR in credit')
        # The journal items of the reconciliation should have their debit and credit total equal
        # Besides, the total debit and total credit should be 60.61 EUR (2.00 USD)
        self.assertEqual(sum(res['debit'] for res in result.values()), 60.61)
        self.assertEqual(sum(res['credit'] for res in result.items()), 60.61)
        counterpart_exchange_loss_line = None
        for line in exchange_loss_line.move_id.line_id:
            if line.account_id.id == self.account_fx_expense_id:
                counterpart_exchange_loss_line = line
        #  We should be able to find a move line of 0.01 EUR on the Foreign Exchange Loss account
        self.assertTrue(counterpart_exchange_loss_line, 'There should be one move line of 0.01 EUR on account "Foreign Exchange Loss"')

    def test_manual_reconcile_wizard_opw678153(self):

        def create_move(name, amount, amount_currency, currency_id):
            debit_line_vals = {
                'name': name,
                'debit': amount > 0 and amount or 0.0,
                'credit': amount < 0 and -amount or 0.0,
                'account_id': self.account_rcv.id,
                'amount_currency': amount_currency,
                'currency_id': currency_id,
            }
            credit_line_vals = debit_line_vals.copy()
            credit_line_vals['debit'] = debit_line_vals['credit']
            credit_line_vals['credit'] = debit_line_vals['debit']
            credit_line_vals['account_id'] = self.account_rsa.id
            credit_line_vals['amount_currency'] = -debit_line_vals['amount_currency']
            vals = {
                'journal_id': self.bank_journal_euro.id,
                'line_ids': [(0,0, debit_line_vals), (0, 0, credit_line_vals)]
            }
            move = self.env['account.move'].create(vals)
            move.action_post()
            return move.id
        move_list_vals = [
            ('1', -1.83, 0, self.currency_swiss_id),
            ('2', 728.35, 795.05, self.currency_swiss_id),
            ('3', -4.46, 0, self.currency_swiss_id),
            ('4', 0.32, 0, self.currency_swiss_id),
            ('5', 14.72, 16.20, self.currency_swiss_id),
            ('6', -737.10, -811.25, self.currency_swiss_id),
        ]
        move_ids = []
        for name, amount, amount_currency, currency_id in move_list_vals:
            move_ids.append(create_move(name, amount, amount_currency, currency_id))
        aml_recs = self.env['account.move.line'].search([('move_id', 'in', move_ids), ('account_id', '=', self.account_rcv.id), ('reconciled', '=', False)])
        aml_recs.reconcile()
        for aml in aml_recs:
            self.assertTrue(aml.reconciled, 'The journal item should be totally reconciled')
            self.assertEqual(aml.amount_residual, 0, 'The journal item should be totally reconciled')
            self.assertEqual(aml.amount_residual_currency, 0, 'The journal item should be totally reconciled')

    def test_partial_reconcile_currencies_01(self):
        #                client Account (payable, rsa)
        #        Debit                      Credit
        # --------------------------------------------------------
        # Pay a : 25/0.5 = 50       |   Inv a : 50/0.5 = 100
        # Pay b: 50/0.75 = 66.66    |   Inv b : 50/0.75 = 66.66
        # Pay c: 25/0.8 = 31.25     |
        #
        # Debit_currency = 100      | Credit currency = 100
        # Debit = 147.91            | Credit = 166.66
        # Balance Debit = 18.75
        # Counterpart Credit goes in Exchange diff

        dest_journal_id = self.env['account.journal'].create({
            'name': 'dest_journal_id',
            'type': 'bank',
        })

        # Setting up rates for USD (main_company is in EUR)
        self.env['res.currency.rate'].create({'name': time.strftime('%Y') + '-' + '07' + '-01',
            'rate': 0.5,
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id})

        self.env['res.currency.rate'].create({'name': time.strftime('%Y') + '-' + '08' + '-01',
            'rate': 0.75,
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id})

        self.env['res.currency.rate'].create({'name': time.strftime('%Y') + '-' + '09' + '-01',
            'rate': 0.80,
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id})

        # Preparing Invoices (from vendor)
        invoice_a = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'invoice_date': '%s-07-01' % time.strftime('%Y'),
            'date': '%s-07-01' % time.strftime('%Y'),
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product.id, 'quantity': 1, 'price_unit': 50.0})
            ],
        })
        invoice_b = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'invoice_date': '%s-08-01' % time.strftime('%Y'),
            'date': '%s-08-01' % time.strftime('%Y'),
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product.id, 'quantity': 1, 'price_unit': 50.0})
            ],
        })
        (invoice_a + invoice_b).action_post()

        # Preparing Payments
        # One partial for invoice_a (fully assigned to it)
        payment_a = self.env['account.payment'].create({'payment_type': 'outbound',
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_euro.id,
            'company_id': self.company.id,
            'date': time.strftime('%Y') + '-' + '07' + '-01',
            'partner_id': self.partner_agrolait_id,
            'payment_method_line_id': self.bank_journal_euro.inbound_payment_method_line_ids[0].id,
            'partner_type': 'supplier'})

        # One that will complete the payment of a, the rest goes to b
        payment_b = self.env['account.payment'].create({'payment_type': 'outbound',
            'amount': 50,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_euro.id,
            'company_id': self.company.id,
            'date': time.strftime('%Y') + '-' + '08' + '-01',
            'partner_id': self.partner_agrolait_id,
            'payment_method_line_id': self.bank_journal_euro.outbound_payment_method_line_ids[0].id,
            'partner_type': 'supplier'})

        # The last one will complete the payment of b
        payment_c = self.env['account.payment'].create({'payment_type': 'outbound',
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_euro.id,
            'company_id': self.company.id,
            'date': time.strftime('%Y') + '-' + '09' + '-01',
            'partner_id': self.partner_agrolait_id,
            'payment_method_line_id': self.bank_journal_euro.outbound_payment_method_line_ids[0].id,
            'partner_type': 'supplier'})

        payment_a.action_post()
        payment_b.action_post()
        payment_c.action_post()

        # Assigning payments to invoices
        debit_line_a = payment_a.line_ids.filtered(lambda l: l.debit and l.account_id == self.account_rsa)
        debit_line_b = payment_b.line_ids.filtered(lambda l: l.debit and l.account_id == self.account_rsa)
        debit_line_c = payment_c.line_ids.filtered(lambda l: l.debit and l.account_id == self.account_rsa)

        invoice_a.js_assign_outstanding_line(debit_line_a.id)
        invoice_a.js_assign_outstanding_line(debit_line_b.id)
        invoice_b.js_assign_outstanding_line(debit_line_b.id)
        invoice_b.js_assign_outstanding_line(debit_line_c.id)

        # Asserting correctness (only in the payable account)
        full_reconcile = False
        reconciled_amls = (debit_line_a + debit_line_b + debit_line_c + (invoice_a + invoice_b).mapped('line_ids'))\
            .filtered(lambda l: l.account_id == self.account_rsa)
        for aml in reconciled_amls:
            self.assertEqual(aml.amount_residual, 0.0)
            self.assertEqual(aml.amount_residual_currency, 0.0)
            self.assertTrue(aml.reconciled)
            if not full_reconcile:
                full_reconcile = aml.full_reconcile_id
            else:
                self.assertTrue(aml.full_reconcile_id == full_reconcile)

        full_rec_move = full_reconcile.exchange_move_id
        # Globally check whether the amount is correct
        self.assertEqual(sum(full_rec_move.mapped('line_ids.debit')), 18.75)

        # Checking if the direction of the move is correct
        full_rec_payable = full_rec_move.line_ids.filtered(lambda l: l.account_id == self.account_rsa)
        self.assertEqual(full_rec_payable.balance, 18.75)

    def test_unreconcile(self):
        # Use case:
        # 2 invoices paid with a single payment. Unreconcile the payment with one invoice, the
        # other invoice should remain reconciled.
        inv1 = self.create_invoice(invoice_amount=10, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(invoice_amount=20, currency_id=self.currency_usd_id)
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_line_id': self.bank_journal_usd.inbound_payment_method_line_ids[0].id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 100,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
        })
        payment.action_post()
        credit_aml = payment.line_ids.filtered('credit')

        # Check residual before assignation
        self.assertAlmostEqual(inv1.amount_residual, 10)
        self.assertAlmostEqual(inv2.amount_residual, 20)

        # Assign credit and residual
        inv1.js_assign_outstanding_line(credit_aml.id)
        inv2.js_assign_outstanding_line(credit_aml.id)
        self.assertAlmostEqual(inv1.amount_residual, 0)
        self.assertAlmostEqual(inv2.amount_residual, 0)

        # Unreconcile one invoice at a time and check residual
        credit_aml.remove_move_reconcile()
        self.assertAlmostEqual(inv1.amount_residual, 10)
        self.assertAlmostEqual(inv2.amount_residual, 20)

    def test_unreconcile_exchange(self):
        # Use case:
        # - Company currency in EUR
        # - Create 2 rates for USD:
        #   1.0 on 2018-01-01
        #   0.5 on 2018-02-01
        # - Create an invoice on 2018-01-02 of 111 USD
        # - Register a payment on 2018-02-02 of 111 USD
        # - Unreconcile the payment

        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-08-01',
            'rate': 0.5,
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id
        })
        inv = self.create_invoice(invoice_amount=111, currency_id=self.currency_usd_id)
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_line_id': self.bank_journal_usd.inbound_payment_method_line_ids[0].id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 111,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
            'date': time.strftime('%Y') + '-08-01',
        })
        payment.action_post()
        credit_aml = payment.line_ids.filtered('credit')

        # Check residual before assignation
        self.assertAlmostEqual(inv.amount_residual, 111)

        # Assign credit, check exchange move and residual
        inv.js_assign_outstanding_line(credit_aml.id)
        self.assertEqual(len(payment.line_ids.mapped('full_reconcile_id').exchange_move_id), 1)
        self.assertAlmostEqual(inv.amount_residual, 0)

        # Unreconcile invoice and check residual
        credit_aml.remove_move_reconcile()
        self.assertAlmostEqual(inv.amount_residual, 111)

    def test_revert_payment_and_reconcile(self):
        payment = self.env['account.payment'].create({
            'payment_method_line_id': self.bank_journal_usd.inbound_payment_method_line_ids[0].id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'journal_id': self.bank_journal_usd.id,
            'date': '2018-06-04',
            'amount': 666,
        })
        payment.action_post()

        self.assertEqual(len(payment.line_ids), 2)

        bank_line = payment.line_ids.filtered(lambda l: l.account_id.id == self.bank_journal_usd.company_id.account_journal_payment_debit_account_id.id)
        customer_line = payment.line_ids - bank_line

        self.assertEqual(len(bank_line), 1)
        self.assertEqual(len(customer_line), 1)
        self.assertNotEqual(bank_line.id, customer_line.id)

        self.assertEqual(bank_line.move_id.id, customer_line.move_id.id)
        move = bank_line.move_id

        # Reversing the payment's move
        reversed_move = move._reverse_moves([{'date': '2018-06-04'}])
        self.assertEqual(len(reversed_move), 1)

        self.assertEqual(len(reversed_move.line_ids), 2)

        # Testing the reconciliation matching between the move lines and their reversed counterparts
        reversed_bank_line = reversed_move.line_ids.filtered(lambda l: l.account_id.id == self.bank_journal_usd.company_id.account_journal_payment_debit_account_id.id)
        reversed_customer_line = reversed_move.line_ids - reversed_bank_line

        self.assertEqual(len(reversed_bank_line), 1)
        self.assertEqual(len(reversed_customer_line), 1)
        self.assertNotEqual(reversed_bank_line.id, reversed_customer_line.id)
        self.assertEqual(reversed_bank_line.move_id.id, reversed_customer_line.move_id.id)

        self.assertEqual(reversed_bank_line.full_reconcile_id.id, bank_line.full_reconcile_id.id)
        self.assertEqual(reversed_customer_line.full_reconcile_id.id, customer_line.full_reconcile_id.id)


    def test_revert_payment_and_reconcile_exchange(self):

        # A reversal of a reconciled payment which created a currency exchange entry, should create reversal moves
        # which move lines should be reconciled two by two with the original move's lines

        def _determine_debit_credit_line(move):
            line_ids_reconciliable = move.line_ids.filtered(lambda l: l.account_id.reconcile or l.account_id.internal_type == 'liquidity')
            return line_ids_reconciliable.filtered(lambda l: l.debit), line_ids_reconciliable.filtered(lambda l: l.credit)

        def _move_revert_test_pair(move, revert):
            self.assertTrue(move.line_ids)
            self.assertTrue(revert.line_ids)

            move_lines = _determine_debit_credit_line(move)
            revert_lines = _determine_debit_credit_line(revert)

            # in the case of the exchange entry, only one pair of lines will be found
            if move_lines[0] and revert_lines[1]:
                self.assertTrue(move_lines[0].full_reconcile_id.exists())
                self.assertEqual(move_lines[0].full_reconcile_id.id, revert_lines[1].full_reconcile_id.id)

            if move_lines[1] and revert_lines[0]:
                self.assertTrue(move_lines[1].full_reconcile_id.exists())
                self.assertEqual(move_lines[1].full_reconcile_id.id, revert_lines[0].full_reconcile_id.id)

        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-08-01',
            'rate': 0.5,
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id
        })
        inv = self.create_invoice(invoice_amount=111, currency_id=self.currency_usd_id)
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_line_id': self.bank_journal_usd.inbound_payment_method_line_ids[0].id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 111,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
            'date': time.strftime('%Y') + '-08-01',
        })
        payment.action_post()

        credit_aml = payment.line_ids.filtered('credit')
        inv.js_assign_outstanding_line(credit_aml.id)
        self.assertTrue(inv.payment_state in ('in_payment', 'paid'), "Invoice should be paid")

        exchange_reconcile = payment.line_ids.mapped('full_reconcile_id')
        exchange_move = exchange_reconcile.exchange_move_id
        payment_move = payment.line_ids[0].move_id

        reverted_payment_move = payment_move._reverse_moves([{'date': time.strftime('%Y') + '-08-01'}], cancel=True)

        # After reversal of payment, the invoice should be open
        self.assertTrue(inv.state == 'posted', 'The invoice should be open again')
        self.assertFalse(exchange_reconcile.exists())

        reverted_exchange_move = self.env['account.move'].search([('journal_id', '=', exchange_move.journal_id.id), ('ref', 'ilike', exchange_move.name)], limit=1)
        _move_revert_test_pair(payment_move, reverted_payment_move)
        _move_revert_test_pair(exchange_move, reverted_exchange_move)

    def test_partial_reconcile_currencies_02(self):
        ####
        # Day 1: Invoice Cust/001 to customer (expressed in USD)
        # Market value of USD (day 1): 1 USD = 0.5 EUR
        # * Dr. 100 USD / 50 EUR - Accounts receivable
        # * Cr. 100 USD / 50 EUR - Revenue
        ####
        dest_journal_id = self.env['account.journal'].create({
            'name': 'turlututu',
            'type': 'bank',
            'company_id': self.env.company.id,
        })

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'name': time.strftime('%Y') + '-01-01',
            'rate': 2,
        })

        invoice_cust_1 = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_agrolait_id,
            'invoice_date': '%s-01-01' % time.strftime('%Y'),
            'date': '%s-01-01' % time.strftime('%Y'),
            'currency_id': self.currency_usd_id,
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 100.0, 'name': 'product that cost 100'})
            ],
        })
        invoice_cust_1.action_post()
        aml = invoice_cust_1.invoice_line_ids[0]
        self.assertEqual(aml.credit, 50.0)
        #####
        # Day 2: Receive payment for half invoice Cust/1 (in USD)
        # -------------------------------------------------------
        # Market value of USD (day 2): 1 USD = 1 EUR

        # Payment transaction:
        # * Dr. 50 USD / 50 EUR - EUR Bank (valued at market price
        # at the time of receiving the money)
        # * Cr. 50 USD / 50 EUR - Accounts Receivable
        #####
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'name': time.strftime('%Y') + '-01-02',
            'rate': 1,
        })

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice_cust_1.ids)\
            .create({
                'payment_date': time.strftime('%Y') + '-01-02',
                'amount': 50,
                'journal_id': dest_journal_id.id,
                'currency_id': self.currency_usd_id,
            })\
            ._create_payments()

        # We expect at this point that the invoice should still be open, in 'partial' state,
        # because they owe us still 50 CC.
        self.assertEqual(invoice_cust_1.payment_state, 'partial', 'Invoice is in status %s' % invoice_cust_1.state)

    def test_multiple_term_reconciliation_opw_1906665(self):
        '''Test that when registering a payment to an invoice with multiple
        payment term lines the reconciliation happens against the line
        with the earliest date_maturity
        '''

        payment_term = self.env['account.payment.term'].create({
            'name': 'Pay in 2 installments',
            'line_ids': [
                # Pay 50% immediately
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 50,
                }),
                # Pay the rest after 14 days
                (0, 0, {
                    'value': 'balance',
                    'days': 14,
                })
            ],
        })

        # can't use self.create_invoice because it validates and we need to set payment_term_id
        invoice = self.create_invoice_partner(
            partner_id=self.partner_agrolait_id,
            payment_term_id=payment_term.id,
            currency_id=self.currency_usd_id,
        )

        payment = self.env['account.payment'].create({
            'date': time.strftime('%Y') + '-07-15',
            'payment_type': 'inbound',
            'payment_method_line_id': self.bank_journal_usd.inbound_payment_method_line_ids[0].id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
        })
        payment.action_post()

        receivable_line = payment.line_ids.filtered('credit')
        invoice.js_assign_outstanding_line(receivable_line.id)

        self.assertTrue(receivable_line.matched_debit_ids)

    def test_reconciliation_with_currency(self):
        #reconciliation on an account having a foreign currency being
        #the same as the company one
        account_rcv = self.account_rcv
        account_rcv.currency_id = self.currency_euro_id
        aml_obj = self.env['account.move.line'].with_context(
            check_move_validity=False)
        general_move1 = self.env['account.move'].create({
            'name': 'general1',
            'journal_id': self.general_journal.id,
        })
        aml_obj.create({
            'name': 'debit1',
            'account_id': account_rcv.id,
            'debit': 11,
            'move_id': general_move1.id,
        })
        aml_obj.create({
            'name': 'credit1',
            'account_id': self.account_rsa.id,
            'credit': 11,
            'move_id': general_move1.id,
        })
        general_move1.action_post()
        general_move2 = self.env['account.move'].create({
            'name': 'general2',
            'journal_id': self.general_journal.id,
        })
        aml_obj.create({
            'name': 'credit2',
            'account_id': account_rcv.id,
            'credit': 10,
            'move_id': general_move2.id,
        })
        aml_obj.create({
            'name': 'debit2',
            'account_id': self.account_rsa.id,
            'debit': 10,
            'move_id': general_move2.id,
        })
        general_move2.action_post()
        general_move3 = self.env['account.move'].create({
            'name': 'general3',
            'journal_id': self.general_journal.id,
        })
        aml_obj.create({
            'name': 'credit3',
            'account_id': account_rcv.id,
            'credit': 1,
            'move_id': general_move3.id,
        })
        aml_obj.create({
            'name': 'debit3',
            'account_id': self.account_rsa.id,
            'debit': 1,
            'move_id': general_move3.id,
        })
        general_move3.action_post()
        to_reconcile = ((general_move1 + general_move2 + general_move3)
            .mapped('line_ids')
            .filtered(lambda l: l.account_id.id == account_rcv.id))
        to_reconcile.reconcile()
        for aml in to_reconcile:
            self.assertEqual(aml.amount_residual, 0.0)

    def test_inv_refund_foreign_payment_writeoff_domestic2(self):
        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.110600,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': self.company.id
        })
        inv1 = self.create_invoice(invoice_amount=800, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(move_type="out_refund", invoice_amount=400, currency_id=self.currency_usd_id)

        payment = self.env['account.payment'].create({
            'date': time.strftime('%Y') + '-07-15',
            'payment_method_line_id': self.bank_journal_euro.inbound_payment_method_line_ids[0].id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 200.00,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
        })
        payment.action_post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-01',
            'journal_id': self.bank_journal_euro.id,
            'line_ids': [
                (0, False, {'credit': 160.16, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 160.16, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })

        move_balance.action_post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + inv2_receivable + pay_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, move_balance_receiv.full_reconcile_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
        self.assertEqual(inv2.payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic3(self):
        """
                    Receivable
                Domestic (Foreign)
        592.47 (658.00) |                    INV 1  > Done in foreign
                        |   202.59 (225.00)  INV 2  > Done in foreign
                        |   372.10 (413.25)  PAYMENT > Done in domestic (the 413.25 is virtual, non stored)
                        |    17.78  (19.75)  WriteOff > Done in domestic (the 19.75 is virtual, non stored)
        Reconciliation should be full
        Invoices should be marked as paid
        """
        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.110600,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': company.id
        })
        inv1 = self.create_invoice(invoice_amount=658, currency_id=self.currency_usd_id)
        inv2 = self.create_invoice(move_type="out_refund", invoice_amount=225, currency_id=self.currency_usd_id)

        payment = self.env['account.payment'].create({
            'payment_method_line_id': self.bank_journal_euro.inbound_payment_method_line_ids[0].id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 372.10,
            'date': time.strftime('%Y') + '-07-01',
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
        })
        payment.action_post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-01',
            'journal_id': self.bank_journal_euro.id,
            'line_ids': [
                (0, False, {'credit': 17.78, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 17.78, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })

        move_balance.action_post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + inv2_receivable + pay_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, move_balance_receiv.full_reconcile_id)

        self.assertFalse(inv1_receivable.full_reconcile_id.exchange_move_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
        self.assertEqual(inv2.payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic4(self):
        """
                    Receivable
                Domestic (Foreign)
        658.00 (658.00) |                    INV 1  > Done in foreign
                        |   202.59 (225.00)  INV 2  > Done in foreign
                        |   372.10 (413.25)  PAYMENT > Done in domestic (the 413.25 is virtual, non stored)
                        |    83.31  (92.52)  WriteOff > Done in domestic (the 92.52 is virtual, non stored)
        Reconciliation should be full
        Invoices should be marked as paid
        """
        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-15',
            'rate': 1.110600,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': company.id
        })
        inv1 = self._create_invoice(invoice_amount=658, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-01', auto_validate=True)
        inv2 = self._create_invoice(move_type="out_refund", invoice_amount=225, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        payment = self.env['account.payment'].create({
            'date': time.strftime('%Y') + '-07-15',
            'payment_method_line_id': self.bank_journal_euro.inbound_payment_method_line_ids[0].id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 372.10,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': self.currency_euro_id,
        })
        payment.action_post()

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        pay_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 658)
        self.assertEqual(inv2_receivable.balance, -202.59)
        self.assertEqual(pay_receivable.balance, -372.1)

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal_usd.id,
            'line_ids': [
                (0, False, {'credit': 83.31, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 83.31, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })

        move_balance.action_post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + inv2_receivable + pay_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, pay_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, move_balance_receiv.full_reconcile_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
        self.assertEqual(inv2.payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic5(self):
        """
                    Receivable
                Domestic (Foreign)
        600.00 (600.00) |                    INV 1  > Done in foreign
                        |   250.00 (250.00)  INV 2  > Done in foreign
                        |   314.07 (314.07)  PAYMENT > Done in domestic (foreign non stored)
                        |    35.93  (60.93)  WriteOff > Done in domestic (foreign non stored). WriteOff is included in payment
        Reconciliation should be full, without exchange difference
        Invoices should be marked as paid
        """
        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': company.id
        })

        inv1 = self._create_invoice(invoice_amount=600, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)
        inv2 = self._create_invoice(move_type="out_refund", invoice_amount=250, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 600.00)
        self.assertEqual(inv2_receivable.balance, -250)

        # partially pay the invoice with the refund
        inv1.js_assign_outstanding_line(inv2_receivable.id)
        self.assertEqual(inv1.amount_residual, 350)

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=inv1.ids)\
            .create({
                'payment_date': time.strftime('%Y') + '-07-15',
                'amount': 314.07,
                'journal_id': self.bank_journal_euro.id,
                'currency_id': self.currency_euro_id,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.diff_income_account.id,
            })\
            ._create_payments()

        payment_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        self.assertEqual(payment_receivable.balance, -350)

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        self.assertFalse(inv1_receivable.full_reconcile_id.exchange_move_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
        self.assertEqual(inv2.payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic6(self):
        """
                    Receivable
                Domestic (Foreign)
        540.25 (600.00) |                    INV 1  > Done in foreign
                        |   225.10 (250.00)  INV 2  > Done in foreign
                        |   315.15 (350.00)  PAYMENT > Done in domestic (the 350.00 is virtual, non stored)
        """
        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': company.id
        })
        inv1 = self._create_invoice(invoice_amount=600, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)
        inv2 = self._create_invoice(move_type="out_refund", invoice_amount=250, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 540.25)
        self.assertEqual(inv2_receivable.balance, -225.10)

        # partially pay the invoice with the refund
        inv1.js_assign_outstanding_line(inv2_receivable.id)
        self.assertAlmostEqual(inv1.amount_residual, 350)
        self.assertAlmostEqual(inv1_receivable.amount_residual, 315.15)

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=inv1.ids)\
            .create({
                'payment_date': time.strftime('%Y') + '-07-15',
                'amount': 314.07,
                'journal_id': self.bank_journal_euro.id,
                'currency_id': self.currency_euro_id,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.diff_income_account.id,
            })\
            ._create_payments()

        payment_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
        self.assertEqual(inv2.payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic6bis(self):
        """
        Same as domestic6, but only in foreign currencies
        Obviously, it should lead to the same kind of results
        Here there is no exchange difference entry though
        """
        foreign_0 = self.env['res.currency'].create({
            'name': 'foreign0',
            'symbol': 'F0'
        })
        foreign_1 = self.env['res.currency'].browse(self.currency_usd_id)

        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })

        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': foreign_0.id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': foreign_1.id,
            'company_id': company.id
        })
        inv1 = self._create_invoice(invoice_amount=600, currency_id=foreign_1.id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)
        inv2 = self._create_invoice(move_type="out_refund", invoice_amount=250, currency_id=foreign_1.id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        inv2_receivable = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertEqual(inv1_receivable.balance, 540.25)
        self.assertEqual(inv2_receivable.balance, -225.10)

        # partially pay the invoice with the refund
        inv1.js_assign_outstanding_line(inv2_receivable.id)
        self.assertAlmostEqual(inv1.amount_residual, 350)
        self.assertAlmostEqual(inv1_receivable.amount_residual, 315.15)

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=inv1.ids)\
            .create({
                'payment_date': time.strftime('%Y') + '-07-15',
                'amount': 314.07,
                'journal_id': self.bank_journal_euro.id,
                'currency_id': foreign_0.id,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.diff_income_account.id,
            })\
            ._create_payments()

        payment_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, inv2_receivable.full_reconcile_id)
        self.assertEqual(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
        self.assertEqual(inv2.payment_state, 'paid')

    def test_inv_refund_foreign_payment_writeoff_domestic7(self):
        """
                    Receivable
                Domestic (Foreign)
        5384.48 (5980.00) |                      INV 1  > Done in foreign
                          |   5384.43 (5979.95)  PAYMENT > Done in domestic (foreign non stored)
                          |      0.05    (0.00)  WriteOff > Done in domestic (foreign non stored). WriteOff is included in payment,
                                                                so, the amount in currency is irrelevant
        Reconciliation should be full, without exchange difference
        Invoices should be marked as paid
        """
        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': company.id
        })
        inv1 = self._create_invoice(invoice_amount=5980, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertAlmostEqual(inv1_receivable.balance, 5384.48)

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=inv1.ids)\
            .create({
                'payment_date': time.strftime('%Y') + '-07-15',
                'amount': 5384.43,
                'journal_id': self.bank_journal_euro.id,
                'currency_id': self.currency_euro_id,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.diff_income_account.id,
            })\
            ._create_payments()

        payment_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)

        self.assertFalse(inv1_receivable.full_reconcile_id.exchange_move_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")

    def test_inv_refund_foreign_payment_writeoff_domestic8(self):
        """
        Roughly the same as *_domestic7
        Though it simulates going through the reconciliation widget
        Because the WriteOff is on a different line than the payment
        """
        company = self.company
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.0,
            'currency_id': self.currency_euro_id,
            'company_id': company.id
        })
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y') + '-07-01',
            'rate': 1.1106,  # Don't change this !
            'currency_id': self.currency_usd_id,
            'company_id': company.id
        })
        inv1 = self._create_invoice(invoice_amount=5980, currency_id=self.currency_usd_id, date_invoice=time.strftime('%Y') + '-07-15', auto_validate=True)

        inv1_receivable = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        self.assertAlmostEqual(inv1_receivable.balance, 5384.48)

        Payment = self.env['account.payment']
        payment = Payment.create({
            'date': time.strftime('%Y') + '-07-15',
            'payment_method_line_id': self.bank_journal_euro.inbound_payment_method_line_ids[0].id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': inv1.partner_id.id,
            'amount': 5384.43,
            'journal_id': self.bank_journal_euro.id,
            'company_id': company.id,
            'currency_id': self.currency_euro_id,
        })
        payment.action_post()
        payment_receivable = payment.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        move_balance = self.env['account.move'].create({
            'partner_id': inv1.partner_id.id,
            'date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal_usd.id,
            'line_ids': [
                (0, False, {'credit': 0.05, 'account_id': inv1_receivable.account_id.id, 'name': 'Balance WriteOff'}),
                (0, False, {'debit': 0.05, 'account_id': self.diff_expense_account.id, 'name': 'Balance WriteOff'}),
            ]
        })
        move_balance.action_post()
        move_balance_receiv = move_balance.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        (inv1_receivable + payment_receivable + move_balance_receiv).reconcile()

        self.assertTrue(inv1_receivable.full_reconcile_id.exists())
        self.assertEqual(inv1_receivable.full_reconcile_id, payment_receivable.full_reconcile_id)
        self.assertEqual(move_balance_receiv.full_reconcile_id, inv1_receivable.full_reconcile_id)

        self.assertTrue(inv1.payment_state in ('in_payment', 'paid'), "Invoice should be paid")

    def test_reconciliation_with_old_oustanding_account(self):
        """
        Test the reconciliation of an invoice with a payment after changing the outstanding account of the journal.
        """
        outstanding_account_1 = self.company_data['company'].account_journal_payment_debit_account_id.copy()
        outstanding_account_2 = outstanding_account_1.copy()

        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = outstanding_account_1

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'amount': 1150,
        })
        payment.action_post()

        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = outstanding_account_2
        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000.0], taxes=self.env['account.tax'])

        credit_line = payment.line_ids.filtered(lambda l: l.credit and l.account_id == self.account_rcv)

        invoice.js_assign_outstanding_line(credit_line.id)
        self.assertTrue(invoice.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
