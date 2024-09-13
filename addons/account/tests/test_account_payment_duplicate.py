from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountPaymentDuplicateMoves(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.company_data['company']
        cls.receivable = cls.company_data['default_account_receivable']
        cls.payable = cls.company_data['default_account_payable']
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.comp_curr = cls.company_data['currency']

        cls.payment_in = cls.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_id': cls.partner_a.id,
            'destination_account_id': cls.receivable.id,
        })
        cls.payment_out = cls.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'outbound',
            'partner_id': cls.partner_a.id,
            'destination_account_id': cls.payable.id,
        })

        cls.out_invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 50.0, 'tax_ids': []})],
        })
        cls.in_invoice_1 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 50.0, 'tax_ids': []})],
        })
        cls.out_invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 20.0, 'tax_ids': []})],
        })
        (cls.out_invoice_1 + cls.out_invoice_2 + cls.in_invoice_1).action_post()

    def test_duplicate_payments(self):
        """ Ensure duplicated payments are computed correctly for both inbound and outbound payments.
        For it to be a duplicate, the partner, the date and the amount must be the same.
        """
        payment_in_1 = self.payment_in
        payment_out_1 = self.payment_out

        # Different type but same partner, amount and date, no duplicate
        self.assertRecordValues(payment_in_1, [{'duplicate_move_ids': []}])

        # Create duplicate payments
        payment_in_2 = payment_in_1.copy(default={'date': payment_in_1.date})
        payment_out_2 = payment_out_1.copy(default={'date': payment_out_1.date})
        # Inbound payment finds duplicate inbound payment, not the outbound payment with same information
        self.assertRecordValues(payment_in_2, [{
            'duplicate_move_ids': [payment_in_1.move_id.id],
        }])
        # Outbound payment finds duplicate outbound duplicate, not the inbound payment with same information
        self.assertRecordValues(payment_out_2, [{
            'duplicate_move_ids': [payment_out_1.move_id.id],
        }])
        # Different date but same amount and same partner, no duplicate
        payment_out_3 = payment_out_1.copy(default={'date': '2023-12-31'})
        self.assertRecordValues(payment_out_3, [{'duplicate_move_ids': []}])

        # Different amount but same partner and same date, no duplicate
        payment_out_4 = self.env['account.payment'].create({
            'amount': 60.0,
            'payment_type': 'outbound',
            'partner_id': self.partner_a.id,
            'destination_account_id': self.payable.id,
        })
        self.assertRecordValues(payment_out_4, [{'duplicate_move_ids': []}])

        # Different partner but same amount and same date, no duplicate
        payment_out_5 = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'outbound',
            'partner_id': self.partner_b.id,
            'destination_account_id': self.payable.id,
        })
        self.assertRecordValues(payment_out_5, [{'duplicate_move_ids': []}])

    def test_payment_duplicate_moves(self):
        """ Ensure payments with matching moves are computed correctly, including journal entries,
        refunds and statement lines. For it to be a duplicate, the partner, the date, the amount
        and the account (for bank statements, it can be in the suspense account) must be the same.
        """
        payment_in_1 = self.payment_in
        payment_out_1 = self.payment_out

        # Create statement lines with positive value (inbound payment) and negative value (outbound payment)
        statement_line_in = self.env['account.bank.statement.line'].create({
            'date': payment_in_1.date,
            'journal_id': self.bank_journal.id,
            'payment_ref': 'line_1_in',
            'partner_id': self.partner_a.id,
            'amount': 50.0,
        })
        statement_line_out = self.env['account.bank.statement.line'].create({
            'date': payment_out_1.date,
            'journal_id': self.bank_journal.id,
            'payment_ref': 'line_1_out',
            'partner_id': self.partner_a.id,
            'amount': -50.0,
        })

        # Create credit note and refund with same amount, partner and date.
        credit_note = self.init_invoice('out_refund', amounts=[50.0], invoice_date=payment_in_1.date, partner=self.partner_a)
        refund = self.init_invoice('in_refund', amounts=[50.0], invoice_date=payment_in_1.date, partner=self.partner_a)

        # create_line_for_reconciliation allows creation of an entry on a specific account. The duplicate moves function
        # matches credits in a receivable acc or debits in a payable acc, which are the parameters in the helper function
        # Payment in = credit in a receivable account, hence the negative balance.
        misc_entry_in = self.create_line_for_reconciliation(-50.0, -50.0, self.comp_curr, payment_in_1.date, self.receivable, self.partner_a)
        misc_entry_out = self.create_line_for_reconciliation(50.0, 50.0, self.comp_curr, payment_in_1.date, self.payable, self.partner_a)

        # Inbound payment finds statement line, credit note and misc entry crediting receivable account
        self.assertRecordValues(payment_in_1, [{
            'duplicate_move_ids': (statement_line_in.move_id + credit_note + misc_entry_in.move_id).ids,
        }])
        # Outbound payment finds statement line, refund and misc entry debiting payable account
        self.assertRecordValues(payment_out_1, [{
            'duplicate_move_ids': (statement_line_out.move_id + refund + misc_entry_out.move_id).ids,
        }])

    def test_payment_dup_outstanding_account(self):
        """ Ensure that moves in other outstanding accounts are also considered as potential duplicates """
        payment_1 = self.payment_in
        # In the same journal, a new method line for inbound and a new method for outbound payments will be added
        journal = payment_1.journal_id
        outstanding_payment_in = self.company.account_journal_payment_debit_account_id.copy()
        outstanding_payment_out = self.company.account_journal_payment_credit_account_id.copy()
        self.env['account.payment.method.line'].create({
            'name': 'new inbound payment method line',
            'payment_method_id': journal.available_payment_method_ids[0].id,
            'payment_type': 'inbound',
            'journal_id': journal.id,
            'payment_account_id': outstanding_payment_in.id,
        })
        self.env['account.payment.method.line'].create({
            'name': 'new outbound payment method line',
            'payment_method_id': journal.available_payment_method_ids[0].id,
            'payment_type': 'outbound',
            'journal_id': journal.id,
            'payment_account_id': outstanding_payment_out.id,
        })
        # Create new journal entries using the new outstanding accounts
        misc_entry_in = self.create_line_for_reconciliation(-50.0, -50.0, self.comp_curr, payment_1.date, outstanding_payment_in, self.partner_a)
        self.create_line_for_reconciliation(50.0, 50.0, self.comp_curr, payment_1.date, outstanding_payment_out, self.partner_a)

        self.assertRecordValues(payment_1, [{
            'duplicate_move_ids': [misc_entry_in.move_id.id],  # not misc_entry_out, as the account is for outbound payments
        }])

    def test_inbound_payment_dup_no_outstanding_account(self):
        """ Test that duplicate payments query still works in case there are no
        outstanding accounts in the journal nor the company
        """
        self.payment_in.journal_id.outbound_payment_method_line_ids = None
        self.company.account_journal_payment_debit_account_id = None
        payment_in_2 = self.payment_in.copy(default={'date': self.payment_in.date})
        self.assertRecordValues(payment_in_2, [{
            'duplicate_move_ids': [self.payment_in.move_id.id],
        }])

    def test_in_payment_multiple_duplicate_inbound_batch(self):
        """ Ensure duplicated payments are computed correctly when updated in batch,
        where payments are all of a single payment type
        """
        payment_1 = self.payment_in
        payment_2 = payment_1.copy(default={'date': payment_1.date})
        payment_3 = payment_1.copy(default={'date': payment_1.date})

        payments = payment_1 + payment_2 + payment_3

        self.assertRecordValues(payments, [
            {'duplicate_move_ids': (payment_2.move_id + payment_3.move_id).ids},
            {'duplicate_move_ids': (payment_1.move_id + payment_3.move_id).ids},
            {'duplicate_move_ids': (payment_1.move_id + payment_2.move_id).ids},
        ])

    def test_in_payment_multiple_duplicate_multiple_journals(self):
        """ Ensure duplicated payments are computed correctly when updated in batch,
        with inbound and outbound payments with different journals
        """
        payment_in_1 = self.payment_in
        payment_out_1 = self.payment_out
        # Create a different journals with a different outstanding account
        bank_journal_B = self.bank_journal.copy()
        outstanding_payment_account_B = self.company.account_journal_payment_debit_account_id.copy()
        bank_journal_B.inbound_payment_method_line_ids.payment_account_id = outstanding_payment_account_B
        # Create new payments in the second journal
        payment_in_2 = payment_in_1.copy(default={'date': payment_in_1.date})
        payment_in_2.journal_id = bank_journal_B
        payment_out_2 = payment_out_1.copy(default={'date': payment_out_1.date})
        payment_out_2.journal_id = bank_journal_B

        payments = payment_in_1 + payment_out_1 + payment_in_2 + payment_out_2

        self.assertRecordValues(payments, [
            {'duplicate_move_ids': [payment_in_2.move_id.id]},
            {'duplicate_move_ids': [payment_out_2.move_id.id]},
            {'duplicate_move_ids': [payment_in_1.move_id.id]},
            {'duplicate_move_ids': [payment_out_1.move_id.id]},
        ])

    def test_register_payment_different_payment_types(self):
        """ Test that payment wizard correctly calculates duplicate_move_ids """
        payment_1 = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.out_invoice_1.ids).create({'payment_date': self.payment_in.date})
        payment_2 = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.in_invoice_1.ids).create({'payment_date': self.payment_out.date})
        existing_payment_in = self.payment_in
        existing_payment_out = self.payment_out

        # Payment wizards flag unreconciled existing payments of the same payment type only
        self.assertRecordValues(payment_1, [{'duplicate_move_ids': [existing_payment_in.move_id.id]}])
        self.assertRecordValues(payment_2, [{'duplicate_move_ids': [existing_payment_out.move_id.id]}])

    def test_register_payment_single_batch_duplicate_payments(self):
        """ Test that duplicate_move_ids is correctly calculated for single batches """
        payment_1 = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.out_invoice_1.ids).create({'payment_date': self.payment_in.date})
        payment_2 = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.out_invoice_2.ids).create({'payment_date': self.out_invoice_2.date})
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        combined_payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 50.0,  # amount can be changed manually
            'group_payment': True,
            'payment_difference_handling': 'open',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        existing_payment = self.payment_in

        self.assertRecordValues(payment_1, [{'duplicate_move_ids': [existing_payment.move_id.id]}])
        self.assertRecordValues(payment_2, [{'duplicate_move_ids': []}])  # different amount, not a duplicate
        # Combined payments does not show payment_1 as duplicate because payment_1 is reconciled
        self.assertRecordValues(combined_payments, [{'duplicate_move_ids': [existing_payment.move_id.id]}])

    def test_register_payment_dup_no_outstanding_account(self):
        """ Test that duplicate payments query for the account payment register still
        works in case there are no outstanding accounts in the journal nor in the company
        """
        self.bank_journal.outbound_payment_method_line_ids = None
        self.company.account_journal_payment_debit_account_id = None
        payment_1 = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.out_invoice_1.ids).create({'payment_date': self.payment_in.date})

        self.assertRecordValues(payment_1, [{'duplicate_move_ids': [self.payment_in.move_id.id]}])
