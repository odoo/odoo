# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import new_test_user, tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountMovePaymentsWidget(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.payable_account = cls.company_data['default_account_payable']

        cls.curr_1 = cls.company_data['currency']
        cls.curr_2 = cls.setup_other_currency('EUR')
        cls.curr_3 = cls.setup_other_currency('CAD', rates=[('2016-01-01', 6.0), ('2017-01-01', 4.0)])

        # Plain partners sharing the default receivable account, unlike partner_a and partner_b.
        cls.old_partner, cls.new_partner = cls.env['res.partner'].create([
            {'name': 'old partner'},
            {'name': 'new partner'},
        ])

        cls.payment_2016_curr_1 = cls.env['account.move'].create({
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -500.0,  'currency_id': cls.curr_1.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 500.0,   'currency_id': cls.curr_1.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2016_curr_1.action_post()

        cls.payment_2016_curr_2 = cls.env['account.move'].create({
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -1550.0, 'currency_id': cls.curr_2.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 1550.0,  'currency_id': cls.curr_2.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2016_curr_2.action_post()

        cls.payment_2017_curr_2 = cls.env['account.move'].create({
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -950.0, 'currency_id': cls.curr_2.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 950.0,  'currency_id': cls.curr_2.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2017_curr_2.action_post()

        cls.payment_2016_curr_3 = cls.env['account.move'].create({
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -3050.0, 'currency_id': cls.curr_3.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 3050.0,  'currency_id': cls.curr_3.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2016_curr_3.action_post()

        cls.payment_2017_curr_3 = cls.env['account.move'].create({
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -1950.0, 'currency_id': cls.curr_3.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 1950.0,  'currency_id': cls.curr_3.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2017_curr_3.action_post()

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------

    def test_outstanding_payments_single_currency(self):
        ''' Test the outstanding payments widget on invoices having the same currency
        as the company one.
        '''

        # Customer invoice of 2500.0 in curr_1.
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        })
        out_invoice.action_post()

        # Vendor bill of 2500.0 in curr_1.
        in_invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        })
        in_invoice.action_post()

        expected_amounts = {
            self.payment_2016_curr_1.id: 500.0,
            self.payment_2016_curr_2.id: 500.0,
            self.payment_2017_curr_2.id: 500.0,
            self.payment_2016_curr_3.id: 500.0,
            self.payment_2017_curr_3.id: 500.0,
        }

        self.assert_invoice_outstanding_to_reconcile_widget(out_invoice, expected_amounts)
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoice, expected_amounts)

    def test_outstanding_payments_foreign_currency(self):
        ''' Test the outstanding payments widget on invoices having a foreign currency. '''

        # Customer invoice of 2500.0 in curr_1.
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 7500.0})],
        })
        out_invoice.action_post()

        # Vendor bill of 2500.0 in curr_1.
        in_invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 7500.0})],
        })
        in_invoice.action_post()

        expected_amounts = {
            self.payment_2016_curr_1.id: 1500.0,
            self.payment_2016_curr_2.id: 1550.0,
            self.payment_2017_curr_2.id: 950.0,
            self.payment_2016_curr_3.id: 1500.0,
            self.payment_2017_curr_3.id: 1000.0,
        }

        self.assert_invoice_outstanding_to_reconcile_widget(out_invoice, expected_amounts)
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoice, expected_amounts)

    def test_payments_with_exchange_difference_payment(self):
        ''' Test the payments widget on invoices having a foreign currency that triggers an exchange difference on the payment. '''

        # Customer invoice of 300 in GOL at exchage rate 3:1. 300 GOL -> 100 USD
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2016-01-01',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 300,
                'tax_ids': [],
            })],
        })
        out_invoice.action_post()

        # Payment at exchange rate 2:1. 300 GOL -> 150 USD
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=out_invoice.ids)\
            .create({'payment_date': '2017-01-01'})\
            ._create_payments()

        expected_amounts = {payment.move_id.id: 300.0}
        # Get the exchange difference move.
        for ln in out_invoice.line_ids:
            if ln.matched_credit_ids.exchange_move_id:
                expected_amounts[ln.matched_credit_ids.exchange_move_id.id] = 50.0

        self.assert_invoice_outstanding_reconciled_widget(out_invoice, expected_amounts)

    def test_payments_with_exchange_difference_invoice(self):
        ''' Test the payments widget on invoices having a foreign currency that triggers an exchange difference on the invoice. '''

        # Customer invoice of 300 in GOL at exchage rate 2:1. 300 GOL -> 150 USD
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 300,
                'tax_ids': [],
            })],
        })
        out_invoice.action_post()

        # Payment at exchange rate 3:1. 300 GOL -> 100 USD
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=out_invoice.ids)\
            .create({'payment_date': '2016-01-01'})\
            ._create_payments()

        expected_amounts = {payment.move_id.id: 300.0}
        # Get the exchange difference move.
        for ln in out_invoice.line_ids:
            if ln.matched_credit_ids.exchange_move_id:
                expected_amounts[ln.matched_credit_ids.exchange_move_id.id] = 50.0

        self.assert_invoice_outstanding_reconciled_widget(out_invoice, expected_amounts)

    def test_outstanding_payments_branch_and_companies(self):
        """ Test the outstanding payments widget on invoices of a branch
        of the company having oustanding payments.
        """

        branch_a, branch_b = self.env['res.company'].create([{
            'name': name,
            'parent_id': self.env.company.id,
        } for name in ['Branch A', 'Branch B']])
        self.cr.precommit.run()  # load the CoA

        other_company_data = self.setup_other_company()
        other_company = other_company_data['company']

        self.env['account.journal'].with_company(company=other_company).create([
            {'name': 'sale', 'type': 'sale', 'code': 'SALE'},
            {'name': 'purchase', 'type': 'purchase', 'code': 'BUY'},
        ])

        # Customer invoice of 2500.0 in curr_1.
        out_invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'company_id': company.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        } for company in [branch_a, branch_b, other_company, self.company]])
        out_invoices.action_post()

        # Vendor bill of 2500.0 in curr_1.
        in_invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'company_id': company.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        } for company in [branch_a, branch_b, other_company, self.company]])
        in_invoices.action_post()

        out_refund = self.env['account.move'].create([{
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'company_id': branch.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': price})],
        } for branch, price in zip((branch_a, branch_b), (2500.0, 1000.0))])
        out_refund.action_post()
        in_refund = self.env['account.move'].create([{
            'move_type': 'in_refund',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'company_id': branch.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': price})],
        } for branch, price in zip((branch_a, branch_b), (2500.0, 1000.0))])
        in_refund.action_post()

        expected_amounts = {
            self.payment_2016_curr_1.id: 500.0,
            self.payment_2016_curr_2.id: 500.0,
            self.payment_2017_curr_2.id: 500.0,
            self.payment_2016_curr_3.id: 500.0,
            self.payment_2017_curr_3.id: 500.0,
        }

        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[0], {out_refund[0].id: 2500.0})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[0], {in_refund[0].id: 2500.0})
        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[1], {out_refund[1].id: 1000.0})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[1], {in_refund[1].id: 1000.0})
        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[2], {})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[2], {})
        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[3], {**expected_amounts, out_refund[0].id: 2500.0, out_refund[1].id: 1000.0})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[3], {**expected_amounts, in_refund[0].id: 2500.0, in_refund[1].id: 1000.0})

    def test_payments_widget_open_entries(self):
        """ The invoicing users can't open the entries that aren't invoices or payments. """
        invoice = self.init_invoice('out_invoice', amounts=[3000.0], post=True)
        receivable_line = invoice.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 1000.0,
        })._create_payments()
        bank_journal = self.company_data['default_journal_bank']
        bank_entry = self.env['account.move'].create({
            'journal_id': bank_journal.id,
            'line_ids': [
                Command.create({'credit': 1000.0, 'account_id': self.receivable_account.id, 'partner_id': self.partner_a.id}),
                Command.create({'debit': 1000.0, 'account_id': bank_journal.default_account_id.id}),
            ],
        })
        misc_entry = self.payment_2016_curr_1.copy({'date': '2017-01-01'})
        (bank_entry + misc_entry).action_post()
        (receivable_line + (bank_entry + misc_entry).line_ids.filtered(lambda line: line.account_id == self.receivable_account)).reconcile()

        invoicing_user = new_test_user(self.env, login='invoicing_user', groups='base.group_user,account.group_account_invoice')
        readonly_user = new_test_user(self.env, login='readonly_user', groups='base.group_user,account.group_account_readonly')
        for user, expected in (
            (invoicing_user, {payment.move_id.id: True, bank_entry.id: False, misc_entry.id: False}),
            (readonly_user, {payment.move_id.id: True, bank_entry.id: True, misc_entry.id: True}),
        ):
            with self.subTest(user=user.login):
                widget_vals = invoice.with_user(user).invoice_payments_widget
                self.assertEqual({vals['move_id']: vals['can_open_move'] for vals in widget_vals['content']}, expected)

    def _create_draft_invoice(self, partner, currency=None):
        """
        Create a draft invoice of 300 without taxes.
        :return: (invoice, invoice_line), invoice_line being its receivable line.
        """
        invoice = self._create_invoice_one_line(
            price_unit=300.0, tax_ids=[], invoice_date='2017-01-01',
            partner_id=partner, currency_id=currency,
        )
        return invoice, invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')

    def _create_reconciled_draft_invoice(self, invoice_partner, payment_partner, currency=None,
                                         payment_date='2017-01-01'):
        """
        Create a draft invoice of 300 and a posted payment of 300, then reconcile them.
        :return: (invoice, invoice_line, payment_line), the lines being the reconciled receivable lines.
        """
        invoice, invoice_line = self._create_draft_invoice(invoice_partner, currency=currency)
        payment = self.init_payment(300.0, post=True, date=payment_date, partner=payment_partner, currency=currency)
        payment_line = payment.move_id.line_ids.filtered(lambda line: line.account_id == invoice_line.account_id)
        (invoice_line + payment_line).reconcile()
        self.assertTrue(invoice_line.reconciled)
        return invoice, invoice_line, payment_line

    def test_draft_change_partner_unreconcile(self):
        """
        A payment of the old partner must not stay reconciled with an invoice given to another partner.
        """
        invoice, invoice_line, payment_line = self._create_reconciled_draft_invoice(self.old_partner, self.old_partner)

        invoice.partner_id = self.new_partner

        self.assertFalse(invoice_line.matched_debit_ids + invoice_line.matched_credit_ids)
        self.assertRecordValues(payment_line, [{'reconciled': False, 'amount_residual': -300.0}])

    def test_draft_change_partner_contact_keep_reconciliation(self):
        """
        A payment made by a contact of the new partner belongs to the same commercial partner and stays reconciled.
        """
        contact = self.env['res.partner'].create({'name': 'new partner contact', 'parent_id': self.new_partner.id})
        invoice, invoice_line, payment_line = self._create_reconciled_draft_invoice(self.old_partner, contact)

        invoice.partner_id = self.new_partner

        self.assertRecordValues(invoice_line + payment_line, [
            {'reconciled': True, 'partner_id': self.new_partner.id},
            {'reconciled': True, 'partner_id': contact.id},
        ])

    def test_draft_change_partner_exchange_diff_unreconcile(self):
        """
        The payment already belongs to the new partner, but the exchange difference entry created by the
        reconciliation carries the old partner on its receivable line. Keeping the reconciliation would leave
        -50 on the old partner and +50 on the new one, so it must be broken and redone.
        """
        # Invoice of 300 EUR on 2017-01-01 at rate 2 (150 USD), paid by 300 EUR on 2016-01-01 at rate 3 (100 USD):
        # the exchange difference of 50 USD is booked against the invoice line, with the invoice partner.
        invoice, invoice_line, payment_line = self._create_reconciled_draft_invoice(
            self.old_partner, self.new_partner, currency=self.curr_2, payment_date='2016-01-01',
        )
        exchange_move = (invoice_line.matched_debit_ids + invoice_line.matched_credit_ids).exchange_move_id
        exchange_loss_account = self.env.company.expense_currency_exchange_account_id
        self.assertRecordValues(exchange_move.line_ids, [
            {'account_id': invoice_line.account_id.id, 'partner_id': self.old_partner.id, 'balance': -50.0},
            {'account_id': exchange_loss_account.id, 'partner_id': self.old_partner.id, 'balance': 50.0},
        ])

        invoice.partner_id = self.new_partner

        self.assertRecordValues(invoice_line + payment_line, [
            {'reconciled': False, 'partner_id': self.new_partner.id, 'amount_residual': 150.0},
            {'reconciled': False, 'partner_id': self.new_partner.id, 'amount_residual': -100.0},
        ])
        self.assertFalse(exchange_move.exists())

        # Reconciling again books the exchange difference on the new partner.
        (invoice_line + payment_line).reconcile()
        new_exchange_move = (invoice_line.matched_debit_ids + invoice_line.matched_credit_ids).exchange_move_id
        self.assertEqual(new_exchange_move.line_ids.partner_id, self.new_partner)

    def test_draft_change_partner_st_line_unreconcile(self):
        """
        When the invoice was paid from a bank statement line of the old partner, the statement line
        must be reset to its suspense account, as when undoing its reconciliation.
        """
        invoice, invoice_line = self._create_draft_invoice(self.old_partner)
        bank_journal = self.company_data['default_journal_bank']
        st_line = self.env['account.bank.statement.line'].create({
            'journal_id': bank_journal.id,
            'date': '2017-01-01',
            'payment_ref': 'ref',
            'amount': 300.0,
            'partner_id': self.old_partner.id,
        })
        _liquidity_line, st_suspense_line, _other_lines = (
            st_line.with_context(skip_account_move_synchronization=True)._seek_for_lines()
        )
        st_suspense_line.account_id = invoice_line.account_id
        (st_suspense_line + invoice_line).reconcile()
        self.assertTrue(st_line.is_reconciled)

        invoice.partner_id = self.new_partner

        self.assertFalse(invoice_line.matched_debit_ids + invoice_line.matched_credit_ids)
        self.assertRecordValues(st_line, [{'is_reconciled': False}])
        self.assertIn(bank_journal.suspense_account_id, st_line.line_ids.account_id)
