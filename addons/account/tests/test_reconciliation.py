from openerp.tests.common import TransactionCase
import time

class TestReconciliation(TransactionCase):
    """Tests for reconciliation (account.tax)

    Test used to check that when doing a sale or purchase invoice in a different currency,
    the result will be balanced.
    """

    def setUp(self):
        super(TestReconciliation, self).setUp()
        self.account_invoice_model = self.registry('account.invoice')
        self.account_invoice_line_model = self.registry('account.invoice.line')
        self.acc_bank_stmt_model = self.registry('account.bank.statement')
        self.acc_bank_stmt_line_model = self.registry('account.bank.statement.line')
        self.res_currency_model = self.registry('res.currency')
        self.res_currency_rate_model = self.registry('res.currency.rate')
        
        self.partner_agrolait_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "res_partner_2")[1]
        self.currency_swiss_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "CHF")[1]
        self.currency_usd_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "USD")[1]
        self.account_rcv_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "a_recv")[1]
        self.account_fx_income_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "income_fx_income")[1]
        self.account_fx_expense_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "income_fx_expense")[1]

        self.product_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "product", "product_product_4")[1]
        
        self.bank_journal_usd_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "bank_journal_usd")[1]
        self.account_usd_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "usd_bnk")[1]
        
        self.company_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "main_company")[1]

        #set expense_currency_exchange_account_id and income_currency_exchange_account_id to the according accounts
        self.registry("res.company").write(self.cr, self.uid, [self.company_id], {'expense_currency_exchange_account_id': self.account_fx_expense_id, 'income_currency_exchange_account_id':self.account_fx_income_id})

    def test_balanced_customer_invoice(self):
        cr, uid = self.cr, self.uid
        #we create an invoice in CHF
        invoice_id = self.account_invoice_model.create(cr, uid, {'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'currency_id': self.currency_swiss_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y')+'-07-01', # to use USD rate rateUSDbis
            })
        self.account_invoice_line_model.create(cr, uid, {'product_id': self.product_id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice_id,
            'name': 'product that cost 100',})

        #validate purchase
        self.registry('account.invoice').signal_workflow(cr, uid, [invoice_id], 'invoice_open')        
        invoice_record = self.account_invoice_model.browse(cr, uid, [invoice_id])

        #we pay half of it on a journal with currency in dollar (bank statement)
        bank_stmt_id = self.acc_bank_stmt_model.create(cr, uid, {
            'journal_id': self.bank_journal_usd_id,
            'date': time.strftime('%Y')+'-07-15',
        })

        bank_stmt_line_id = self.acc_bank_stmt_line_model.create(cr, uid, {'name': 'half payment',
            'statement_id': bank_stmt_id,
            'partner_id': self.partner_agrolait_id,
            'amount': 42,
            'amount_currency': 50,
            'currency_id': self.currency_swiss_id,
            'date': time.strftime('%Y')+'-07-15',})

        #reconcile the payment with the invoice
        for l in invoice_record.move_id.line_id:
            if l.account_id.id == self.account_rcv_id:
                line_id = l
                break
        self.acc_bank_stmt_line_model.process_reconciliation(cr, uid, bank_stmt_line_id, [
            {'counterpart_move_line_id': line_id.id, 'credit':50, 'debit':0, 'name': line_id.name,}])

        #we check that the line is balanced (bank statement line)
        move_line_ids = self.acc_bank_stmt_model.browse(cr,uid,bank_stmt_id).move_line_ids

        self.assertEquals(len(move_line_ids), 3)
        checked_line = 0
        for move_line in move_line_ids:
            if move_line.account_id.id == self.account_usd_id:
                self.assertEquals(move_line.debit, 27.47)
                self.assertEquals(move_line.credit, 0.0)
                self.assertEquals(move_line.amount_currency, 42)
                self.assertEquals(move_line.currency_id.id, self.currency_usd_id)
                checked_line += 1
                continue
            if move_line.account_id.id == self.account_rcv_id:
                self.assertEquals(move_line.debit, 0.0)
                self.assertEquals(move_line.credit, 38.21)
                self.assertEquals(move_line.amount_currency, -50)
                self.assertEquals(move_line.currency_id.id, self.currency_swiss_id)
                checked_line += 1
                continue
            if move_line.account_id.id == self.account_fx_expense_id:
                self.assertEquals(move_line.debit, 10.74)
                self.assertEquals(move_line.credit, 0.0)
                checked_line += 1
                continue
        self.assertEquals(checked_line, 3)

        

    def test_balanced_supplier_invoice(self):
        cr, uid = self.cr, self.uid
        #we create a supplier invoice in CHF
        invoice_id = self.account_invoice_model.create(cr, uid, {'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'currency_id': self.currency_swiss_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'in_invoice',
            'date_invoice': time.strftime('%Y')+'-07-01',
            })
        self.account_invoice_line_model.create(cr, uid, {'product_id': self.product_id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice_id,
            'name': 'product that cost 100',})

        #validate purchase
        self.registry('account.invoice').signal_workflow(cr, uid, [invoice_id], 'invoice_open')        
        invoice_record = self.account_invoice_model.browse(cr, uid, [invoice_id])

        #we pay half of it on a journal with currency in dollar (bank statement)
        bank_stmt_id = self.acc_bank_stmt_model.create(cr, uid, {
            'journal_id': self.bank_journal_usd_id,
            'date': time.strftime('%Y')+'-07-15',
        })

        bank_stmt_line_id = self.acc_bank_stmt_line_model.create(cr, uid, {'name': 'half payment',
            'statement_id': bank_stmt_id,
            'partner_id': self.partner_agrolait_id,
            'amount': -42,
            'amount_currency': -50,
            'currency_id': self.currency_swiss_id,
            'date': time.strftime('%Y')+'-07-15',})

        #reconcile the payment with the invoice
        for l in invoice_record.move_id.line_id:
            if l.account_id.id == self.account_rcv_id:
                line_id = l
                break
        self.acc_bank_stmt_line_model.process_reconciliation(cr, uid, bank_stmt_line_id, [
            {'counterpart_move_line_id': line_id.id, 'credit':0, 'debit':50, 'name': line_id.name,}])

        #we check that the line is balanced (bank statement line)
        move_line_ids = self.acc_bank_stmt_model.browse(cr,uid,bank_stmt_id).move_line_ids

        self.assertEquals(len(move_line_ids), 3)
        checked_line = 0
        for move_line in move_line_ids:
            if move_line.account_id.id == self.account_usd_id:
                self.assertEquals(move_line.debit, 0.0)
                self.assertEquals(move_line.credit, 27.47)
                self.assertEquals(move_line.amount_currency, -42)
                self.assertEquals(move_line.currency_id.id, self.currency_usd_id)
                checked_line += 1
                continue
            if move_line.account_id.id == self.account_rcv_id:
                self.assertEquals(move_line.debit, 38.21)
                self.assertEquals(move_line.credit, 0.0)
                self.assertEquals(move_line.amount_currency, 50)
                self.assertEquals(move_line.currency_id.id, self.currency_swiss_id)
                checked_line += 1
                continue
            if move_line.account_id.id == self.account_fx_income_id:
                self.assertEquals(move_line.debit, 0.0)
                self.assertEquals(move_line.credit, 10.74)
                checked_line += 1
                continue
        self.assertEquals(checked_line, 3)

    def test_balanced_exchanges_gain_loss(self):
        # The point of this test is to show that we handle correctly the gain/loss exchanges during reconciliations in foreign currencies.
        # For instance, with a company set in EUR, and a USD rate set to 0.033,
        # the reconciliation of an invoice of 2.00 USD (60.61 EUR) and a bank statement of two lines of 1.00 USD (30.30 EUR)
        # will lead to an exchange loss, that should be handled correctly within the journal items.
        cr, uid = self.cr, self.uid
        # We update the currency rate of the currency USD in order to force the gain/loss exchanges in next steps
        self.res_currency_rate_model.create(cr, uid, {
            'name': time.strftime('%Y-%m-%d') + ' 00:00:00',
            'currency_id': self.currency_usd_id,
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
