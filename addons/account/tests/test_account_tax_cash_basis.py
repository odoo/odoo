# coding: utf-8
import time
from odoo.tools import float_round
from odoo.addons.account.tests.test_reconciliation import TestReconciliation


class TestAccountTaxCashBasis(TestReconciliation):
    """Tests for taxes effectively receivable(paid) when there is difference
    rate between date invoice and date payment

    The rate always must be of the payment to create tax effectively receivable

    Currency company EUR
    Secondary currency USD

    e.g
    Tax effectively receivable: $16
    Rates USD:
               date         |  rate  | inverse rate | expected tax effectively
        --------------------|--------|--------------|------------------------
        12/31/2009 18:00:00 | 1.2834 |0.7791803023  | 12.47
        06/05/2017 19:00:00 | 1.5289 |0.6540650141  | 10.47
    """

    def setUp(self):
        super(TestAccountTaxCashBasis, self).setUp()
        self.user_type_id = self.env.ref(
            'account.data_account_type_current_liabilities')
        self.account_model = self.env['account.account']
        self.account_move_line_model = self.env['account.move.line']
        self.journal_model = self.env['account.journal']
        self.payment_model = self.env['account.payment']
        self.precision = self.env.user.company_id.currency_id.decimal_places
        self.pay_method = self.env.ref(
            'account.account_payment_method_manual_out')
        self.account_tax_receivable = self.account_model.search(
            [('user_type_id', '=', self.user_type_id .id)], limit=1)
        self.journal_cbt = self.journal_model.create({
            'name': 'Cash Basis Tax',
            'type': 'general',
            'code': 'CBT',
        })
        self.account_tax_cash_basis = self.create_account_tax_er()
        self.env.ref('base.main_company').write(
            {'tax_cash_basis_journal_id': self.journal_cbt.id})

    def create_payment(self, invoice, date, amount):
        payment = self.payment_model.create({
            'payment_date': date,
            'journal_id': self.bank_journal_usd.id,
            'amount': amount,
            'invoice_ids': [(6, 0, invoice.ids)],
            'payment_type': 'inbound',
            'payment_method_id': self.pay_method.id,
            'partner_id': invoice.partner_id.id,
            'currency_id': self.currency_usd_id,
            'partner_type': 'customer'})
        payment.post()

    def create_account_tax_er(self):
        """This account is created to use like cash basis account and only
        it will be filled when there is payment
        """
        account_ter = self.account_model.create({
            'name': 'Tax effectively receivable',
            'code': '11111101',
            'user_type_id': self.user_type_id.id,
        })
        return account_ter

    def create_invoice_usd(self, date_invoice):
        """Create to invoice in given date
        :param date_invoice: the date invoice and this date will be used to get
        the currency rate"""

        tax = self.env['account.tax'].create({
            'name': 'Tax 16.0',
            'amount': 16.0,
            'amount_type': 'percent',
            'account_id': self.account_tax_receivable.id,
            'tax_exigibility': 'on_payment',
            'cash_basis_account': self.account_tax_cash_basis.id
        })

        invoice = self.account_invoice_model.create({
            'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'currency_id': self.currency_usd_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv.id,
            'type': 'out_invoice',
            'date_invoice': date_invoice,
            })
        self.account_invoice_line_model.create({
            'product_id': self.product.id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            'account_id': self.account_model.search(
                [('user_type_id', '=', self.env.ref(
                    'account.data_account_type_revenue').id)], limit=1).id,
            'invoice_line_tax_ids': [(6, 0, tax.ids)]
        })

        # validate invoice
        invoice.compute_taxes()
        invoice.action_invoice_open()
        return invoice

    def test_cash_basis_tax_rate_invoice_greater_than_payment(self):
        """Test to validate tax effectively receivable

        Case   |   rate | expected tax effectively receivable
       --------|--------|-----------------------------------
       Invoice | 1.2834 | Not yet created
       Payment | 1.5289 | 10.47
        """
        invoice_id = self.create_invoice_usd(time.strftime('%Y') + '-01-01')
        self.create_payment(invoice_id, time.strftime('%Y') + '-07-15', 116)
        move_ter = self.account_move_line_model.search(
            [('account_id', '=', self.account_tax_cash_basis.id)])
        ter_balance = (
            sum(move_ter.mapped('credit')) - sum(move_ter.mapped('debit')))
        self.assertEquals(
            float_round(ter_balance, precision_digits=self.precision), 10.47)

    def test_cash_basis_tax_rate_invoice_less_than_payment(self):
        """Test to validate tax effectively receivable

        Case   |   rate | expected tax effectively receivable
       --------|--------|-----------------------------------
       Invoice | 1.5289 | Not yet created
       Payment | 1.2834 | 12.47
        """
        invoice_id = self.create_invoice_usd(time.strftime('%Y') + '-07-15')
        self.create_payment(invoice_id, time.strftime('%Y') + '-01-01', 116)
        move_ter = self.account_move_line_model.search(
            [('account_id', '=', self.account_tax_cash_basis.id)])
        ter_balance = (
            sum(move_ter.mapped('credit')) - sum(move_ter.mapped('debit')))
        self.assertEquals(
            float_round(ter_balance, precision_digits=self.precision), 12.47)

    def test_cash_basis_tax_rate_invoice_same_payment(self):
        """Test to validate tax effectively receivable

        Case   |   rate | expected tax effectively receivable
       --------|--------|-----------------------------------
       Invoice | 1.2834 | Not yet created
       Payment | 1.2834 | 12.47
        """
        invoice_id = self.create_invoice_usd(time.strftime('%Y') + '-01-01')
        self.create_payment(invoice_id, time.strftime('%Y') + '-01-01', 116)
        move_ter = self.account_move_line_model.search(
            [('account_id', '=', self.account_tax_cash_basis.id)])
        ter_balance = (
            sum(move_ter.mapped('credit')) - sum(move_ter.mapped('debit')))
        self.assertEquals(
            float_round(ter_balance, precision_digits=self.precision), 12.47)
