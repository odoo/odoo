# -*- coding: utf-8 -*-
# pylint: disable=C0326
import datetime

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestDeferredManagement(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_accounts = [cls.env['account.account'].create({
            'name': f'Expense {i}',
            'code': f'EXP{i}',
            'account_type': 'expense',
        }) for i in range(3)]
        cls.revenue_accounts = [cls.env['account.account'].create({
            'name': f'Revenue {i}',
            'code': f'REV{i}',
            'account_type': 'income',
        }) for i in range(3)]

        cls.company.deferred_expense_journal_id = cls.company_data['default_journal_misc'].id
        cls.company.deferred_revenue_journal_id = cls.company_data['default_journal_misc'].id
        cls.company.deferred_expense_account_id = cls.company_data['default_account_deferred_expense'].id
        cls.company.deferred_revenue_account_id = cls.company_data['default_account_deferred_revenue'].id

        cls.expense_lines = [
            [cls.expense_accounts[0], 1000, '2023-01-01', '2023-04-30'],  # 4 full months (=250/month)
            [cls.expense_accounts[0], 1050, '2023-01-16', '2023-04-30'],  # 3 full months + 15 days (=300/month)
            [cls.expense_accounts[1], 1225, '2023-01-01', '2023-04-15'],  # 3 full months + 15 days (=350/month)
            [cls.expense_accounts[2], 1680, '2023-01-21', '2023-04-14'],  # 2 full months + 10 days + 14 days (=600/month)
            [cls.expense_accounts[2],  225, '2023-04-01', '2023-04-15'],  # 15 days (=450/month)
        ]
        cls.revenue_lines = [
            [cls.revenue_accounts[0], 1000, '2023-01-01', '2023-04-30'],  # 4 full months (=250/month)
            [cls.revenue_accounts[0], 1050, '2023-01-16', '2023-04-30'],  # 3 full months + 15 days (=300/month)
            [cls.revenue_accounts[1], 1225, '2023-01-01', '2023-04-15'],  # 3 full months + 15 days (=350/month)
            [cls.revenue_accounts[2], 1680, '2023-01-21', '2023-04-14'],  # 2 full months + 10 days + 14 days (=600/month)
            [cls.revenue_accounts[2],  225, '2023-04-01', '2023-04-15'],  # 15 days (=450/month)
        ]

    def create_invoice(self, move_type, invoice_lines, date=None, post=True):
        journal = self.company_data['default_journal_purchase'] if move_type in self.env['account.move'].get_purchase_types() else self.company_data['default_journal_sale']
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'date': date or '2023-01-01',
            'invoice_date': date or '2023-01-01',
            'journal_id': journal.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'account_id': account.id,
                    'price_unit': price_unit,
                    'deferred_start_date': start_date,
                    'deferred_end_date': end_date,
                }) for account, price_unit, start_date, end_date in invoice_lines
            ]
        })
        if post:
            move.action_post()
        return move

    def test_deferred_management_get_diff_dates(self):
        def assert_get_diff_dates(start, end, expected):
            diff = self.env['account.move']._get_deferred_diff_dates(fields.Date.to_date(start), fields.Date.to_date(end))
            self.assertAlmostEqual(diff, expected, 3)

        assert_get_diff_dates('2023-01-01', '2023-01-01', 0)
        assert_get_diff_dates('2023-01-01', '2023-01-02', 1/30)
        assert_get_diff_dates('2023-01-01', '2023-01-20', 19/30)
        assert_get_diff_dates('2023-01-01', '2023-01-31', 29/30)
        assert_get_diff_dates('2023-01-01', '2023-01-30', 29/30)
        assert_get_diff_dates('2023-01-01', '2023-02-01', 1)
        assert_get_diff_dates('2023-01-01', '2023-02-28', 1 + 29/30)
        assert_get_diff_dates('2023-02-01', '2023-02-28', 29/30)
        assert_get_diff_dates('2023-02-10', '2023-02-28', 20/30)
        assert_get_diff_dates('2023-01-01', '2023-02-15', 1 + 14/30)
        assert_get_diff_dates('2023-01-01', '2023-03-31', 2 + 29/30)
        assert_get_diff_dates('2023-01-01', '2023-04-01', 3)
        assert_get_diff_dates('2023-01-01', '2023-04-30', 3 + 29/30)
        assert_get_diff_dates('2023-01-10', '2023-04-30', 3 + 20/30)
        assert_get_diff_dates('2023-01-10', '2023-04-09', 2 + 29/30)
        assert_get_diff_dates('2023-01-10', '2023-04-10', 3)
        assert_get_diff_dates('2023-01-10', '2023-04-11', 3 + 1/30)
        assert_get_diff_dates('2023-02-20', '2023-04-10', 1 + 20/30)
        assert_get_diff_dates('2023-01-31', '2023-04-30', 3)
        assert_get_diff_dates('2023-02-28', '2023-04-10', 1 + 10/30)
        assert_get_diff_dates('2023-03-01', '2023-04-10', 1 + 9/30)
        assert_get_diff_dates('2023-04-10', '2023-03-01', 1 + 9/30)
        assert_get_diff_dates('2023-01-01', '2023-12-31', 11 + 29/30)
        assert_get_diff_dates('2023-01-01', '2024-01-01', 12)
        assert_get_diff_dates('2023-01-01', '2024-07-01', 18)
        assert_get_diff_dates('2023-01-01', '2024-07-10', 18 + 9/30)

    def test_get_ends_of_month(self):
        def assertEndsOfMonths(start_date, end_date, expected):
            self.assertEqual(
                self.env['account.move.line']._get_deferred_ends_of_month(
                    fields.Date.to_date(start_date),
                    fields.Date.to_date(end_date)
                ),
                [fields.Date.to_date(date) for date in expected]
            )

        assertEndsOfMonths('2023-01-01', '2023-01-01', ['2023-01-31'])
        assertEndsOfMonths('2023-01-01', '2023-01-02', ['2023-01-31'])
        assertEndsOfMonths('2023-01-01', '2023-01-20', ['2023-01-31'])
        assertEndsOfMonths('2023-01-01', '2023-01-30', ['2023-01-31'])
        assertEndsOfMonths('2023-01-01', '2023-01-31', ['2023-01-31'])
        assertEndsOfMonths('2023-01-01', '2023-02-01', ['2023-01-31', '2023-02-28'])
        assertEndsOfMonths('2023-01-01', '2023-02-28', ['2023-01-31', '2023-02-28'])
        assertEndsOfMonths('2023-02-01', '2023-02-28', ['2023-02-28'])
        assertEndsOfMonths('2023-02-10', '2023-02-28', ['2023-02-28'])
        assertEndsOfMonths('2023-01-01', '2023-02-15', ['2023-01-31', '2023-02-28'])
        assertEndsOfMonths('2023-01-01', '2023-03-31', ['2023-01-31', '2023-02-28', '2023-03-31'])
        assertEndsOfMonths('2023-01-01', '2023-04-01', ['2023-01-31', '2023-02-28', '2023-03-31', '2023-04-30'])
        assertEndsOfMonths('2023-01-01', '2023-04-30', ['2023-01-31', '2023-02-28', '2023-03-31', '2023-04-30'])
        assertEndsOfMonths('2023-01-10', '2023-04-30', ['2023-01-31', '2023-02-28', '2023-03-31', '2023-04-30'])
        assertEndsOfMonths('2023-01-10', '2023-04-09', ['2023-01-31', '2023-02-28', '2023-03-31', '2023-04-30'])

    def test_deferred_abnormal_dates(self):
        """
        Test that we correctly detect abnormal dates.
        In the deferred computations, we always assume that both the start and end date are inclusive
        E.g: 1st January -> 31st December is *exactly* 1 year = 12 months
        However, the user may instead put 1st January -> 1st January of next year which is then
        12 months + 1/30 month = 12.03 months which may result in odd amounts when deferrals are created.
        This is what we call abnormal dates.
        Other cases were the number of months is not round should not be handled and are not considered abnormal.
        """
        move = self.create_invoice('in_invoice', [
            [self.expense_accounts[0], 0, '2023-01-01', '2023-12-30'],
            [self.expense_accounts[0], 1, '2023-01-01', '2023-12-31'],
            [self.expense_accounts[0], 2, '2023-01-01', '2024-01-01'],
            [self.expense_accounts[0], 3, '2023-01-01', '2024-01-02'],
            [self.expense_accounts[0], 4, '2023-01-01', '2024-01-31'],
            [self.expense_accounts[0], 5, '2023-01-01', '2024-02-01'],
            [self.expense_accounts[0], 6, '2023-01-02', '2024-02-01'],
            [self.expense_accounts[0], 7, '2023-01-02', '2024-02-02'],
            [self.expense_accounts[0], 8, '2023-01-31', '2024-01-30'],
            [self.expense_accounts[0], 9, '2023-01-31', '2024-02-28'],  # 29 days in Feb 2024
            # Following one is abnormal because we have a full months in February (= 30 accounting days) + 1 day in January
            [self.expense_accounts[0], 10, '2023-01-31', '2024-02-29'],
            [self.expense_accounts[0], 11, '2023-02-01', '2024-02-29'],
        ], post=True)
        lines = move.invoice_line_ids.sorted('price_unit')
        self.assertFalse(lines[0].has_abnormal_deferred_dates)
        self.assertFalse(lines[1].has_abnormal_deferred_dates)
        self.assertTrue(lines[2].has_abnormal_deferred_dates)
        self.assertFalse(lines[3].has_abnormal_deferred_dates)
        self.assertFalse(lines[4].has_abnormal_deferred_dates)
        self.assertTrue(lines[5].has_abnormal_deferred_dates)
        self.assertFalse(lines[6].has_abnormal_deferred_dates)
        self.assertTrue(lines[7].has_abnormal_deferred_dates)
        self.assertFalse(lines[8].has_abnormal_deferred_dates)
        self.assertFalse(lines[9].has_abnormal_deferred_dates)
        self.assertTrue(lines[10].has_abnormal_deferred_dates)
        self.assertFalse(lines[11].has_abnormal_deferred_dates)

    def test_deferred_expense_generate_entries_method(self):
        # The deferred entries are NOT generated when the invoice is validated if the method is set to 'manual'.
        self.company.generate_deferred_expense_entries_method = 'manual'
        move = self.create_invoice('in_invoice', [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 0)

        move = self.create_invoice('in_refund', [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 0)

        # Test that the deferred entries are generated when the invoice is validated.
        self.company.generate_deferred_expense_entries_method = 'on_validation'
        move = self.create_invoice('in_invoice', [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 5)  # 1 for the invoice deferred + 4 for the deferred entries

        move = self.create_invoice('in_refund', [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 5)
        # See test_deferred_expense_credit_note for the values

    def test_deferred_expense_reset_to_draft(self):
        """
        Test that the deferred entries are deleted/reverted when the invoice is reset to draft.
        """
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 1680, '2023-01-21', '2023-04-14')], date='2023-03-15')
        self.assertEqual(len(move.deferred_move_ids), 5)
        move.button_draft()
        self.assertFalse(move.deferred_move_ids)

        # With a lock date, we should reverse the moves that cannot be deleted
        move.action_post()  # Post the move to create the deferred entries with 'on_validation' method
        self.assertEqual(len(move.deferred_move_ids), 5)
        move.company_id.fiscalyear_lock_date = fields.Date.to_date('2023-02-15')
        move.button_draft()
        # January deferred entry is in lock period, so it is reversed, not deleted, thus we have one deferred entry and its revert
        self.assertEqual(len(move.deferred_move_ids), 2)
        self.assertEqual(move.deferred_move_ids[0].date, fields.Date.to_date('2023-01-31'))
        self.assertEqual(move.deferred_move_ids[1].date, fields.Date.to_date('2023-02-28'))

        # If we repost the move, it should be allowed
        move.action_post()
        self.assertEqual(len(move.deferred_move_ids), 2 + 5)

    @freeze_time('2023-03-15')
    def test_deferred_invoice_reset_to_draft_with_audit_trail(self):
        """
        Test that the deferred entries in draft are deleted when the invoice is reset to draft
        and the posted deferred entries are cancelled.
        """
        invoice = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 1680, '2023-02-01', '2023-04-30')], date='2023-03-15')
        posted_deferred_entries = invoice.deferred_move_ids.filtered(lambda move: move.state == 'posted')
        draft_deferred_move_ids = invoice.deferred_move_ids.filtered(lambda move: move.state =="draft")
        self.assertEqual(len(posted_deferred_entries), 2)
        self.assertEqual(len(draft_deferred_move_ids), 2)

        # Set the company's audit trail to True
        self.env.company.check_account_audit_trail = True

        invoice.button_draft()

        # Assert that the draft moves no longer exist
        remaining_draft_moves = self.env['account.move'].search([('id', 'in', draft_deferred_move_ids.ids)])
        self.assertFalse(remaining_draft_moves)
        # The posted deferred entries should be cancelled
        self.assertEqual(len(posted_deferred_entries.filtered(lambda move: move.state == 'cancel')), 2)

    def assert_invoice_lines(self, move, expected_values, source_account, deferred_account):
        deferred_moves = move.deferred_move_ids.sorted('date')
        for deferred_move, expected_value in zip(deferred_moves, expected_values):
            expected_date, expense_line_debit, expense_line_credit, deferred_line_debit, deferred_line_credit = expected_value
            self.assertRecordValues(deferred_move, [{
                'state': 'posted',
                'move_type': 'entry',
                'partner_id': self.partner_a.id,
                'date': fields.Date.to_date(expected_date),
            }])
            expense_line = deferred_move.line_ids.filtered(lambda line: line.account_id == source_account)
            self.assertRecordValues(expense_line, [
                {'debit': expense_line_debit, 'credit': expense_line_credit, 'partner_id': self.partner_a.id},
            ])
            deferred_line = deferred_move.line_ids.filtered(lambda line: line.account_id == deferred_account)
            self.assertEqual(deferred_line.debit, deferred_line_debit)
            self.assertEqual(deferred_line.credit, deferred_line_credit)

    def test_default_tax_on_account_not_on_deferred_entries(self):
        """
        Test that the default taxes on an account are not calculated on deferral entries, since this would impact the
        tax report.
        """
        revenue_account_with_taxes = self.env['account.account'].create({
            'name': 'Revenue with Taxes',
            'code': 'REVWTAXES',
            'account_type': 'income',
            'tax_ids': [Command.set(self.tax_sale_a.ids)]
        })

        move = self.create_invoice(
            'out_invoice',
            [[revenue_account_with_taxes, 1000, '2023-01-01', '2023-04-30']],
            date='2022-12-10'
        )

        expected_line_values = [
            # Date         [Line expense] [Line deferred]
            ('2022-12-10',  1000,      0,      0,   1000),
            ('2023-01-31',     0,    250,    250,      0),
            ('2023-02-28',     0,    250,    250,      0),
            ('2023-03-31',     0,    250,    250,      0),
        ]

        self.assert_invoice_lines(
            move,
            expected_line_values,
            revenue_account_with_taxes,
            self.company_data['default_account_deferred_revenue']
        )

        for deferred_move in move.deferred_move_ids:
            # There are no extra lines besides the two lines we checked before
            self.assertEqual(len(deferred_move.line_ids), 2)


    def test_deferred_values(self):
        """
        Test that the debit/credit values are correctly computed, even after a credit note is issued.
        """

        expected_line_values1 = [
            # Date         [Line expense] [Line deferred]
            ('2022-12-10',     0,   1000,    1000,     0),
            ('2023-01-31',   250,      0,       0,   250),
            ('2023-02-28',   250,      0,       0,   250),
            ('2023-03-31',   250,      0,       0,   250),
        ]
        expected_line_values2 = [
            # Date         [Line expense] [Line deferred]
            ('2022-12-10',  1000,      0,      0,   1000),
            ('2023-01-31',     0,    250,    250,      0),
            ('2023-02-28',     0,    250,    250,      0),
            ('2023-03-31',     0,    250,    250,      0),
        ]

        # Vendor bill and credit note
        move = self.create_invoice('in_invoice', [self.expense_lines[0]], post=True, date='2022-12-10')
        self.assert_invoice_lines(move, expected_line_values1, self.expense_accounts[0], self.company_data['default_account_deferred_expense'])
        reverse_move = move._reverse_moves()
        self.assert_invoice_lines(reverse_move, expected_line_values2, self.expense_accounts[0], self.company_data['default_account_deferred_expense'])

        # Customer invoice and credit note
        move2 = self.create_invoice('out_invoice', [self.revenue_lines[0]], post=True, date='2022-12-10')
        self.assert_invoice_lines(move2, expected_line_values2, self.revenue_accounts[0], self.company_data['default_account_deferred_revenue'])
        reverse_move2 = move2._reverse_moves()
        self.assert_invoice_lines(reverse_move2, expected_line_values1, self.revenue_accounts[0], self.company_data['default_account_deferred_revenue'])

    def test_deferred_values_rounding(self):
        """
        Test that the debit/credit values are correctly computed when values are rounded
        """

        # Vendor Bill
        expense_line = [self.expense_accounts[0], 500, '2020-08-07', '2020-12-07']
        expected_line_values = [
            # Date         [Line expense] [Line deferred]
            ('2020-08-07',      0, 500,   500,      0),
            ('2020-08-31',  99.17,   0,     0,  99.17),
            ('2020-09-30', 123.97,   0,     0, 123.97),
            ('2020-10-31', 123.97,   0,     0, 123.97),
            ('2020-11-30', 123.97,   0,     0, 123.97),
            ('2020-12-07',  28.92,   0,     0,  28.92),
        ]
        self.assertEqual(self.company.currency_id.round(sum(x[1] for x in expected_line_values)), 500)
        move = self.create_invoice('in_invoice', [expense_line], date='2020-08-07')
        self.assert_invoice_lines(move, expected_line_values, self.expense_accounts[0], self.company_data['default_account_deferred_expense'])

        # Customer invoice
        revenue_line = [self.revenue_accounts[0], 500, '2020-08-07', '2020-12-07']
        expected_line_values = [
            # Date         [Line expense] [Line deferred]
            ('2020-08-07', 500,      0,      0,       500),
            ('2020-08-31',   0,  99.17,  99.17,         0),
            ('2020-09-30',   0, 123.97, 123.97,         0),
            ('2020-10-31',   0, 123.97, 123.97,         0),
            ('2020-11-30',   0, 123.97, 123.97,         0),
            ('2020-12-07',   0,  28.92,  28.92,         0),
        ]
        self.assertEqual(self.company.currency_id.round(sum(x[2] for x in expected_line_values)), 500)
        move = self.create_invoice('out_invoice', [revenue_line], post=True, date='2020-08-07')
        self.assert_invoice_lines(move, expected_line_values, self.revenue_accounts[0], self.company_data['default_account_deferred_revenue'])

    def test_deferred_expense_avoid_useless_deferred_entries(self):
        """
        If we have an invoice with a start date in the beginning of the month, and an end date in the end of the month,
        we should not create the deferred entries because the original invoice will be totally deferred
        on the last day of the month, but the full amount will be accounted for on the same day too, thus
        cancelling each other. Therefore we should not create the deferred entries. This is only the case
        if the invoice date is also inside the deferred period.
        """
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 1680, '2023-01-01', '2023-01-31')], date='2023-01-01')
        self.assertEqual(len(move.deferred_move_ids), 0)
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 1680, '2023-01-01', '2023-01-31')], date='2022-01-01')
        self.assertEqual(len(move.deferred_move_ids), 2)

    def test_deferred_expense_single_period_entries(self):
        """
        If we have an invoice covering only one period, we should only avoid creating deferral entries when the
        accounting date is the same as the period for the deferral. Otherwise we should still generate a deferral entry.
        """
        self.company.deferred_expense_amount_computation_method = 'month'
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 1680, '2023-02-01', '2023-02-28')])
        self.assertRecordValues(move.deferred_move_ids, [
            {'date': fields.Date.to_date('2023-01-01')},
            {'date': fields.Date.to_date('2023-02-28')},
        ])

    def test_taxes_deferred_after_date_added(self):
        """
        Test that applicable taxes get deferred also when the dates of the base line are filled in after a first save.
        """

        expected_line_values = [
            # Date         [Line expense] [Line deferred]
            ('2022-12-10',     0,    100,     100,     0),
            ('2022-12-10',     0,   1000,    1000,     0),
            ('2023-01-31',    25,      0,       0,    25),
            ('2023-01-31',   250,      0,       0,   250),
            ('2023-02-28',    25,      0,       0,    25),
            ('2023-02-28',   250,      0,       0,   250),
            ('2023-03-31',    25,      0,       0,    25),
            ('2023-03-31',   250,      0,       0,   250),
        ]

        partially_deductible_tax = self.env['account.tax'].create({
            'name': 'Partially deductible Tax',
            'amount': 20,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True
                }),
            ],
        })

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2022-12-10',
            'invoice_date': '2022-12-10',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1,
                    'account_id': self.expense_lines[0][0].id,
                    'price_unit': self.expense_lines[0][1],
                    'tax_ids': [Command.set(partially_deductible_tax.ids)],
                })
            ]
        })

        move.invoice_line_ids.write({
            'deferred_start_date': self.expense_lines[0][2],
            'deferred_end_date': self.expense_lines[0][3],
        })

        move.action_post()

        self.assert_invoice_lines(move, expected_line_values, self.expense_accounts[0], self.company_data['default_account_deferred_expense'])

    def test_deferred_tax_key(self):
        """
        Test that the deferred tax key is correctly computed.
        and is the same between _compute_tax_key and _compute_all_tax
        """
        lines = [
            [self.expense_accounts[0], 1000, '2023-01-01', '2023-04-30'],
            [self.expense_accounts[0], 1000, False, False],
        ]
        move = self.create_invoice('in_invoice', lines, post=True)
        original_amount_total = move.amount_total
        self.assertEqual(len(move.line_ids.filtered(lambda l: l.display_type == 'tax')), 1)
        move.button_draft()
        move.action_post()
        # The number of tax lines shouldn't change, nor the total amount
        self.assertEqual(len(move.line_ids.filtered(lambda l: l.display_type == 'tax')), 1)
        self.assertEqual(move.amount_total, original_amount_total)

    def test_compute_empty_start_date(self):
        """
        Test that the deferred start date is computed when empty and posting the move.
        """
        lines = [[self.expense_accounts[0], 1000, False, '2023-04-30']]
        move = self.create_invoice('in_invoice', lines, post=False)

        # We don't have a deferred date in the beginning
        self.assertFalse(move.line_ids[0].deferred_start_date)

        move.action_post()
        # Deferred start date is set after post
        self.assertEqual(move.line_ids[0].deferred_start_date, datetime.date(2023, 1, 1))

        move.button_draft()
        move.line_ids[0].deferred_start_date = False
        move.invoice_date = '2023-02-01'
        # Start date is set when changing invoice date
        self.assertEqual(move.line_ids[0].deferred_start_date, datetime.date(2023, 2, 1))

        move.line_ids[0].deferred_start_date = False
        move.line_ids[0].deferred_end_date = '2023-05-31'
        # Start date is set when changing deferred end date
        self.assertEqual(move.line_ids[0].deferred_start_date, datetime.date(2023, 2, 1))

    def test_deferred_on_accounting_date(self):
        """
        When we are in `on_validation` mode, the deferral of the total amount should happen on the
        accounting date of the move.
        """
        move = self.create_invoice(
            'in_invoice',
            [(self.expense_accounts[0], 1680, '2023-01-01', '2023-02-28')],
            date='2023-01-10',
            post=False
        )
        move.date = '2023-01-15'
        move.action_post()
        self.assertRecordValues(move.deferred_move_ids, [
            {'date': fields.Date.to_date('2023-01-15')},
            {'date': fields.Date.to_date('2023-01-31')},
            {'date': fields.Date.to_date('2023-02-28')},
        ])

    def test_deferred_entries_not_created_on_future_invoice(self):
        """Test that we don't create deferred entries on a future posted invoice"""
        tomorrow = fields.Date.to_date(fields.Date.today()) + datetime.timedelta(days=1)
        move = self.create_invoice(
            'out_invoice',
            [(self.expense_accounts[0], 1680, tomorrow, tomorrow + datetime.timedelta(days=100))],
            date=tomorrow,
            post=False
        )
        move.auto_post = "at_date"
        move._post()
        self.assertFalse(move.deferred_move_ids)

        with freeze_time(tomorrow):
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
            self.assertEqual(move.state, 'posted')
            self.assertTrue(move.deferred_move_ids)

    def test_deferred_entries_created_on_auto_post_invoice(self):
        """Test that deferred entries are created on an invoice with auto_post set to 'at_date'"""
        yesterday = fields.Date.to_date(fields.Date.today()) - datetime.timedelta(days=1)
        move = self.create_invoice(
            'out_invoice',
            [(self.expense_accounts[0], 1680, yesterday, yesterday + datetime.timedelta(days=45))],
            date=yesterday,
            post=False
        )
        move.auto_post = "at_date"
        move._post()
        self.assertEqual(move.state, 'posted')
        self.assertTrue(move.deferred_move_ids)

    def test_deferred_compute_method_full_months(self):
        """
        Test that the deferred amount is correctly computed when the new full_months method computation is used
        """
        self.company.deferred_expense_amount_computation_method = 'full_months'

        dates = (('2024-06-05', '2025-06-04'), ('2024-06-30', '2025-06-29'))
        for (date_from, date_to) in dates:
            move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, date_from, date_to)], date='2024-06-05')
            self.assertRecordValues(move.deferred_move_ids.sorted('date'), [
                {'date': fields.Date.to_date('2024-06-05'), 'amount_total': 12000},
                {'date': fields.Date.to_date('2024-06-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-07-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-08-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-09-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-10-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-11-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-12-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-01-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-02-28'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-03-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-04-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-05-31'), 'amount_total': 1000},
                # 0 for June 2025, so no move created
            ])

        # Start of month <=> Equal per month method
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-07-01', '2025-06-30')], date='2024-07-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-07-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-07-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-08-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-09-30'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-10-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-11-30'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-12-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-01-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-02-28'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-03-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-04-30'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-05-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-06-30'), 'amount_total': 1000},
        ])

        # Nothing to defer, everything is in the same month
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-01', '2024-01-16')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Round period of 2 months -> Divide by 2
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-01', '2024-02-29')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 6000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 6000},
        ])

        # Round period of 2 months -> Divide by 2
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-15', '2024-03-14')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 6000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 6000},
        ])

        # Period of exactly one month: full amount should be in Jan. So we revert 1st Jan, and account for 31st Jan <=> don't generate anything
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-15', '2024-02-14')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Not-round period of 1.5 month with only one end of month in January (same explanation as above)
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-01', '2024-02-15')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Not-round period of 1.5+ month with only one end of month in January (same explanation as above)
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-05', '2024-02-15')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Period of exactly one month: full amount should be in Feb. So we revert 1st Jan, and account for all on 29th Feb.
        # Deferrals are in different months for this case, so the deferrals should be generated.
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-02-15', '2024-03-14')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 12000},
        ])

        # Not-round period of 1.5+ month: full amount should be in Feb. So we revert 1st Jan, and account for all on 29th Feb.
        # Deferrals are in different months for this case, so the deferrals should be generated.
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-02-05', '2024-03-15')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 12000},
        ])

        # Not-round period of 1.5 month with 2 ends of months, so divide balance by 2
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-16', '2024-02-29')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 6000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 6000},
        ])

        # Not-round period of 2.5 month, with 3 ends of months, so divide balance by 3
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], 12000, '2024-01-16', '2024-03-31')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 4000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 4000},
            {'date': fields.Date.to_date('2024-03-31'), 'amount_total': 4000},
        ])

    def test_deferred_compute_method_full_months_revenue(self):
        """
        Test that the deferred amount is correctly computed when the new full_months method computation is used
        """
        self.company.deferred_revenue_amount_computation_method = 'full_months'

        dates = (('2024-06-05', '2025-06-04'), ('2024-06-30', '2025-06-29'))
        for (date_from, date_to) in dates:
            move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, date_from, date_to)], date='2024-06-05')
            self.assertRecordValues(move.deferred_move_ids.sorted('date'), [
                {'date': fields.Date.to_date('2024-06-05'), 'amount_total': 12000},
                {'date': fields.Date.to_date('2024-06-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-07-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-08-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-09-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-10-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-11-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2024-12-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-01-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-02-28'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-03-31'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-04-30'), 'amount_total': 1000},
                {'date': fields.Date.to_date('2025-05-31'), 'amount_total': 1000},
                # 0 for June 2025, so no move created
            ])

        # Start of month <=> Equal per month method
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-07-01', '2025-06-30')], date='2024-07-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-07-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-07-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-08-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-09-30'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-10-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-11-30'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2024-12-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-01-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-02-28'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-03-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-04-30'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-05-31'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-06-30'), 'amount_total': 1000},
        ])

        # Nothing to defer, everything is in the same month
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-01', '2024-01-16')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Round period of 2 months -> Divide by 2
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-01', '2024-02-29')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 6000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 6000},
        ])

        # Round period of 2 months -> Divide by 2
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-15', '2024-03-14')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 6000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 6000},
        ])

        # Period of exactly one month: full amount should be in Jan. So we revert 1st Jan, and account for 31st Jan <=> don't generate anything
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-15', '2024-02-14')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Not-round period of 1.5 month with only one end of month in January (same explanation as above)
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-01', '2024-02-15')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Not-round period of 1.5+ month with only one end of month in January (same explanation as above)
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-05', '2024-02-15')], date='2024-01-01')
        self.assertFalse(move.deferred_move_ids)

        # Period of exactly one month: full amount should be in Feb. So we revert 1st Jan, and account for all on 29th Feb.
        # Deferrals are in different months for this case, so the deferrals should be generated.
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-02-15', '2024-03-14')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 12000},
        ])

        # Not-round period of 1.5+ month: full amount should be in Feb. So we revert 1st Jan, and account for all on 29th Feb.
        # Deferrals are in different months for this case, so the deferrals should be generated.
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-02-05', '2024-03-15')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 12000},
        ])

        # Not-round period of 1.5 month with 2 ends of months, so divide balance by 2
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-16', '2024-02-29')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 6000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 6000},
        ])

        # Not-round period of 2.5 month, with 3 ends of months, so divide balance by 3
        move = self.create_invoice('out_invoice', [(self.revenue_accounts[0], 12000, '2024-01-16', '2024-03-31')], date='2024-01-01')
        self.assertRecordValues(move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)), [
            {'date': fields.Date.to_date('2024-01-01'), 'amount_total': 12000},
            {'date': fields.Date.to_date('2024-01-31'), 'amount_total': 4000},
            {'date': fields.Date.to_date('2024-02-29'), 'amount_total': 4000},
            {'date': fields.Date.to_date('2024-03-31'), 'amount_total': 4000},
        ])

    def test_deferral_moves_not_removed(self):
        """
        Test that when there are multiple amls with the same price on the original invoice the deferral_moves are not removed
        """
        move = self.create_invoice('in_invoice', [
            (self.expense_accounts[0], 1000, '2025-05-10', '2025-05-25'),
            (self.expense_accounts[0], 1000, '2025-05-10', '2025-05-25')
        ], date='2025-04-11')
        self.assertEqual(len(move.deferred_move_ids), 4)

    def test_case_1_deferred_entries_computations_period_across_months(self):
        """
        Tests deferred expense recognition when the invoice is dated in a month
        after the service period has already begun.
        Corresponds to Case from Row 6 of the user's image.

        - Service Period: June 25, 2024 -> July 7, 2024 (13 days)
        - Invoice Date: July 1, 2024
        - Expected: The system should correctly create a back-dated expense entry for
          the 6 days in June (dated June 30) and an entry for the 7 days in July
          (dated July 7).
        """
        invoice_date = '2024-07-01'
        invoice_line_data = [self.expense_accounts[0], 1300, '2024-06-25', '2024-07-07']

        expected_line_values = [
            ('2024-06-30',       600,     0,      0,      600),
            (invoice_date,         0,  1300,   1300,        0),
            ('2024-07-07',       700,     0,      0,      700),
        ]

        move = self.create_invoice(
            'in_invoice', [invoice_line_data], date=invoice_date
        )

        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data['default_account_deferred_expense']
        )

    def test_case_2_deferred_entries_computations_period_across_months(self):
        """
           Tests deferred expense recognition when the invoice is dated within the
           service period, which spans across two months.
           Corresponds to Case from Row 7 of the user's image.

           - Service Period: June 25, 2024 -> July 7, 2024 (13 days)
           - Invoice Date: June 29, 2024
           - Expected: The system should correctly prorate the expense with 6 days
             in June and 7 days in July.
        """
        invoice_date = '2024-06-29'
        invoice_line_data = [self.expense_accounts[0], 1300, '2024-06-25', '2024-07-07']

        expected_line_values = [
            (invoice_date,         0,  1300,   1300,        0),
            ('2024-06-30',       600,     0,      0,      600),
            ('2024-07-07',       700,     0,      0,     700),
        ]

        move = self.create_invoice(
            'in_invoice', [invoice_line_data], date=invoice_date
        )

        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data['default_account_deferred_expense']
        )

    def test_case_3_deferred_entries_computations_period_across_months(self):
        """
        Tests deferred expense recognition for a longer service period that spans
        across two months, with the invoice dated within the first month.
        Corresponds to Case from Row 8 in the user's image.

        - Service Period: June 25, 2024 -> July 23, 2024 (29 days)
        - Invoice Date: June 29, 2024
        - Expected: The system should correctly split the expense between June
          (6/29 of total) and July (23/29 of total).
        """
        invoice_date = '2024-06-29'
        # Using 2900 for the amount to keep the numbers clean
        invoice_line_data = [self.expense_accounts[0], 2900, '2024-06-25', '2024-07-23']

        expected_line_values = [
            (invoice_date,         0,  2900,   2900,        0),
            ('2024-06-30',       600,     0,      0,      600),
            ('2024-07-23',      2300,     0,      0,     2300),
        ]

        move = self.create_invoice(
            'in_invoice', [invoice_line_data], date=invoice_date
        )

        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data['default_account_deferred_expense']
        )

    def test_deferred_moves_from_same_move_different_lines(self):
        """
        Test that fully deferred move and deferral move from different lines are not cancelling each other
        when having the same amount.
        """
        move = self.create_invoice('in_invoice', [(self.expense_accounts[0], amount, '2025-10-01', '2025-11-30') for amount in (1000, 500)], date='2025-11-30')
        self.assertRecordValues(move.deferred_move_ids.sorted('date'), [
            {'date': fields.Date.to_date('2025-10-31'), 'amount_total': 500},
            {'date': fields.Date.to_date('2025-10-31'), 'amount_total': 250},
            {'date': fields.Date.to_date('2025-11-30'), 'amount_total': 1000},
            {'date': fields.Date.to_date('2025-11-30'), 'amount_total': 500},
            {'date': fields.Date.to_date('2025-11-30'), 'amount_total': 500},
            {'date': fields.Date.to_date('2025-11-30'), 'amount_total': 250},
        ])
