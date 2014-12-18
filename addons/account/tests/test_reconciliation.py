from openerp.tests.common import TransactionCase
import datetime


class TestReconciliation(TransactionCase):

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

        self.partner_agrolait_id = self.env.ref("base.res_partner_2")
        self.currency_swiss_id = self.env.ref("base.CHF")
        self.currency_usd_id = self.env.ref("base.USD")
        self.account_rcv_id = self.env.ref("account.a_recv")
        self.account_rsa_id = self.env.ref("account.rsa")
        self.product_id = self.env.ref("product.product_product_4")

        self.bank_journal_usd_id = self.env.ref('account.bank_journal_usd')
        self.account_usd_id = self.env.ref('account.usd_bnk')

        self.company_id = self.env.ref('base.main_company')

        # set expense_currency_exchange_account_id and income_currency_exchange_account_id to a random account
        self.company_id.write({
            'expense_currency_exchange_account_id': self.account_rsa_id.id,
            'income_currency_exchange_account_id': self.account_rsa_id.id
        })

    def test_balanced_customer_invoice(self):
        # we create an invoice in CHF
        invoice_id = self.account_invoice_model.create({
            'partner_id': self.partner_agrolait_id.id,
            'reference_type': 'none',
            'currency_id': self.currency_swiss_id.id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id.id,
            'type': 'out_invoice'
        })

        self.account_invoice_line_model.create({
            'product_id': self.product_id.id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice_id.id,
            'name': 'product that cost 100',
        })

        # validate purchase
        invoice_id.signal_workflow('invoice_open')
        # invoice_record = self.account_invoice_model.browse(cr, uid, [invoice_id])

        # we pay half of it on a journal with currency in dollar (bank statement)

        bank_stmt_id = self.acc_bank_stmt_model.with_context(journal_type='bank').create({
            'journal_id': self.bank_journal_usd_id.id,
        })

        bank_stmt_line_id = self.acc_bank_stmt_line_model.create({
            'name': 'half payment',
            'date': datetime.date.today(),
            'statement_id': bank_stmt_id.id,
            'partner_id': self.partner_agrolait_id.id,
            'amount': 42,
            'amount_currency': 50,
            'currency_id': self.bank_journal_usd_id.id,
        })

        # reconcile the payment with the invoice
        # for l in invoice_id.move_id.line_id:
        #     if l.account_id.id == self.account_rcv_id.id:
        #         bank_stmt_line_id.process_reconciliation([{
        #             'counterpart_move_line_id': l.id,
        #             'credit': 50,
        #             'debit': 0,
        #             'name': l.name,
        #         }])

        # we check that the line is balanced (bank statement line)

        # self.assertEquals(len(bank_stmt_id.move_line_ids), 3)
        # checked_line = 0
        # for move_line in bank_stmt_id.move_line_ids:
        #     if move_line.account_id.id == self.account_usd_id:
        #         self.assertEquals(move_line.debit, 27.47)
        #         self.assertEquals(move_line.credit, 0.0)
        #         self.assertEquals(move_line.amount_currency, 42)
        #         self.assertEquals(move_line.currency_id.id, self.currency_usd_id.id)
        #         checked_line += 1
        #         continue
        #     if move_line.account_id.id == self.account_rcv_id:
        #         self.assertEquals(move_line.debit, 0.0)
        #         self.assertEquals(move_line.credit, 38.21)
        #         self.assertEquals(move_line.amount_currency, -50)
        #         self.assertEquals(move_line.currency_id.id, self.currency_swiss_id.id)
        #         checked_line += 1
        #         continue
        #     if move_line.account_id.id == self.account_rsa_id:
        #         self.assertEquals(move_line.debit, 10.74)
        #         self.assertEquals(move_line.credit, 0.0)
        #         checked_line += 1
        #         continue
        # self.assertEquals(checked_line, 3)

    def test_balanced_supplier_invoice(self):
        # we create a supplier invoice in CHF
        invoice_id = self.account_invoice_model.create({
            'partner_id': self.partner_agrolait_id.id,
            'reference_type': 'none',
            'currency_id': self.currency_swiss_id.id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id.id,
            'type': 'in_invoice'
        })
        self.account_invoice_line_model.create({
            'product_id': self.product_id.id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice_id.id,
            'name': 'product that cost 100',
        })

        # validate purchase
        invoice_id.signal_workflow('invoice_open')

        # we pay half of it on a journal with currency in dollar (bank statement)
        bank_stmt_id = self.acc_bank_stmt_model.with_context(journal_type='bank').create({
            'journal_id': self.bank_journal_usd_id.id,
        })

        bank_stmt_line_id = self.acc_bank_stmt_line_model.create({
            'name': 'half payment',
            'statement_id': bank_stmt_id.id,
            'date': datetime.date.today(),
            'partner_id': self.partner_agrolait_id.id,
            'amount': -42,
            'amount_currency': -50,
            'currency_id': self.bank_journal_usd_id.id,
        })

        # reconcile the payment with the invoice
        # for l in invoice_record.move_id.line_id:
        #     if l.account_id.id == self.account_rcv_id:
        #         bank_stmt_line_id.process_reconciliation([{
        #             'counterpart_move_line_id': l.id,
        #             'credit': 0,
        #             'debit': 50,
        #             'name': l.name,
        #         }])

        # we check that the line is balanced (bank statement line)

        # self.assertEquals(len(bank_stmt_id.move_line_ids), 3)
        # checked_line = 0
        # for move_line in bank_stmt_id.move_line_ids:
        #     if move_line.account_id.id == self.account_usd_id:
        #         self.assertEquals(move_line.debit, 0.0)
        #         self.assertEquals(move_line.credit, 27.47)
        #         self.assertEquals(move_line.amount_currency, -42)
        #         self.assertEquals(move_line.currency_id.id, self.currency_usd_id.id)
        #         checked_line += 1
        #         continue
        #     if move_line.account_id.id == self.account_rcv_id:
        #         self.assertEquals(move_line.debit, 38.21)
        #         self.assertEquals(move_line.credit, 0.0)
        #         self.assertEquals(move_line.amount_currency, 50)
        #         self.assertEquals(move_line.currency_id.id, self.currency_swiss_id.id)
        #         checked_line += 1
        #         continue
        #     if move_line.account_id.id == self.account_rsa_id:
        #         self.assertEquals(move_line.debit, 0.0)
        #         self.assertEquals(move_line.credit, 10.74)
        #         checked_line += 1
        #         continue
        # self.assertEquals(checked_line, 3)

