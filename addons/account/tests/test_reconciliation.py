from openerp.tests.common import TransactionCase

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
        
        self.partner_agrolait_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "res_partner_2")[1]
        self.currency_swiss_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "CHF")[1]
        self.currency_usd_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "USD")[1]
        self.account_rcv_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "a_recv")[1]
        self.account_rsa_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "rsa")[1]
        self.product_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "product", "product_product_4")[1]
        
        self.bank_journal_usd_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "bank_journal_usd")[1]
        self.account_usd_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "usd_bnk")[1]
        
        self.company_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "main_company")[1]
        #set expense_currency_exchange_account_id and income_currency_exchange_account_id to a random account
        self.registry("res.company").write(self.cr, self.uid, [self.company_id], {'expense_currency_exchange_account_id': self.account_rsa_id, 'income_currency_exchange_account_id':self.account_rsa_id})

    def test_balanced_customer_invoice(self):
        cr, uid = self.cr, self.uid
        #we create an invoice in CHF
        invoice_id = self.account_invoice_model.create(cr, uid, {'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'currency_id': self.currency_swiss_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice'
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
        bank_stmt_id = self.acc_bank_stmt_model.create(cr, uid, {'journal_id': self.bank_journal_usd_id,})

        bank_stmt_line_id = self.acc_bank_stmt_line_model.create(cr, uid, {'name': 'half payment',
            'statement_id': bank_stmt_id,
            'partner_id': self.partner_agrolait_id,
            'amount': 42,
            'amount_currency': 50,
            'currency_id': self.currency_swiss_id,})

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
            if move_line.account_id.id == self.account_rsa_id:
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
            'type': 'in_invoice'
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
        bank_stmt_id = self.acc_bank_stmt_model.create(cr, uid, {'journal_id': self.bank_journal_usd_id,})

        bank_stmt_line_id = self.acc_bank_stmt_line_model.create(cr, uid, {'name': 'half payment',
            'statement_id': bank_stmt_id,
            'partner_id': self.partner_agrolait_id,
            'amount': -42,
            'amount_currency': -50,
            'currency_id': self.currency_swiss_id,})

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
            if move_line.account_id.id == self.account_rsa_id:
                self.assertEquals(move_line.debit, 0.0)
                self.assertEquals(move_line.credit, 10.74)
                checked_line += 1
                continue
        self.assertEquals(checked_line, 3)

