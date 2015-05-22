from openerp.addons.account.tests.account_test_classes import AccountingTestCase
import time

class TestReconciliation(AccountingTestCase):

    """Tests for reconciliation (account.tax)

    Test used to check that when doing a sale or purchase invoice in a different currency,
    the result will be balanced.
    """

    def setUp(self):
        super(TestReconciliation, self).setUp()
        self.account_invoice_model = self.env['account.invoice']
        self.account_invoice_line_model = self.env['account.invoice.line']
        self.acc_bank_stmt_model = self.env['account.bank.statement']
        self.acc_bank_stmt_line_model = self.env['account.bank.statement.line']

        self.partner_agrolait_id = self.env.ref("base.res_partner_2").id
        self.currency_swiss_id = self.env.ref("base.CHF").id
        self.currency_usd_id = self.env.ref("base.USD").id
        self.currency_euro_id = self.env.ref("base.EUR").id
        self.env.ref('base.main_company').write({'currency_id': self.currency_euro_id})
        self.account_rcv = self.env['account.account'].search([('user_type', '=', self.env.ref('account.data_account_type_receivable').id)])[0]
        self.account_rsa = self.env['account.account'].search([('user_type', '=', self.env.ref('account.data_account_type_payable').id)])[0]
        self.product = self.env.ref("product.product_product_4")

        self.bank_euro = self.env['res.partner.bank'].create({'acc_number': 'Reconciliation test', 'bank_name': 'Test Bank', 'company_id': self.env.user.company_id.id})
        self.bank_journal_euro = self.bank_euro.journal_id
        self.account_euro = self.bank_journal_euro.default_debit_account_id

        self.bank_usd = self.env['res.partner.bank'].create({'acc_number': 'Reconciliation test USD',
                                                             'bank_name': 'Test Bank USD', 'company_id': self.env.user.company_id.id})
        self.bank_journal_usd = self.bank_usd.journal_id
        self.account_usd = self.bank_journal_usd.default_debit_account_id
        self.account_usd.write({'currency_id': self.currency_usd_id})
        self.bank_journal_usd.write({'currency_id': self.currency_usd_id})
        self.diff_income_account = self.env['res.users'].browse(self.env.uid).company_id.income_currency_exchange_account_id
        self.diff_expense_account = self.env['res.users'].browse(self.env.uid).company_id.expense_currency_exchange_account_id

    def create_invoice(self, type='out_invoice', currency_id=None):
        #we create an invoice in given currency
        invoice = self.account_invoice_model.create({'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'currency_id': currency_id,
            'name': type == 'out_invoice' and 'invoice to client' or 'invoice to supplier',
            'account_id': self.account_rcv.id,
            'type': type,
            'date_invoice': time.strftime('%Y') + '-07-01',
            })
        self.account_invoice_line_model.create({'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            'account_id': self.env['account.account'].search([('user_type', '=', self.env.ref('account.data_account_type_revenue').id)])[0].id,
        })

        #validate invoice
        invoice.signal_workflow('invoice_open')
        return invoice

    def make_payment(self, invoice_record, bank_journal, amount=0.0, amount_currency=0.0, currency_id=None):
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': bank_journal.id,
            'date': time.strftime('%Y') + '-07-15',
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': amount,
            'amount_currency': amount_currency,
            'currency_id': currency_id,
            'date': time.strftime('%Y') + '-07-15',})

        #reconcile the payment with the invoice
        for l in invoice_record.move_id.line_ids:
            if l.account_id.id == self.account_rcv.id:
                line_id = l
                break
        amount_in_widget = currency_id and amount_currency or amount
        bank_stmt_line.process_reconciliation(counterpart_aml_dicts=[{
            'move_line': line_id,
            'debit': amount_in_widget < 0 and -amount_in_widget or 0.0,
            'credit': amount_in_widget > 0 and amount_in_widget or 0.0,
            'name': line_id.name,
            }])
        return bank_stmt

    def check_results(self, move_line_recs, aml_dict):
        #we check that the line is balanced (bank statement line)
        self.assertEquals(len(move_line_recs), len(aml_dict))
        for move_line in move_line_recs:
            self.assertEquals(round(move_line.debit, 2), aml_dict[move_line.account_id.id]['debit'])
            self.assertEquals(round(move_line.credit, 2), aml_dict[move_line.account_id.id]['credit'])
            self.assertEquals(round(move_line.amount_currency, 2), aml_dict[move_line.account_id.id]['amount_currency'])
            self.assertEquals(move_line.currency_id.id, aml_dict[move_line.account_id.id]['currency_id'])
            if aml_dict[move_line.account_id.id].get('currency_diff'):
                if move_line.credit:
                    rec_ids = [r.id for r in move_line.matched_debit_ids]
                else:
                    rec_ids = [r.id for r in move_line.matched_credit_ids]
                currency_diff_move = self.env['account.move'].search([('rate_diff_partial_rec_id', 'in', rec_ids)])
                self.assertEqual(len(currency_diff_move), 1)
                for currency_diff_line in currency_diff_move[0].line_ids:
                    if aml_dict[move_line.account_id.id].get('currency_diff') > 0:
                        if currency_diff_line.account_id.id == move_line.account_id.id:
                            self.assertAlmostEquals(currency_diff_line.debit, aml_dict[move_line.account_id.id].get('currency_diff'))
                        else:
                            self.assertAlmostEquals(currency_diff_line.credit, aml_dict[move_line.account_id.id].get('currency_diff'))
                            self.assertIn(currency_diff_line.account_id.id, [self.diff_expense_account.id, self.diff_income_account.id], 'The difference accounts should be used correctly. ')
                            #self.assertEquals(currency_diff_line.account_id.id, self.account_rsa.id)
                    else:
                        if currency_diff_line.account_id.id == move_line.account_id.id:
                            self.assertAlmostEquals(currency_diff_line.credit, abs(aml_dict[move_line.account_id.id].get('currency_diff')))
                        else:
                            self.assertAlmostEquals(currency_diff_line.debit, abs(aml_dict[move_line.account_id.id].get('currency_diff')))
                            self.assertIn(currency_diff_line.account_id.id, [self.diff_expense_account.id, self.diff_income_account.id], 'The difference accounts should be used correctly. ')
                            #self.assertEquals(currency_diff_line.account_id.id, self.account_rsa.id)

    def make_customer_and_supplier_flows(self, invoice_currency_id, bank_journal, amount, amount_currency, transaction_currency_id):
        #we create an invoice in given invoice_currency
        invoice_record = self.create_invoice(type='out_invoice', currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=amount, amount_currency=amount_currency, currency_id=transaction_currency_id)
        customer_move_lines = bank_stmt.move_line_ids

        #we create a supplier bill in given invoice_currency
        invoice_record = self.create_invoice(type='in_invoice', currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=-amount, amount_currency=-amount_currency, currency_id=transaction_currency_id)
        supplier_move_lines = bank_stmt.move_line_ids
        return customer_move_lines, supplier_move_lines

    def test_statement_usd_invoice_eur_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_euro_id, self.bank_journal_usd, 42, 30, self.currency_euro_id)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 30.0, 'credit': 0.0, 'amount_currency': 42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 30.0, 'amount_currency': -42, 'currency_id': self.currency_usd_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 30.0, 'amount_currency': -42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 30.0, 'credit': 0.0, 'amount_currency': 42, 'currency_id': self.currency_usd_id},
        })

    def test_statement_usd_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, self.bank_journal_usd, 50, 0, False)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 32.70, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 32.70, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 32.70, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 32.70, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
        })

    def test_statement_usd_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, self.bank_journal_usd, 50, 40, self.currency_euro_id)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id, 'currency_diff': 7.30},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id, 'currency_diff': -7.30},
        })

    def test_statement_usd_invoice_chf_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_swiss_id, self.bank_journal_usd, 42, 50, self.currency_swiss_id)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 27.47, 'credit': 0.0, 'amount_currency': 42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 27.47, 'amount_currency': -50, 'currency_id': self.currency_swiss_id, 'currency_diff': -10.74},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 27.47, 'amount_currency': -42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 27.47, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_swiss_id, 'currency_diff': 10.74},
        })

    def test_statement_eur_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, self.bank_journal_euro, 40, 50, self.currency_usd_id)
        self.check_results(customer_move_lines, {
            self.account_euro.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id, 'currency_diff': 7.30},
        })
        self.check_results(supplier_move_lines, {
            self.account_euro.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id, 'currency_diff': -7.30},
        })

    def test_statement_eur_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, self.bank_journal_euro, 40, 0.0, False)
        self.check_results(customer_move_lines, {
            self.account_euro.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 0.0, 'currency_id': False},
            self.account_rcv.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -61.16, 'currency_id': self.currency_usd_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_euro.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': 0.0, 'currency_id': False},
            self.account_rcv.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 61.16, 'currency_id': self.currency_usd_id},
        })

    def test_statement_euro_invoice_usd_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, self.bank_journal_euro, 42, 50, self.currency_swiss_id)
        self.check_results(customer_move_lines, {
            self.account_euro.id: {'debit': 42.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_swiss_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 42.0, 'amount_currency': -50, 'currency_id': self.currency_swiss_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_euro.id: {'debit': 0.0, 'credit': 42.0, 'amount_currency': -50, 'currency_id': self.currency_swiss_id},
            self.account_rcv.id: {'debit': 42.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_swiss_id},
        })
