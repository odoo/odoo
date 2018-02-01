
import time
import odoo.tests.common as common


class TestBadReconciliation(common.TransactionCase):

    def setUp(self):
        res = super(TestBadReconciliation, self).setUp()
        self.company = self.env.ref('base.main_company')
        self.receivable_account = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref(
                'account.data_account_type_receivable').id),
             ('company_id', '=', self.company.id)],
            limit=1)
        self.payable_account = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref(
                'account.data_account_type_payable').id),
             ('company_id', '=', self.company.id)],
            limit=1)
        self.account_expenses = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref(
                'account.data_account_type_expenses').id),
             ('company_id', '=', self.company.id)],
            limit=1)
        self.account_revenue = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref(
                'account.data_account_type_revenue').id),
             ('company_id', '=', self.company.id)],
            limit=1)

        self.cc_bank_account = self.env['account.account'].create({
            'name': 'CC Bank Account',
            'code': '9991',
            'company_id': self.company.id,
            'user_type_id': self.env.ref(
                'account.data_account_type_current_assets').id

        })
        self.company.income_currency_exchange_account_id = self.env[
            'account.account'].create({
                'name': 'Exchange Profit',
                'code': '9993',
                'company_id': self.company.id,
                'user_type_id': self.env.ref(
                    'account.data_account_type_revenue').id
            })
        self.company.expense_currency_exchange_account_id = self.env[
            'account.account'].create({
                'name': 'Exchange Loss',
                'code': '9994',
                'company_id': self.company.id,
                'user_type_id': self.env.ref(
                    'account.data_account_type_expenses').id
            })
        self.currency_cc = self.env['res.currency'].with_context(
            company_id=self.company.id,
            force_company=self.company.id).create({
                'name': 'CC',
                'rounding': 0.010000,
                'symbol': 'CC',
                'position': 'after',
            })
        self.customer = self.env['res.partner'].create({
            'name': 'Test customer',
            'customer': True,
        })
        self.supplier = self.env['res.partner'].create({
            'name': 'Test supplier',
            'customer': True,
        })
        self.cc_journal = self.env['account.journal'].create({
            'name': 'CC Payments Journal',
            'code': 'CC',
            'type': 'bank',
            'company_id': self.company.id,
            'default_debit_account_id': self.cc_bank_account.id,
            'default_credit_account_id': self.cc_bank_account.id,
        })
        # We want to make sure that the company has no rates, that would
        # screw up the conversions.
        company_rates = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.company.currency_id.id)])
        company_rates.unlink()

        return res

    def _check_account_balance(self, account):
        balance = sum(self.env['account.move.line'].search(
            [('account_id', '=', account.id)]).mapped('balance'))
        return balance

    def test_01(self):
        """ Implements a successful scenario """
        ####
        # Day 1: Invoice Cust/001 to customer (expressed in CC)
        # Market value of CC (day 1): 1 CC = $0.5
        # * Dr. 100 CC / $50 - Accounts receivable
        # * Cr. 100 CC / $50 - Revenue
        ####
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_cc.id,
            'name': time.strftime('%Y') + '-01-01',
            'rate': 2,
        })
        invoice_cust_001 = self.env['account.invoice'].create({
            'partner_id': self.customer.id,
            'account_id': self.receivable_account.id,
            'type': 'out_invoice',
            'currency_id': self.currency_cc.id,
            'company_id': self.company.id,
            'date_invoice': time.strftime('%Y') + '-01-01',
        })
        self.env['account.invoice.line'].create({
            'product_id': self.env.ref('product.product_product_4').id,
            'quantity': 1.0,
            'price_unit': 100.0,
            'invoice_id': invoice_cust_001.id,
            'name': 'product that cost 100',
            'account_id': self.account_revenue.id,
        })
        invoice_cust_001.action_invoice_open()
        self.assertEqual(invoice_cust_001.residual_company_signed, 50.0)
        aml = invoice_cust_001.move_id.mapped('line_ids').filtered(
            lambda x: x.account_id == self.account_revenue)
        self.assertEqual(aml.credit, 50.0)
        #####
        # Day 2: Receive payment for half invoice Cust/001 (in CC)
        # -------------------------------------------------------
        # Market value of CC (day 2): 1 CC = $0.5

        # Payment transaction:
        # * Dr. 50 CC / $25 - CC Bank (valued at market price
        # at the time of receiving the coins)
        # * Cr. 50 CC / $25 - Accounts Receivable
        #####
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_cc.id,
            'name': time.strftime('%Y') + '-01-02',
            'rate': 2,
        })
        # register payment on invoice
        payment = self.env['account.payment'].create(
            {'payment_type': 'inbound',
             'payment_method_id': self.env.ref(
                 'account.account_payment_method_manual_in').id,
             'partner_type': 'customer',
             'partner_id': self.customer.id,
             'amount': 50,
             'currency_id': self.currency_cc.id,
             'payment_date': time.strftime('%Y') + '-01-02',
             'journal_id': self.cc_journal.id,
             })
        payment.post()
        payment_move_line = False
        for l in payment.move_line_ids:
            if l.account_id == self.receivable_account:
                payment_move_line = l
        invoice_cust_001.register_payment(payment_move_line)
        self.assertEqual(invoice_cust_001.state, 'open',
                         'Invoice is in status %s' % invoice_cust_001.state)
        #####
        # Day 2: Receive payment for half invoice Cust/001 (in CC)
        # -------------------------------------------------------
        # Market value of CC (day 2): 1 CC = $1

        # Payment transaction:
        # * Dr. 50 CC / $25 - CC Bank (valued at market price
        # at the time of receiving the coins)
        # * Cr. 50 CC / $25 - Accounts Receivable
        #####
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_cc.id,
            'name': time.strftime('%Y') + '-01-03',
            'rate': 1,
        })
        # register payment on invoice
        payment = self.env['account.payment'].create(
            {'payment_type': 'inbound',
             'payment_method_id': self.env.ref(
                 'account.account_payment_method_manual_in').id,
             'partner_type': 'customer',
             'partner_id': self.customer.id,
             'amount': 50,
             'currency_id': self.currency_cc.id,
             'payment_date': time.strftime('%Y') + '-01-03',
             'journal_id': self.cc_journal.id,
             })
        payment.post()
        payment_move_line = False
        for l in payment.move_line_ids:
            if l.account_id == self.receivable_account:
                payment_move_line = l
        invoice_cust_001.register_payment(payment_move_line)
        self.assertEqual(invoice_cust_001.state, 'paid',
                         'Invoice is in status %s' % invoice_cust_001.state)

    def test_02(self):
        """ Implements the failing scenario """
        ####
        # Day 1: Invoice Cust/001 to customer (expressed in CC)
        # Market value of CC (day 1): 1 CC = $0.5
        # * Dr. 100 CC / $50 - Accounts receivable
        # * Cr. 100 CC / $50 - Revenue
        ####
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_cc.id,
            'name': time.strftime('%Y') + '-01-01',
            'rate': 2,
        })
        invoice_cust_001 = self.env['account.invoice'].create({
            'partner_id': self.customer.id,
            'account_id': self.receivable_account.id,
            'type': 'out_invoice',
            'currency_id': self.currency_cc.id,
            'company_id': self.company.id,
            'date_invoice': time.strftime('%Y') + '-01-01',
        })
        self.env['account.invoice.line'].create({
            'product_id': self.env.ref('product.product_product_4').id,
            'quantity': 1.0,
            'price_unit': 100.0,
            'invoice_id': invoice_cust_001.id,
            'name': 'product that cost 100',
            'account_id': self.account_revenue.id,
        })
        invoice_cust_001.action_invoice_open()
        self.assertEqual(invoice_cust_001.residual_company_signed, 50.0)
        aml = invoice_cust_001.move_id.mapped('line_ids').filtered(
            lambda x: x.account_id == self.account_revenue)
        self.assertEqual(aml.credit, 50.0)
        #####
        # Day 2: Receive payment for half invoice Cust/001 (in CC)
        # -------------------------------------------------------
        # Market value of CC (day 2): 1 CC = $1

        # Payment transaction:
        # * Dr. 50 CC / $50 - CC Bank (valued at market price
        # at the time of receiving the coins)
        # * Cr. 50 CC / $50 - Accounts Receivable
        #####
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_cc.id,
            'name': time.strftime('%Y') + '-01-02',
            'rate': 1,
        })
        # register payment on invoice
        payment = self.env['account.payment'].create(
            {'payment_type': 'inbound',
             'payment_method_id': self.env.ref(
                 'account.account_payment_method_manual_in').id,
             'partner_type': 'customer',
             'partner_id': self.customer.id,
             'amount': 50,
             'currency_id': self.currency_cc.id,
             'payment_date': time.strftime('%Y') + '-01-02',
             'journal_id': self.cc_journal.id,
             })
        payment.post()
        payment_move_line = False
        for l in payment.move_line_ids:
            if l.account_id == self.receivable_account:
                payment_move_line = l
        invoice_cust_001.register_payment(payment_move_line)
        # We expect at this point that the invoice should still be open,
        # because they owe us still 50 CC.
        self.assertEqual(invoice_cust_001.state, 'open',
                         'Invoice is in status %s' % invoice_cust_001.state)
