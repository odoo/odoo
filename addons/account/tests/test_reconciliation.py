from openerp.addons.account.tests.account_test_classes import AccountingTestCase
import time
import unittest

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
        self.res_currency_model = self.registry('res.currency')
        self.res_currency_rate_model = self.registry('res.currency.rate')

        self.partner_agrolait_id = self.env.ref("base.res_partner_2").id
        self.currency_swiss_id = self.env.ref("base.CHF").id
        self.currency_usd_id = self.env.ref("base.USD").id
        self.currency_euro_id = self.env.ref("base.EUR").id
        self.env.ref('base.main_company').write({'currency_id': self.currency_euro_id})
        self.account_rcv = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        self.account_rsa = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_payable').id)], limit=1)
        self.product = self.env.ref("product.product_product_4")

        self.bank_journal_euro = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        self.account_euro = self.bank_journal_euro.default_debit_account_id

        self.bank_journal_usd = self.env['account.journal'].create({'name': 'Bank US', 'type': 'bank', 'code': 'BNK68', 'currency_id': self.currency_usd_id})
        self.account_usd = self.bank_journal_usd.default_debit_account_id
        
        self.diff_income_account = self.env['res.users'].browse(self.env.uid).company_id.income_currency_exchange_account_id
        self.diff_expense_account = self.env['res.users'].browse(self.env.uid).company_id.expense_currency_exchange_account_id

    def create_invoice(self, type='out_invoice', invoice_amount=50, currency_id=None):
        #we create an invoice in given currency
        invoice = self.account_invoice_model.create({'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'currency_id': currency_id,
            'name': type == 'out_invoice' and 'invoice to client' or 'invoice to vendor',
            'account_id': self.account_rcv.id,
            'type': type,
            'date_invoice': time.strftime('%Y') + '-07-01',
            })
        self.account_invoice_line_model.create({'product_id': self.product.id,
            'quantity': 1,
            'price_unit': invoice_amount,
            'invoice_id': invoice.id,
            'name': 'product that cost ' + str(invoice_amount),
            'account_id': self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
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
            if 'currency_diff' in aml_dict[move_line.account_id.id]:
                if move_line.credit:
                    rec_ids = [r.id for r in move_line.matched_debit_ids]
                else:
                    rec_ids = [r.id for r in move_line.matched_credit_ids]
                currency_diff_move = self.env['account.move'].search([('rate_diff_partial_rec_id', 'in', rec_ids)])
                self.assertEqual(len(currency_diff_move), 1)
                for currency_diff_line in currency_diff_move[0].line_ids:
                    if aml_dict[move_line.account_id.id].get('currency_diff') == 0:
                        if currency_diff_line.account_id.id == move_line.account_id.id:
                            self.assertAlmostEquals(currency_diff_line.amount_currency, aml_dict[move_line.account_id.id].get('amount_currency_diff'))
                    if aml_dict[move_line.account_id.id].get('currency_diff') > 0:
                        if currency_diff_line.account_id.id == move_line.account_id.id:
                            self.assertAlmostEquals(currency_diff_line.debit, aml_dict[move_line.account_id.id].get('currency_diff'))
                        else:
                            self.assertAlmostEquals(currency_diff_line.credit, aml_dict[move_line.account_id.id].get('currency_diff'))
                            self.assertIn(currency_diff_line.account_id.id, [self.diff_expense_account.id, self.diff_income_account.id], 'The difference accounts should be used correctly. ')
                    else:
                        if currency_diff_line.account_id.id == move_line.account_id.id:
                            self.assertAlmostEquals(currency_diff_line.credit, abs(aml_dict[move_line.account_id.id].get('currency_diff')))
                        else:
                            self.assertAlmostEquals(currency_diff_line.debit, abs(aml_dict[move_line.account_id.id].get('currency_diff')))
                            self.assertIn(currency_diff_line.account_id.id, [self.diff_expense_account.id, self.diff_income_account.id], 'The difference accounts should be used correctly. ')

    def make_customer_and_supplier_flows(self, invoice_currency_id, invoice_amount, bank_journal, amount, amount_currency, transaction_currency_id):
        #we create an invoice in given invoice_currency
        invoice_record = self.create_invoice(type='out_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=amount, amount_currency=amount_currency, currency_id=transaction_currency_id)
        customer_move_lines = bank_stmt.move_line_ids

        #we create a supplier bill in given invoice_currency
        invoice_record = self.create_invoice(type='in_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=-amount, amount_currency=-amount_currency, currency_id=transaction_currency_id)
        supplier_move_lines = bank_stmt.move_line_ids
        return customer_move_lines, supplier_move_lines

    def test_statement_usd_invoice_eur_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_euro_id, 30, self.bank_journal_usd, 42, 30, self.currency_euro_id)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 30.0, 'credit': 0.0, 'amount_currency': 42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 30.0, 'amount_currency': -42, 'currency_id': self.currency_usd_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 30.0, 'amount_currency': -42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 30.0, 'credit': 0.0, 'amount_currency': 42, 'currency_id': self.currency_usd_id},
        })

    def test_statement_usd_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_usd, 50, 0, False)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 32.70, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 32.70, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 32.70, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 32.70, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
        })

    def test_statement_usd_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_usd, 50, 40, self.currency_euro_id)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id, 'currency_diff': 7.30},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id, 'currency_diff': -7.30},
        })

    def test_statement_usd_invoice_chf_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_swiss_id, 50, self.bank_journal_usd, 42, 50, self.currency_swiss_id)
        self.check_results(customer_move_lines, {
            self.account_usd.id: {'debit': 27.47, 'credit': 0.0, 'amount_currency': 42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 27.47, 'amount_currency': -50, 'currency_id': self.currency_swiss_id, 'currency_diff': -10.74},
        })
        self.check_results(supplier_move_lines, {
            self.account_usd.id: {'debit': 0.0, 'credit': 27.47, 'amount_currency': -42, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 27.47, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_swiss_id, 'currency_diff': 10.74},
        })

    def test_statement_eur_invoice_usd_transaction_usd(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 40, 50, self.currency_usd_id)
        self.check_results(customer_move_lines, {
            self.account_euro.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id, 'currency_diff': 7.30},
        })
        self.check_results(supplier_move_lines, {
            self.account_euro.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -50, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_usd_id, 'currency_diff': -7.30},
        })

    def test_statement_eur_invoice_usd_transaction_eur(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 40, 0.0, False)
        self.check_results(customer_move_lines, {
            self.account_euro.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 0.0, 'currency_id': False},
            self.account_rcv.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': -61.16, 'currency_id': self.currency_usd_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_euro.id: {'debit': 0.0, 'credit': 40.0, 'amount_currency': 0.0, 'currency_id': False},
            self.account_rcv.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 61.16, 'currency_id': self.currency_usd_id},
        })

    def test_statement_euro_invoice_usd_transaction_chf(self):
        customer_move_lines, supplier_move_lines = self.make_customer_and_supplier_flows(self.currency_usd_id, 50, self.bank_journal_euro, 42, 50, self.currency_swiss_id)
        self.check_results(customer_move_lines, {
            self.account_euro.id: {'debit': 42.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_swiss_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 42.0, 'amount_currency': -50, 'currency_id': self.currency_swiss_id},
        })
        self.check_results(supplier_move_lines, {
            self.account_euro.id: {'debit': 0.0, 'credit': 42.0, 'amount_currency': -50, 'currency_id': self.currency_swiss_id},
            self.account_rcv.id: {'debit': 42.0, 'credit': 0.0, 'amount_currency': 50, 'currency_id': self.currency_swiss_id},
        })

    def test_statement_euro_invoice_usd_transaction_euro_full(self):
        #we create an invoice in given invoice_currency
        invoice_record = self.create_invoice(type='out_invoice', invoice_amount=50, currency_id=self.currency_usd_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_euro.id,
            'date': time.strftime('%Y') + '-01-01',
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': 40,
            'date': time.strftime('%Y') + '-01-01',})

        #reconcile the payment with the invoice
        for l in invoice_record.move_id.line_ids:
            if l.account_id.id == self.account_rcv.id:
                line_id = l
                break
        bank_stmt_line.process_reconciliation(counterpart_aml_dicts=[{
              'move_line': line_id,
              'debit': 0.0,
              'credit': 32.7,
              'name': line_id.name,
            }], new_aml_dicts=[{
              'debit': 0.0,
              'credit': 7.3,
              'name': 'exchange difference',
              'account_id': self.diff_income_account.id
            }])
        self.check_results(bank_stmt.move_line_ids, {
            self.account_euro.id: {'debit': 40.0, 'credit': 0.0, 'amount_currency': 0, 'currency_id': False},
            self.account_rcv.id: {'debit': 0.0, 'credit': 32.7, 'amount_currency': -41.97, 'currency_id': self.currency_usd_id, 'currency_diff': 0, 'amount_currency_diff': -8.03},
            self.diff_income_account.id: {'debit': 0.0, 'credit': 7.3, 'amount_currency': -9.37, 'currency_id': self.currency_usd_id},
        })

        # The invoice should be paid, as the payments totally cover its total
        self.assertEquals(invoice_record.state, 'paid', 'The invoice should be paid by now')
        invoice_rec_line = invoice_record.move_id.line_ids.filtered(lambda x: x.account_id.reconcile)
        self.assertTrue(invoice_rec_line.reconciled, 'The invoice should be totally reconciled')
        self.assertEquals(invoice_rec_line.amount_residual, 0, 'The invoice should be totally reconciled')
        self.assertEquals(invoice_rec_line.amount_residual_currency, 0, 'The invoice should be totally reconciled')

    @unittest.skip('adapt to new accounting')
    def test_balanced_exchanges_gain_loss(self):
        # The point of this test is to show that we handle correctly the gain/loss exchanges during reconciliations in foreign currencies.
        # For instance, with a company set in EUR, and a USD rate set to 0.033,
        # the reconciliation of an invoice of 2.00 USD (60.61 EUR) and a bank statement of two lines of 1.00 USD (30.30 EUR)
        # will lead to an exchange loss, that should be handled correctly within the journal items.
        cr, uid = self.cr, self.uid
        # We update the currency rate of the currency USD in order to force the gain/loss exchanges in next steps
        rateUSDbis_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "rateUSDbis")[1]
        self.res_currency_rate_model.write(cr, uid, rateUSDbis_id, {
            'name': time.strftime('%Y-%m-%d') + ' 00:00:00',
            'rate': 0.033,
        })
        # We create a customer invoice of 2.00 USD
        invoice_id = self.account_invoice_model.create(cr, uid, {
            'partner_id': self.partner_agrolait_id,
            'currency_id': self.currency_usd_id,
            'name': 'Foreign invoice with exchange gain',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y-%m-%d'),
            'journal_id': self.bank_journal_usd_id,
            'invoice_line': [
                (0, 0, {
                    'name': 'line that will lead to an exchange gain',
                    'quantity': 1,
                    'price_unit': 2,
                })
            ]
        })
        self.registry('account.invoice').signal_workflow(cr, uid, [invoice_id], 'invoice_open')
        invoice = self.account_invoice_model.browse(cr, uid, invoice_id)
        # We create a bank statement with two lines of 1.00 USD each.
        bank_stmt_id = self.acc_bank_stmt_model.create(cr, uid, {
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

        statement = self.acc_bank_stmt_model.browse(cr, uid, bank_stmt_id)

        # We process the reconciliation of the invoice line with the two bank statement lines
        line_id = None
        for l in invoice.move_id.line_id:
            if l.account_id.id == self.account_rcv_id:
                line_id = l
                break
        for statement_line in statement.line_ids:
            self.acc_bank_stmt_line_model.process_reconciliation(cr, uid, statement_line.id, [
                {'counterpart_move_line_id': line_id.id, 'credit': 1.0, 'debit': 0.0, 'name': line_id.name}
            ])

        # The invoice should be paid, as the payments totally cover its total
        self.assertEquals(invoice.state, 'paid', 'The invoice should be paid by now')
        reconcile = None
        for payment in invoice.payment_ids:
            reconcile = payment.reconcile_id
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
        self.assertEquals(sum([res['debit'] for res in result.values()]), 60.61)
        self.assertEquals(sum([res['credit'] for res in result.values()]), 60.61)
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
            return self.env['account.move'].create(vals).id
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
        aml_recs = self.env['account.move.line'].search([('move_id', 'in', move_ids), ('account_id', '=', self.account_rcv.id)])
        wizard = self.env['account.move.line.reconcile'].with_context(active_ids=[x.id for x in aml_recs]).create({})
        wizard.trans_rec_reconcile_full()
        for aml in aml_recs:
            self.assertTrue(aml.reconciled, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual, 0, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual_currency, 0, 'The journal item should be totally reconciled')

        move_list_vals = [
            ('2', 728.35, 795.05, self.currency_swiss_id),
            ('3', -4.46, 0, False),
            ('4', 0.32, 0, False),
            ('5', 14.72, 16.20, self.currency_swiss_id),
            ('6', -737.10, -811.25, self.currency_swiss_id),
        ]
        move_ids = []
        for name, amount, amount_currency, currency_id in move_list_vals:
            move_ids.append(create_move(name, amount, amount_currency, currency_id))
        aml_recs = self.env['account.move.line'].search([('move_id', 'in', move_ids), ('account_id', '=', self.account_rcv.id)])
        wizard = self.env['account.move.line.reconcile.writeoff'].with_context(active_ids=[x.id for x in aml_recs]).create({'journal_id': self.bank_journal_usd.id, 'writeoff_acc_id': self.account_rsa.id})
        wizard.trans_rec_reconcile()
        for aml in aml_recs:
            self.assertTrue(aml.reconciled, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual, 0, 'The journal item should be totally reconciled')
            self.assertEquals(aml.amount_residual_currency, 0, 'The journal item should be totally reconciled')

    def test_reconcile_bank_statement_with_payment_and_writeoff(self):
        # Use case:
        # Company is in EUR, create a bill for 80 USD and register payment of 80 USD.
        # create a bank statement in USD bank journal with a bank statement line of 85 USD
        # Reconcile bank statement with payment and put the remaining 5 USD in bank fees or another account.

        invoice = self.create_invoice(type='out_invoice', invoice_amount=80, currency_id=self.currency_usd_id)
        # register payment on invoice
        payment = self.env['account.payment'].create({'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_agrolait_id,
            'amount': 80,
            'currency_id': self.currency_usd_id,
            'payment_date': time.strftime('%Y') + '-07-15',
            'journal_id': self.bank_journal_usd.id,
            })
        payment.post()
        payment_move_line = False
        bank_move_line = False
        for l in payment.move_line_ids:
            if l.account_id.id == self.account_rcv.id:
                payment_move_line = l
            else:
                bank_move_line = l
        invoice.register_payment(payment_move_line)

        # create bank statement
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_usd.id,
            'date': time.strftime('%Y') + '-07-15',
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': 85,
            'date': time.strftime('%Y') + '-07-15',})

        #reconcile the statement with invoice and put remaining in another account
        bank_stmt_line.process_reconciliation(payment_aml_rec= bank_move_line, new_aml_dicts=[{
            'account_id': self.diff_income_account.id,
            'debit': 0,
            'credit': 5,
            'name': 'bank fees',
            }])

        # Check that move lines associated to bank_statement are correct
        bank_stmt_aml = self.env['account.move.line'].search([('statement_id', '=', bank_stmt.id)])
        bank_stmt_aml |= bank_stmt_aml.mapped('move_id').mapped('line_ids')
        self.assertEquals(len(bank_stmt_aml), 4, "The bank statement should have 4 moves lines")
        lines = {
            self.account_usd.id: [
                {'debit': 3.27, 'credit': 0.0, 'amount_currency': 5, 'currency_id': self.currency_usd_id},
                {'debit': 52.33, 'credit': 0, 'amount_currency': 80, 'currency_id': self.currency_usd_id}
                ],
            self.diff_income_account.id: {'debit': 0.0, 'credit': 3.27, 'amount_currency': -5, 'currency_id': self.currency_usd_id},
            self.account_rcv.id: {'debit': 0.0, 'credit': 52.33, 'amount_currency': -80, 'currency_id': self.currency_usd_id},
        }
        for aml in bank_stmt_aml:
            line = lines[aml.account_id.id]
            if type(line) == list:
                # find correct line inside the list
                if line[0]['debit'] == round(aml.debit, 2):
                    line = line[0]
                else:
                    line = line[1]
            self.assertEquals(round(aml.debit, 2), line['debit'])
            self.assertEquals(round(aml.credit, 2), line['credit'])
            self.assertEquals(round(aml.amount_currency, 2), line['amount_currency'])
            self.assertEquals(aml.currency_id.id, line['currency_id'])