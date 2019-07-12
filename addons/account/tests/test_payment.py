from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged
from odoo.tests.common import Form
import time


@tagged('post_install', '-at_install')
class TestPayment(AccountingTestCase):

    def setUp(self):
        super(TestPayment, self).setUp()
        self.register_payments_model = self.env['account.payment.register'].with_context(active_model='account.move')
        self.payment_model = self.env['account.payment']
        self.acc_bank_stmt_model = self.env['account.bank.statement']
        self.acc_bank_stmt_line_model = self.env['account.bank.statement.line']

        self.partner_agrolait = self.env.ref("base.res_partner_2")
        self.partner_china_exp = self.env.ref("base.res_partner_3")
        self.currency_chf_id = self.env.ref("base.CHF").id
        self.currency_usd_id = self.env.ref("base.USD").id
        self.currency_eur_id = self.env.ref("base.EUR").id

        company = self.env.ref('base.main_company')
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.currency_eur_id, company.id])
        self.product = self.env.ref("product.product_product_4")
        self.payment_method_manual_in = self.env.ref("account.account_payment_method_manual_in")
        self.payment_method_manual_out = self.env.ref("account.account_payment_method_manual_out")

        self.account_receivable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        self.account_payable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)], limit=1)
        self.account_revenue = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1)

        self.bank_journal_euro = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        self.account_eur = self.bank_journal_euro.default_debit_account_id

        self.bank_journal_usd = self.env['account.journal'].create({'name': 'Bank US', 'type': 'bank', 'code': 'BNK68', 'currency_id': self.currency_usd_id})
        self.account_usd = self.bank_journal_usd.default_debit_account_id

        self.transfer_account = self.env['res.users'].browse(self.env.uid).company_id.transfer_account_id
        self.diff_income_account = self.env['res.users'].browse(self.env.uid).company_id.income_currency_exchange_account_id
        self.diff_expense_account = self.env['res.users'].browse(self.env.uid).company_id.expense_currency_exchange_account_id

        self.form_payment = Form(self.env['account.payment'])

    def create_invoice(self, amount=100, type='out_invoice', currency_id=None, partner=None, account_id=None):
        """ Returns an open invoice """
        invoice = self.env['account.move'].create({
            'type': type,
            'partner_id': partner or self.partner_agrolait.id,
            'currency_id': currency_id or self.currency_eur_id,
            'invoice_date': time.strftime('%Y') + '-06-26',
            'date': time.strftime('%Y') + '-06-26',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product.id, 'quantity': 1, 'price_unit': amount})
            ],
        })
        invoice.post()
        return invoice

    def reconcile(self, liquidity_aml, amount=0.0, amount_currency=0.0, currency_id=None):
        """ Reconcile a journal entry corresponding to a payment with its bank statement line """
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': liquidity_aml.journal_id.id,
            'date': time.strftime('%Y') + '-07-15',
        })
        bank_stmt_line = self.acc_bank_stmt_line_model.create({
            'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait.id,
            'amount': amount,
            'amount_currency': amount_currency,
            'currency_id': currency_id,
            'date': time.strftime('%Y') + '-07-15'
        })

        bank_stmt_line.process_reconciliation(payment_aml_rec=liquidity_aml)
        return bank_stmt

    def test_full_payment_process(self):
        """ Create a payment for one invoice, post it and reconcile it with a bank statement """
        inv_1 = self.create_invoice(amount=300, currency_id=self.currency_eur_id, partner=self.partner_agrolait.id)

        ids = [inv_1.id]
        register_payments = self.register_payments_model.with_context(active_ids=ids).create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal_euro.id,
            'payment_method_id': self.payment_method_manual_in.id,
        })
        payment = self.payment_model.browse(register_payments.create_payments()['res_id'])

        self.assertAlmostEquals(payment.amount, 300)
        self.assertEqual(payment.state, 'posted')
        self.assertEqual(payment.state, 'posted')
        self.assertEqual(inv_1.invoice_payment_state, 'paid')

        rec_line = payment.move_line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        self.assertRecordValues(payment.move_line_ids.sorted('credit'), [
            {'account_id': self.account_eur.id, 'debit': 300.0, 'credit': 0.0, 'amount_currency': 0, 'currency_id': False},
            {'account_id': rec_line.account_id.id, 'debit': 0.0, 'credit': 300.0, 'amount_currency': 0, 'currency_id': False},
        ])
        self.assertTrue(rec_line.full_reconcile_id.exists())

        liquidity_aml = payment.move_line_ids - rec_line
        bank_statement = self.reconcile(liquidity_aml, 300, 0, False)

        self.assertEqual(liquidity_aml.statement_id, bank_statement)
        self.assertEqual(liquidity_aml.statement_line_id, bank_statement.line_ids[0])

        self.assertEqual(payment.state, 'reconciled')

    def test_internal_transfer_journal_usd_journal_eur(self):
        """ Create a transfer from a EUR journal to a USD journal """
        payment = self.payment_model.create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_type': 'transfer',
            'amount': 50,
            'currency_id': self.currency_usd_id,
            'journal_id': self.bank_journal_usd.id,
            'destination_journal_id': self.bank_journal_euro.id,
            'payment_method_id': self.payment_method_manual_out.id,
        })
        payment.post()
        self.assertRecordValues(payment.move_line_ids, [
            {'account_id': self.transfer_account.id, 'debit': 32.70, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_usd.id, 'debit': 0.0, 'credit': 32.70, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'account_id': self.transfer_account.id, 'debit': 0.0, 'credit': 32.70, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_eur.id, 'debit': 32.70, 'credit': 0.0, 'amount_currency': 0, 'currency_id': False},
        ])

    def test_payment_chf_journal_usd(self):
        payment = self.payment_model.create({
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_type': 'outbound',
            'amount': 50,
            'currency_id': self.currency_chf_id,
            'journal_id': self.bank_journal_usd.id,
            'partner_type': 'supplier',
            'partner_id': self.partner_china_exp.id,
            'payment_method_id': self.payment_method_manual_out.id,
        })
        payment.post()

        self.assertRecordValues(payment.move_line_ids, [
            {'account_id': self.partner_china_exp.property_account_payable_id.id, 'debit': 38.21, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_chf_id},
            {'account_id': self.account_usd.id, 'debit': 0.0, 'credit': 38.21, 'amount_currency': -58.42, 'currency_id': self.currency_usd_id},
        ])

    def test_partial_payment(self):
        """ Create test to pay invoices (cust. inv + vendor bill) with partial payment """
        # Test Customer Invoice
        inv_1 = self.create_invoice(amount=600)
        payment_register = Form(self.env['account.payment'].with_context(active_model='account.move', active_ids=inv_1.ids))
        payment_register.payment_date = time.strftime('%Y') + '-07-15'
        payment_register.journal_id = self.bank_journal_euro
        payment_register.payment_method_id = self.payment_method_manual_in

        # Perform the partial payment by setting the amount at 550 instead of 600
        payment_register.amount = 550

        payment = payment_register.save()

        self.assertEqual(len(payment), 1)
        self.assertEqual(payment.invoice_ids[0].id, inv_1.id)
        self.assertAlmostEquals(payment.amount, 550)
        self.assertEqual(payment.payment_type, 'inbound')
        self.assertEqual(payment.partner_id, self.partner_agrolait)
        self.assertEqual(payment.partner_type, 'customer')

        # Test Vendor Bill
        inv_2 = self.create_invoice(amount=500, type='in_invoice', partner=self.partner_china_exp.id)
        payment_register = Form(self.env['account.payment'].with_context(active_model='account.move', active_ids=inv_2.ids))
        payment_register.payment_date = time.strftime('%Y') + '-07-15'
        payment_register.journal_id = self.bank_journal_euro
        payment_register.payment_method_id = self.payment_method_manual_in

        # Perform the partial payment by setting the amount at 300 instead of 500
        payment_register.amount = 300

        payment = payment_register.save()

        self.assertEqual(len(payment), 1)
        self.assertEqual(payment.invoice_ids[0].id, inv_2.id)
        self.assertAlmostEquals(payment.amount, 300)
        self.assertEqual(payment.payment_type, 'outbound')
        self.assertEqual(payment.partner_id, self.partner_china_exp)
        self.assertEqual(payment.partner_type, 'supplier')

    def test_payment_and_writeoff_in_other_currency_1(self):
        # Use case:
        # Company is in EUR, create a customer invoice for 25 EUR and register payment of 25 USD.
        # Mark invoice as fully paid with a write_off
        # Check that all the aml are correctly created.
        invoice = self.create_invoice(amount=25, type='out_invoice', currency_id=self.currency_eur_id, partner=self.partner_agrolait.id)
        receivable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable')
        # register payment on invoice
        payment = self.payment_model.create({'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait.id,
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.account_payable.id,
            'journal_id': self.bank_journal_euro.id,
            'invoice_ids': [(4, invoice.id, None)]
            })
        payment.post()
        self.assertRecordValues(payment.move_line_ids, [
            {'account_id': receivable_line.account_id.id, 'debit': 0.0, 'credit': 25.0, 'amount_currency': -38.22, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_eur.id, 'debit': 16.35, 'credit': 0.0, 'amount_currency': 25.0, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_payable.id, 'debit': 8.65, 'credit': 0.0, 'amount_currency': 13.22, 'currency_id': self.currency_usd_id},
        ])
        self.assertTrue(receivable_line.full_reconcile_id)
        self.assertEqual(invoice.invoice_payment_state, 'paid')

        # Use case:
        # Company is in EUR, create a vendor bill for 25 EUR and register payment of 25 USD.
        # Mark invoice as fully paid with a write_off
        # Check that all the aml are correctly created.
        invoice = self.create_invoice(amount=25, type='in_invoice', currency_id=self.currency_eur_id, partner=self.partner_agrolait.id)
        payable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'payable')
        # register payment on invoice
        payment = self.payment_model.create({'payment_type': 'outbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'supplier',
            'partner_id': self.partner_agrolait.id,
            'amount': 25,
            'currency_id': self.currency_usd_id,
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.account_receivable.id,
            'journal_id': self.bank_journal_euro.id,
            'invoice_ids': [(4, invoice.id, None)]
            })
        payment.post()
        self.assertRecordValues(payment.move_line_ids, [
            {'account_id': payable_line.account_id.id, 'debit': 25.0, 'credit': 0.0, 'amount_currency': 38.22, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_eur.id, 'debit': 0.0, 'credit': 16.35, 'amount_currency': -25.0, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_receivable.id, 'debit': 0.0, 'credit': 8.65, 'amount_currency': -13.22, 'currency_id': self.currency_usd_id},
        ])
        self.assertTrue(payable_line.full_reconcile_id)
        self.assertEqual(invoice.invoice_payment_state, 'paid')

    def test_payment_and_writeoff_out_refund(self):
        # Use case:
        # Company is in EUR, create a credit note for 100 EUR and register payment of 90.
        # Mark invoice as fully paid with a write_off
        # Check that all the aml are correctly created.
        invoice = self.create_invoice(amount=100, type='out_refund', currency_id=self.currency_eur_id, partner=self.partner_agrolait.id)
        receivable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable')
        # register payment on invoice
        payment = self.payment_model.create({'payment_type': 'outbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait.id,
            'amount': 90,
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.account_payable.id,
            'journal_id': self.bank_journal_euro.id,
            'invoice_ids': [(4, invoice.id, None)]
            })
        payment.post()
        self.assertRecordValues(payment.move_line_ids, [
            {'account_id': receivable_line.account_id.id, 'debit': 100.0, 'credit': 0.0, 'amount_currency': 0.0, 'currency_id': False},
            {'account_id': self.account_eur.id, 'debit': 0.0, 'credit': 90.0, 'amount_currency': 0.0, 'currency_id': False},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 10.0, 'amount_currency': 0.0, 'currency_id': False},
        ])
        self.assertEqual(invoice.invoice_payment_state, 'paid')

    def test_payment_and_writeoff_in_other_currency_2(self):
        # Use case:
        # Company is in EUR, create a supplier bill of 5325.6 USD and register payment of 5325 USD, at a different rate
        # Mark invoice as fully paid with a write_off
        # Check that all the aml are correctly created.

        # Set exchange rates  0.895@2017-11-01 and 0.88@2017-12-01
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'rate': 0.895,
            'name': time.strftime('%Y') + '-06-26'})
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'rate': 0.88,
            'name': time.strftime('%Y') + '-07-15'})

        invoice = self.create_invoice(amount=5325.6, type='in_invoice', currency_id=self.currency_usd_id, partner=self.partner_agrolait.id)
        payable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'payable')

        # register payment on invoice
        payment = self.payment_model.create({'payment_type': 'outbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'supplier',
            'partner_id': self.partner_agrolait.id,
            'amount': 5325,
            'currency_id': self.currency_usd_id,
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.account_revenue.id,
            'journal_id': self.bank_journal_euro.id,
            'invoice_ids': [(4, invoice.id, None)]
            })
        payment.post()
        self.assertRecordValues(payment.move_line_ids, [
            {'debit': 6051.82,  'credit': 0.0,      'amount_currency': 5325.6,      'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 6051.14,  'amount_currency': -5325.0,     'currency_id': self.currency_usd_id},
            {'debit': 0.0,      'credit': 0.68,     'amount_currency': -0.6,        'currency_id': self.currency_usd_id},
        ])
        exchange_lines = payable_line.full_reconcile_id.exchange_move_id.line_ids
        self.assertRecordValues(exchange_lines, [
            {'debit': 0.0,     'credit': 101.43,   'account_id': payable_line.account_id.id},
            {'debit': 101.43,  'credit': 0.0,      'account_id': self.diff_expense_account.id},
        ])

        #check the invoice status
        self.assertEqual(invoice.invoice_payment_state, 'paid')

    def test_payment_and_writeoff_in_other_currency_3(self):
        # Use case related in revision 20935462a0cabeb45480ce70114ff2f4e91eaf79
        # Invoice made in secondary currency for which the rate to the company currency
        # is higher than the foreign currency decimal precision.
        # E.g: Company currency is EUR, create a customer invoice of 247590.40 EUR and
        #       register payment of 267 USD (1 USD = 948 EUR)
        #      Mark invoice as fully paid with a write_off
        #      Check that all the aml are correctly created and that the invoice is paid

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_usd_id,
            'rate': 1,
            'name': time.strftime('%Y') + '-06-26'})
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_eur_id,
            'rate': 948,
            'name': time.strftime('%Y') + '-06-26'})

        invoice = self.create_invoice(amount=247590.4, type='out_invoice', currency_id=self.currency_eur_id, partner=self.partner_agrolait.id)
        receivable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable')

        # register payment on invoice
        payment = self.payment_model.create({'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait.id,
            'amount': 267,
            'currency_id': self.currency_usd_id,
            'payment_date': time.strftime('%Y') + '-06-26',
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.account_revenue.id,
            'journal_id': self.bank_journal_euro.id,
            'invoice_ids': [(4, invoice.id, None)],
            'name': 'test_payment_and_writeoff_in_other_currency_3',
            })
        payment.post()
        self.assertRecordValues(payment.move_line_ids, [
            {'account_id': receivable_line.account_id.id, 'debit': 0.0, 'credit': 247589.16, 'amount_currency': -261.17, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_eur.id, 'debit': 253116.0, 'credit': 0.0, 'amount_currency': 267.0, 'currency_id': self.currency_usd_id},
            {'account_id': self.account_revenue.id, 'debit': 0.0, 'credit': 5526.84, 'amount_currency': -5.83, 'currency_id': self.currency_usd_id},
        ])

        # Check the invoice status and the full reconciliation: the difference on the receivable account
        # should have been completed by an exchange rate difference entry
        self.assertEqual(invoice.invoice_payment_state, 'paid')
        self.assertTrue(receivable_line.full_reconcile_id)

    def test_post_at_bank_reconciliation_payment(self):
        # Create two new payments in a journal requiring the journal entries to be posted at bank reconciliation
        post_at_bank_rec_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'COUCOU',
            'post_at_bank_rec': True,
        })
        payment_one = self.payment_model.create({'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait.id,
            'amount': 42,
            'payment_date': time.strftime('%Y') + '-07-15',
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.account_receivable.id,
            'journal_id': post_at_bank_rec_journal.id,
            })
        payment_one.post()
        payment_two = self.payment_model.create({'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait.id,
            'amount': 11,
            'payment_date': time.strftime('%Y') + '-12-15',
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.account_receivable.id,
            'journal_id': post_at_bank_rec_journal.id,
            })
        payment_two.post()

        # Check the payments and their move state
        self.assertEqual(payment_one.state, 'posted', "Payment one shoud be in posted state.")
        self.assertEqual(payment_one.mapped('move_line_ids.move_id.state'), ['draft'], "A posted payment (payment_one) in a bank journal with the 'post at bank reconciliation' option activated should correspond to a draft account.move")
        self.assertEqual(payment_two.state, 'posted', "Payment two shoud be in posted state.")
        self.assertEqual(payment_two.mapped('move_line_ids.move_id.state'), ['draft'], "A posted payment (payment_two) in a bank journal with the 'post at bank reconciliation' option activated should correspond to a draft account.move")

        # Reconcile the two payments with an invoice, whose full amount is equal to their sum
        invoice = self.create_invoice(amount=53, partner=self.partner_agrolait.id)
        (payment_one.move_line_ids + payment_two.move_line_ids + invoice.line_ids).filtered(lambda x: x.account_id.user_type_id.type == 'receivable').reconcile()

        self.assertEqual(invoice.invoice_payment_state, 'in_payment', "Invoice should be in 'in payment' state")

        # Match the first payment with a bank statement line
        bank_statement_one = self.reconcile(payment_one.move_line_ids.filtered(lambda x: x.account_id.user_type_id.type == 'liquidity'), 42)
        stmt_line_date_one = bank_statement_one.mapped('line_ids.date')

        self.assertEqual(payment_one.mapped('move_line_ids.move_id.state'), ['posted'], "After bank reconciliation, payment one's account.move should be posted.")
        self.assertEqual(payment_one.mapped('move_line_ids.move_id.date'), stmt_line_date_one, "After bank reconciliation, payment one's account.move should share the same date as the bank statement.")
        self.assertEqual([payment_one.payment_date], stmt_line_date_one, "After bank reconciliation, payment one should share the same date as the bank statement.")
        self.assertEqual(invoice.invoice_payment_state, 'in_payment', "The invoice should still be 'in payment', not all its payments are reconciled with a statement")

        # Match the second payment with a bank statement line
        bank_statement_two = self.reconcile(payment_two.move_line_ids.filtered(lambda x: x.account_id.user_type_id.type == 'liquidity'), 42)
        stmt_line_date_two = bank_statement_two.mapped('line_ids.date')

        self.assertEqual(payment_two.mapped('move_line_ids.move_id.state'), ['posted'], "After bank reconciliation, payment two's account.move should be posted.")
        self.assertEqual(payment_two.mapped('move_line_ids.move_id.date'), stmt_line_date_two, "After bank reconciliation, payment two's account.move should share the same date as the bank statement.")
        self.assertEqual([payment_two.payment_date], stmt_line_date_two, "After bank reconciliation, payment two should share the same date as the bank statement.")

        # The invoice should now be paid
        self.assertEqual(invoice.invoice_payment_state, 'paid', "Invoice should be in 'paid' state after having reconciled the two payments with a bank statement")
