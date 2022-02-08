# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.exceptions import ValidationError, UserError
from odoo import fields

from unittest.mock import patch


class TestAccountBankStatementCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # We need a third currency as you could have a company's currency != journal's currency !=
        cls.currency_data_2 = cls.setup_multi_currency_data(default_values={
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=6.0, rate2017=4.0)
        cls.currency_data_3 = cls.setup_multi_currency_data(default_values={
            'name': 'Black Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Black Choco',
            'currency_subunit_label': 'Black Cacao Powder',
        }, rate2016=12.0, rate2017=8.0)

        cls.bank_journal_1 = cls.company_data['default_journal_bank']
        cls.bank_journal_2 = cls.bank_journal_1.copy()
        cls.bank_journal_3 = cls.bank_journal_2.copy()
        cls.currency_1 = cls.company_data['currency']
        cls.currency_2 = cls.currency_data['currency']
        cls.currency_3 = cls.currency_data_2['currency']
        cls.currency_4 = cls.currency_data_3['currency']

    def assertBankStatementLine(self, statement_line, expected_statement_line_vals, expected_move_line_vals):
        self.assertRecordValues(statement_line, [expected_statement_line_vals])
        self.assertRecordValues(statement_line.line_ids.sorted('balance'), expected_move_line_vals)


@tagged('post_install', '-at_install')
class TestAccountBankStatement(TestAccountBankStatementCommon):

    # -------------------------------------------------------------------------
    # TESTS about the statement model.
    # -------------------------------------------------------------------------

    def test_starting_ending_balance_chaining(self):
        # Create first statement on 2019-01-02.
        bnk1 = self.env['account.bank.statement'].create({
            'name': 'BNK1',
            'date': '2019-01-02',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 100.0})],
        })
        self.assertRecordValues(bnk1, [{
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'balance_end': 100.0,
            'previous_statement_id': False,
        }])

        # Create a new statement after that one.
        bnk2 = self.env['account.bank.statement'].create({
            'name': 'BNK2',
            'date': '2019-01-10',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 50.0})],
        })
        self.assertRecordValues(bnk2, [{
            'balance_start': 100.0,
            'balance_end_real': 150.0,
            'balance_end': 150.0,
            'previous_statement_id': bnk1.id,
        }])

        # Create new statement with given ending balance.
        bnk3 = self.env['account.bank.statement'].create({
            'name': 'BNK3',
            'date': '2019-01-15',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 25.0})],
            'balance_end_real': 200.0,
        })
        self.assertRecordValues(bnk3, [{
            'balance_start': 150.0,
            'balance_end_real': 200.0,
            'balance_end': 175.0,
            'previous_statement_id': bnk2.id,
        }])

        # Create new statement with a date right after BNK1.
        bnk4 = self.env['account.bank.statement'].create({
            'name': 'BNK4',
            'date': '2019-01-03',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 100.0})],
        })
        self.assertRecordValues(bnk4, [{
            'balance_start': 100.0,
            'balance_end_real': 200.0,
            'balance_end': 200.0,
            'previous_statement_id': bnk1.id,
        }])

        # BNK2/BNK3 should have changed their previous statements.
        self.assertRecordValues(bnk2, [{
            'balance_start': 200.0,
            'balance_end_real': 250.0,
            'balance_end': 250.0,
            'previous_statement_id': bnk4.id,
        }])
        self.assertRecordValues(bnk3, [{
            'balance_start': 250.0,
            'balance_end_real': 200.0,
            'balance_end': 275.0,
            'previous_statement_id': bnk2.id,
        }])

        # Correct the ending balance of BNK3.
        bnk3.balance_end_real = 275

        # Change date of BNK4 to be the last.
        bnk4.date = '2019-01-20'
        self.assertRecordValues(bnk1, [{
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'balance_end': 100.0,
            'previous_statement_id': False,
        }])
        self.assertRecordValues(bnk2, [{
            'balance_start': 100.0,
            'balance_end_real': 150.0,
            'balance_end': 150.0,
            'previous_statement_id': bnk1.id,
        }])
        self.assertRecordValues(bnk3, [{
            'balance_start': 150.0,
            'balance_end_real': 175.0,
            'balance_end': 175.0,
            'previous_statement_id': bnk2.id,
        }])
        self.assertRecordValues(bnk4, [{
            'balance_start': 175.0,
            'balance_end_real': 200.0,
            'balance_end': 275.0,
            'previous_statement_id': bnk3.id,
        }])

        # Correct the ending balance of BNK4.
        bnk4.balance_end_real = 275

        # Move BNK3 to first position.
        bnk3.date = '2019-01-01'
        self.assertRecordValues(bnk3, [{
            'balance_start': 0.0,
            'balance_end_real': 25.0,
            'balance_end': 25.0,
            'previous_statement_id': False,
        }])
        self.assertRecordValues(bnk1, [{
            'balance_start': 25.0,
            'balance_end_real': 125.0,
            'balance_end': 125.0,
            'previous_statement_id': bnk3.id,
        }])
        self.assertRecordValues(bnk2, [{
            'balance_start': 125.0,
            'balance_end_real': 175.0,
            'balance_end': 175.0,
            'previous_statement_id': bnk1.id,
        }])
        self.assertRecordValues(bnk4, [{
            'balance_start': 175.0,
            'balance_end_real': 275.0,
            'balance_end': 275.0,
            'previous_statement_id': bnk2.id,
        }])

        # Move BNK1 to the third position.
        bnk1.date = '2019-01-11'
        self.assertRecordValues(bnk3, [{
            'balance_start': 0.0,
            'balance_end_real': 25.0,
            'balance_end': 25.0,
            'previous_statement_id': False,
        }])
        self.assertRecordValues(bnk2, [{
            'balance_start': 25.0,
            'balance_end_real': 75.0,
            'balance_end': 75.0,
            'previous_statement_id': bnk3.id,
        }])
        self.assertRecordValues(bnk1, [{
            'balance_start': 75.0,
            'balance_end_real': 175.0,
            'balance_end': 175.0,
            'previous_statement_id': bnk2.id,
        }])
        self.assertRecordValues(bnk4, [{
            'balance_start': 175.0,
            'balance_end_real': 275.0,
            'balance_end': 275.0,
            'previous_statement_id': bnk1.id,
        }])

        # Delete BNK3 and BNK1.
        (bnk3 + bnk1).unlink()
        self.assertRecordValues(bnk2, [{
            'balance_start': 0.0,
            'balance_end_real': 50.0,
            'balance_end': 50.0,
            'previous_statement_id': False,
        }])
        self.assertRecordValues(bnk4, [{
            'balance_start': 50.0,
            'balance_end_real': 275.0,
            'balance_end': 150.0,
            'previous_statement_id': bnk2.id,
        }])

    def test_statements_different_journal(self):
        # Create statements in bank journal.
        bnk1_1 = self.env['account.bank.statement'].create({
            'name': 'BNK1_1',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 100.0})],
            'balance_end_real': 100.0,
        })
        bnk1_2 = self.env['account.bank.statement'].create({
            'name': 'BNK1_2',
            'date': '2019-01-10',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 50.0})],
        })

        # Create statements in cash journal.
        bnk2_1 = self.env['account.bank.statement'].create({
            'name': 'BNK2_1',
            'date': '2019-01-02',
            'journal_id': self.company_data['default_journal_cash'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 20.0})],
            'balance_end_real': 20.0,
        })
        bnk2_2 = self.env['account.bank.statement'].create({
            'name': 'BNK2_2',
            'date': '2019-01-12',
            'journal_id': self.company_data['default_journal_cash'].id,
            'line_ids': [(0, 0, {'payment_ref': '/', 'amount': 10.0})],
        })
        self.assertRecordValues(bnk1_1, [{
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'balance_end': 100.0,
            'previous_statement_id': False,
        }])
        self.assertRecordValues(bnk1_2, [{
            'balance_start': 100.0,
            'balance_end_real': 150.0,
            'balance_end': 150.0,
            'previous_statement_id': bnk1_1.id,
        }])
        self.assertRecordValues(bnk2_1, [{
            'balance_start': 0.0,
            'balance_end_real': 20.0,
            'balance_end': 20.0,
            'previous_statement_id': False,
        }])
        self.assertRecordValues(bnk2_2, [{
            'balance_start': 20.0,
            'balance_end_real': 0.0,
            'balance_end': 30.0,
            'previous_statement_id': bnk2_1.id,
        }])

    def test_cash_statement_with_difference(self):
        ''' A cash statement always creates an additional line to store the cash difference towards the ending balance.
        '''
        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_cash'].id,
            'balance_end_real': 100.0,
        })

        statement.button_post()

        self.assertRecordValues(statement.line_ids, [{
            'amount': 100.0,
            'is_reconciled': True,
        }])


@tagged('post_install', '-at_install')
class TestAccountBankStatementLine(TestAccountBankStatementCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.statement = cls.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': cls.bank_journal_1.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': cls.partner_a.id,
                    'foreign_currency_id': cls.currency_2.id,
                    'amount': 1250.0,
                    'amount_currency': 2500.0,
                }),
            ],
        })
        cls.statement_line = cls.statement.line_ids

        cls.expected_st_line = {
            'date': fields.Date.from_string('2019-01-01'),
            'journal_id': cls.statement.journal_id.id,
            'payment_ref': 'line_1',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_1.id,
            'foreign_currency_id': cls.currency_2.id,
            'amount': 1250.0,
            'amount_currency': 2500.0,
            'is_reconciled': False,
        }

        cls.expected_bank_line = {
            'name': cls.statement_line.payment_ref,
            'partner_id': cls.statement_line.partner_id.id,
            'currency_id': cls.currency_2.id,
            'account_id': cls.statement.journal_id.default_account_id.id,
            'debit': 1250.0,
            'credit': 0.0,
            'amount_currency': 2500.0,
        }

        cls.expected_counterpart_line = {
            'name': cls.statement_line.payment_ref,
            'partner_id': cls.statement_line.partner_id.id,
            'currency_id': cls.currency_2.id,
            'account_id': cls.statement.journal_id.suspense_account_id.id,
            'debit': 0.0,
            'credit': 1250.0,
            'amount_currency': -2500.0,
        }

    # -------------------------------------------------------------------------
    # TESTS about the statement line model.
    # -------------------------------------------------------------------------

    def _test_statement_line_edition(
            self,
            journal,
            amount, amount_currency,
            journal_currency, foreign_currency,
            expected_liquidity_values, expected_counterpart_values):
        ''' Test the edition of a statement line from itself or from its linked journal entry.
        :param journal:                     The account.journal record that will be set on the statement line.
        :param amount:                      The amount in journal's currency.
        :param amount_currency:             The amount in the foreign currency.
        :param journal_currency:            The journal's currency as a res.currency record.
        :param foreign_currency:            The foreign currency as a res.currency record.
        :param expected_liquidity_values:   The expected account.move.line values for the liquidity line.
        :param expected_counterpart_values: The expected account.move.line values for the counterpart line.
        '''
        if journal_currency:
            journal.currency_id = journal_currency.id

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': journal.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': foreign_currency and foreign_currency.id,
                    'amount': amount,
                    'amount_currency': amount_currency,
                }),
            ],
        })
        statement_line = statement.line_ids

        # ==== Test the statement line amounts are correct ====
        # If there is a bug in the compute/inverse methods, the amount/amount_currency could be
        # incorrect directly after the creation of the statement line.

        self.assertRecordValues(statement_line, [{
            'amount': amount,
            'amount_currency': amount_currency,
        }])
        self.assertRecordValues(statement_line.move_id, [{
            'partner_id': self.partner_a.id,
            'currency_id': (statement_line.foreign_currency_id or statement_line.currency_id).id,
        }])

        # ==== Test the edition of statement line amounts ====
        # The statement line must remain consistent with its account.move.
        # To test the compute/inverse methods are correctly managing all currency setup,
        # we check the edition of amounts in both directions statement line <-> journal entry.

        # Check initial state of the statement line.
        liquidity_lines, suspense_lines, other_lines = statement_line._seek_for_lines()
        self.assertRecordValues(liquidity_lines, [expected_liquidity_values])
        self.assertRecordValues(suspense_lines, [expected_counterpart_values])

        # Check the account.move is still correct after editing the account.bank.statement.line.
        statement_line.write({
            'amount': statement_line.amount * 2,
            'amount_currency': statement_line.amount_currency * 2,
        })
        self.assertRecordValues(statement_line, [{
            'amount': amount * 2,
            'amount_currency': amount_currency * 2,
        }])
        self.assertRecordValues(liquidity_lines, [{
            **expected_liquidity_values,
            'debit': expected_liquidity_values.get('debit', 0.0) * 2,
            'credit': expected_liquidity_values.get('credit', 0.0) * 2,
            'amount_currency': expected_liquidity_values.get('amount_currency', 0.0) * 2,
        }])
        self.assertRecordValues(suspense_lines, [{
            'debit': expected_counterpart_values.get('debit', 0.0) * 2,
            'credit': expected_counterpart_values.get('credit', 0.0) * 2,
            'amount_currency': expected_counterpart_values.get('amount_currency', 0.0) * 2,
        }])

        # Check the account.bank.statement.line is still correct after editing the account.move.
        statement_line.move_id.write({'line_ids': [
            (1, liquidity_lines.id, {
                'debit': expected_liquidity_values.get('debit', 0.0),
                'credit': expected_liquidity_values.get('credit', 0.0),
                'amount_currency': expected_liquidity_values.get('amount_currency', 0.0),
            }),
            (1, suspense_lines.id, {
                'debit': expected_counterpart_values.get('debit', 0.0),
                'credit': expected_counterpart_values.get('credit', 0.0),
                'amount_currency': expected_counterpart_values.get('amount_currency', 0.0),
            }),
        ]})
        self.assertRecordValues(statement_line, [{
            'amount': amount,
            'amount_currency': amount_currency,
        }])

    def _test_edition_customer_and_supplier_flows(
            self,
            amount, amount_currency,
            journal_currency, foreign_currency,
            expected_liquidity_values, expected_counterpart_values):
        ''' Test '_test_statement_line_edition' using the customer (positive amounts)
        & the supplier flow (negative amounts).
        :param amount:                      The amount in journal's currency.
        :param amount_currency:             The amount in the foreign currency.
        :param journal_currency:            The journal's currency as a res.currency record.
        :param foreign_currency:            The foreign currency as a res.currency record.
        :param expected_liquidity_values:   The expected account.move.line values for the liquidity line.
        :param expected_counterpart_values: The expected account.move.line values for the counterpart line.
        '''

        # Check the full process with positive amount (customer process).
        self._test_statement_line_edition(
            self.bank_journal_2,
            amount, amount_currency,
            journal_currency, foreign_currency,
            expected_liquidity_values,
            expected_counterpart_values,
        )

        # Check the full process with negative amount (supplier process).
        self._test_statement_line_edition(
            self.bank_journal_3,
            -amount, -amount_currency,
            journal_currency, foreign_currency,
            {
                **expected_liquidity_values,
                'debit': expected_liquidity_values.get('credit', 0.0),
                'credit': expected_liquidity_values.get('debit', 0.0),
                'amount_currency': -expected_liquidity_values.get('amount_currency', 0.0),
            },
            {
                **expected_counterpart_values,
                'debit': expected_counterpart_values.get('credit', 0.0),
                'credit': expected_counterpart_values.get('debit', 0.0),
                'amount_currency': -expected_counterpart_values.get('amount_currency', 0.0),
            },
        )

    def test_edition_journal_curr_2_statement_curr_3(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,               120.0,
            self.currency_2,    self.currency_3,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -120.0,      'currency_id': self.currency_3.id},
        )

    def test_edition_journal_curr_2_statement_curr_1(self):
        self._test_edition_customer_and_supplier_flows(
            120.0,              80.0,
            self.currency_2,    self.currency_1,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_edition_journal_curr_1_statement_curr_2(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,               120.0,
            self.currency_1,    self.currency_2,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -120.0,      'currency_id': self.currency_2.id},
        )

    def test_edition_journal_curr_2_statement_false(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,               0.0,
            self.currency_2,    False,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -80.0,       'currency_id': self.currency_2.id},
        )

    def test_edition_journal_curr_1_statement_false(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,               0.0,
            self.currency_1,    False,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_1.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_zero_amount_journal_curr_1_statement_curr_2(self):
        self.bank_journal_2.currency_id = self.currency_1

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': self.currency_2.id,
                    'amount': 0.0,
                    'amount_currency': 10.0,
                }),
            ],
        })

        self.assertRecordValues(statement.line_ids.move_id.line_ids, [
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 10.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -10.0,       'currency_id': self.currency_2.id},
        ])

    def test_zero_amount_currency_journal_curr_1_statement_curr_2(self):
        self.bank_journal_2.currency_id = self.currency_1

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': self.currency_2.id,
                    'amount': 10.0,
                    'amount_currency': 0.0,
                }),
            ],
        })

        self.assertRecordValues(statement.line_ids.move_id.line_ids, [
            {'debit': 10.0,     'credit': 0.0,      'amount_currency': 0.0,         'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 10.0,     'amount_currency': 0.0,         'currency_id': self.currency_2.id},
        ])

    def test_zero_amount_journal_curr_2_statement_curr_1(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': self.currency_1.id,
                    'amount': 0.0,
                    'amount_currency': 10.0,
                }),
            ],
        })

        self.assertRecordValues(statement.line_ids.move_id.line_ids, [
            {'debit': 10.0,     'credit': 0.0,      'amount_currency': 0.0,         'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 10.0,     'amount_currency': -10.0,       'currency_id': self.currency_1.id},
        ])

    def test_zero_amount_currency_journal_curr_2_statement_curr_1(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': self.currency_1.id,
                    'amount': 10.0,
                    'amount_currency': 0.0,
                }),
            ],
        })

        self.assertRecordValues(statement.line_ids.move_id.line_ids, [
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 10.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,         'currency_id': self.currency_1.id},
        ])

    def test_zero_amount_journal_curr_2_statement_curr_3(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': self.currency_3.id,
                    'amount': 0.0,
                    'amount_currency': 10.0,
                }),
            ],
        })

        self.assertRecordValues(statement.line_ids.move_id.line_ids, [
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,         'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -10.0,       'currency_id': self.currency_3.id},
        ])

    def test_zero_amount_currency_journal_curr_2_statement_curr_3(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': self.currency_3.id,
                    'amount': 10.0,
                    'amount_currency': 0.0,
                }),
            ],
        })

        self.assertRecordValues(statement.line_ids.move_id.line_ids, [
            {'debit': 5.0,      'credit': 0.0,      'amount_currency': 10.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 5.0,      'amount_currency': 0.0,         'currency_id': self.currency_3.id},
        ])

    def test_constraints(self):
        def assertStatementLineConstraint(statement_vals, statement_line_vals):
            with self.assertRaises(Exception), self.cr.savepoint():
                self.env['account.bank.statement'].create({
                    **statement_vals,
                    'line_ids': [(0, 0, statement_line_vals)],
                })

        statement_vals = {
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_2.id,
        }
        statement_line_vals = {
            'date': '2019-01-01',
            'payment_ref': 'line_1',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': False,
            'amount': 10.0,
            'amount_currency': 0.0,
        }

        # ==== Test constraints at creation ====

        # Foreign currency must not be the same as the journal one.
        assertStatementLineConstraint(statement_vals, {
            **statement_line_vals,
            'foreign_currency_id': self.currency_1.id,
        })

        # Can't have a stand alone amount in foreign currency without foreign currency set.
        assertStatementLineConstraint(statement_vals, {
            **statement_line_vals,
            'amount_currency': 10.0,
        })

        # ==== Test constraints at edition ====

        statement = self.env['account.bank.statement'].create({
            **statement_vals,
            'line_ids': [(0, 0, statement_line_vals)],
        })
        st_line = statement.line_ids

        # You can't messed up the journal entry by adding another liquidity line.
        addition_lines_to_create = [
            {
                'debit': 1.0,
                'credit': 0,
                'account_id': self.bank_journal_2.default_account_id.id,
                'move_id': st_line.move_id.id,
            },
            {
                'debit': 0,
                'credit': 1.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'move_id': st_line.move_id.id,
            },
        ]
        with self.assertRaises(UserError), self.cr.savepoint():
            st_line.move_id.write({
                'line_ids': [(0, 0, vals) for vals in addition_lines_to_create]
            })

        with self.assertRaises(UserError), self.cr.savepoint():
            st_line.line_ids.create(addition_lines_to_create)

        # You can't set the journal entry in an unconsistent state.
        with self.assertRaises(UserError), self.cr.savepoint():
            st_line.move_id.action_post()

    def test_statement_line_move_onchange_1(self):
        ''' Test the consistency between the account.bank.statement.line and the generated account.move.lines
        using the form view emulator.
        '''

        # Check the initial state of the statement line.
        self.assertBankStatementLine(self.statement_line, self.expected_st_line, [self.expected_counterpart_line, self.expected_bank_line])

        # Inverse the amount + change them.
        with Form(self.statement) as statement_form:
            with statement_form.line_ids.edit(0) as st_line_form:
                st_line_form.amount = -2000.0
                st_line_form.amount_currency = -4000.0
                st_line_form.foreign_currency_id = self.currency_3

        self.assertBankStatementLine(self.statement_line, {
            **self.expected_st_line,
            'amount': -2000.0,
            'amount_currency': -4000.0,
            'foreign_currency_id': self.currency_3.id,
        }, [
            {
                **self.expected_bank_line,
                'debit': 0.0,
                'credit': 2000.0,
                'amount_currency': -4000.0,
                'currency_id': self.currency_3.id,
            },
            {
                **self.expected_counterpart_line,
                'debit': 2000.0,
                'credit': 0.0,
                'amount_currency': 4000.0,
                'currency_id': self.currency_3.id,
            },
        ])

        # Check changing the label and the partner.
        with Form(self.statement) as statement_form:
            with statement_form.line_ids.edit(0) as st_line_form:
                st_line_form.payment_ref = 'line_1 (bis)'
                st_line_form.partner_id = self.partner_b

        self.assertBankStatementLine(self.statement_line, {
            **self.expected_st_line,
            'payment_ref': self.statement_line.payment_ref,
            'partner_id': self.statement_line.partner_id.id,
            'amount': -2000.0,
            'amount_currency': -4000.0,
            'foreign_currency_id': self.currency_3.id,
        }, [
            {
                **self.expected_bank_line,
                'name': self.statement_line.payment_ref,
                'partner_id': self.statement_line.partner_id.id,
                'debit': 0.0,
                'credit': 2000.0,
                'amount_currency': -4000.0,
                'currency_id': self.currency_3.id,
            },
            {
                **self.expected_counterpart_line,
                'name': self.statement_line.payment_ref,
                'partner_id': self.statement_line.partner_id.id,
                'debit': 2000.0,
                'credit': 0.0,
                'amount_currency': 4000.0,
                'currency_id': self.currency_3.id,
            },
        ])

    # -------------------------------------------------------------------------
    # TESTS about reconciliation:
    # - Test '_prepare_counterpart_move_line_vals': one test for each case.
    # - Test 'reconcile': 3 cases:
    #       - Open-balance in debit.
    #       - Open-balance in credit.
    #       - No open-balance.
    # - Test 'button_undo_reconciliation'.
    # -------------------------------------------------------------------------

    def _test_statement_line_reconciliation(
            self,
            journal,
            amount, amount_currency, counterpart_amount,
            journal_currency, foreign_currency, counterpart_currency,
            expected_liquidity_values, expected_counterpart_values):
        ''' Test the reconciliation of a statement line.
        :param journal:                     The account.journal record that will be set on the statement line.
        :param amount:                      The amount in journal's currency.
        :param amount_currency:             The amount in the foreign currency.
        :param counterpart_amount:          The amount of the invoice to reconcile.
        :param journal_currency:            The journal's currency as a res.currency record.
        :param foreign_currency:            The foreign currency as a res.currency record.
        :param counterpart_currency:        The invoice currency as a res.currency record.
        :param expected_liquidity_values:   The expected account.move.line values for the liquidity line.
        :param expected_counterpart_values: The expected account.move.line values for the counterpart line.
        '''
        if journal_currency:
            journal.currency_id = journal_currency.id

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': journal.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': foreign_currency and foreign_currency.id,
                    'amount': amount,
                    'amount_currency': amount_currency,
                }),
            ],
        })
        statement_line = statement.line_ids

        # - There is 3 flows to check:
        #   * The invoice will fully reconcile the statement line.
        #   * The invoice will partially reconcile the statement line and leads to an open balance in debit.
        #   * The invoice will partially reconcile the statement line and leads to an open balance in credit.
        # - The dates are different to be sure the reconciliation will preserve the conversion rate bank side.
        move_type = 'out_invoice' if counterpart_amount < 0.0 else 'in_invoice'

        test_invoices = self.env['account.move'].create([
            {
                'move_type': move_type,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'date': fields.Date.from_string('2016-01-01'),
                'partner_id': self.partner_a.id,
                'currency_id': counterpart_currency.id,
                'invoice_line_ids': [
                    (0, None, {
                        'name': 'counterpart line, same amount',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'quantity': 1,
                        'price_unit': abs(counterpart_amount),
                    }),
                ],
            },
            {
                'move_type': move_type,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'date': fields.Date.from_string('2016-01-01'),
                'partner_id': self.partner_a.id,
                'currency_id': counterpart_currency.id,
                'invoice_line_ids': [
                    (0, None, {
                        'name': 'counterpart line, lower amount',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'quantity': 1,
                        'price_unit': abs(counterpart_amount / 2),
                    }),
                ],
            },
            {
                'move_type': move_type,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'date': fields.Date.from_string('2016-01-01'),
                'partner_id': self.partner_a.id,
                'currency_id': counterpart_currency.id,
                'invoice_line_ids': [
                    (0, None, {
                        'name': 'counterpart line, bigger amount',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'quantity': 1,
                        'price_unit': abs(counterpart_amount * 2),
                    }),
                ],
            },
        ])
        test_invoices.action_post()
        statement.button_post()
        counterpart_lines = test_invoices.mapped('line_ids').filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))

        # Check the full reconciliation.
        statement_line.reconcile([{'id': counterpart_lines[0].id}])
        liquidity_lines, suspense_lines, other_lines = statement_line._seek_for_lines()
        self.assertRecordValues(liquidity_lines, [expected_liquidity_values])
        self.assertRecordValues(other_lines, [expected_counterpart_values])

        # Check the reconciliation with partial lower amount.
        statement_line.button_undo_reconciliation()
        statement_line.reconcile([{'id': counterpart_lines[1].id}])
        liquidity_lines, suspense_lines, other_lines = statement_line._seek_for_lines()
        self.assertRecordValues(liquidity_lines, [expected_liquidity_values])
        self.assertRecordValues(other_lines.sorted('balance', reverse=amount < 0.0), [
            {
                **expected_counterpart_values,
                'debit': expected_counterpart_values.get('debit', 0.0) / 2,
                'credit': expected_counterpart_values.get('credit', 0.0) / 2,
                'amount_currency': expected_counterpart_values.get('amount_currency', 0.0) / 2,
            },
            {
                'debit': expected_counterpart_values.get('debit', 0.0) / 2,
                'credit': expected_counterpart_values.get('credit', 0.0) / 2,
                'amount_currency': expected_counterpart_values.get('amount_currency', 0.0) / 2,
                'currency_id': expected_counterpart_values.get('currency_id'),
            },
        ])

        # Check the reconciliation with partial higher amount.
        statement_line.button_undo_reconciliation()
        statement_line.reconcile([{'id': counterpart_lines[2].id}])
        liquidity_lines, suspense_lines, other_lines = statement_line._seek_for_lines()
        self.assertRecordValues(liquidity_lines, [expected_liquidity_values])
        self.assertRecordValues(other_lines.sorted('balance', reverse=amount < 0.0), [
            {
                **expected_counterpart_values,
                'debit': expected_counterpart_values.get('debit', 0.0) * 2,
                'credit': expected_counterpart_values.get('credit', 0.0) * 2,
                'amount_currency': expected_counterpart_values.get('amount_currency', 0.0) * 2,
            },
            {
                'debit': expected_counterpart_values.get('credit', 0.0),
                'credit': expected_counterpart_values.get('debit', 0.0),
                'amount_currency': -expected_counterpart_values.get('amount_currency', 0.0),
                'currency_id': expected_counterpart_values.get('currency_id'),
            },
        ])

        # Make sure the statement line is still correct.
        self.assertRecordValues(statement_line, [{
            'amount': amount,
            'amount_currency': amount_currency,
        }])

    def _test_reconciliation_customer_and_supplier_flows(
            self,
            amount, amount_currency, counterpart_amount,
            journal_currency, foreign_currency, counterpart_currency,
            expected_liquidity_values, expected_counterpart_values):
        ''' Test '_test_statement_line_reconciliation' using the customer (positive amounts)
        & the supplier flow (negative amounts).
        :param amount:                      The amount in journal's currency.
        :param amount_currency:             The amount in the foreign currency.
        :param counterpart_amount:          The amount of the invoice to reconcile.
        :param journal_currency:            The journal's currency as a res.currency record.
        :param foreign_currency:            The foreign currency as a res.currency record.
        :param counterpart_currency:        The invoice currency as a res.currency record.
        :param expected_liquidity_values:   The expected account.move.line values for the liquidity line.
        :param expected_counterpart_values: The expected account.move.line values for the counterpart line.
        '''

        # Check the full process with positive amount (customer process).
        self._test_statement_line_reconciliation(
            self.bank_journal_2,
            amount, amount_currency, counterpart_amount,
            journal_currency, foreign_currency, counterpart_currency,
            expected_liquidity_values,
            expected_counterpart_values,
        )

        # Check the full process with negative amount (supplier process).
        self._test_statement_line_reconciliation(
            self.bank_journal_3,
            -amount, -amount_currency, -counterpart_amount,
            journal_currency, foreign_currency, counterpart_currency,
            {
                **expected_liquidity_values,
                'debit': expected_liquidity_values.get('credit', 0.0),
                'credit': expected_liquidity_values.get('debit', 0.0),
                'amount_currency': -expected_liquidity_values.get('amount_currency', 0.0),
            },
            {
                **expected_counterpart_values,
                'debit': expected_counterpart_values.get('credit', 0.0),
                'credit': expected_counterpart_values.get('debit', 0.0),
                'amount_currency': -expected_counterpart_values.get('amount_currency', 0.0),
            },
        )

    def test_reconciliation_journal_curr_2_statement_curr_3_counterpart_curr_3(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               120.0,              -120.0,
            self.currency_2,    self.currency_3,    self.currency_3,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -120.0,      'currency_id': self.currency_3.id},
        )

    def test_reconciliation_journal_curr_2_statement_curr_1_counterpart_curr_2(self):
        self._test_reconciliation_customer_and_supplier_flows(
            120.0,              80.0,               -120.0,
            self.currency_2,    self.currency_1,    self.currency_2,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_reconciliation_journal_curr_2_statement_curr_3_counterpart_curr_2(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               120.0,              -80.0,
            self.currency_2,    self.currency_3,    self.currency_2,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -120.0,      'currency_id': self.currency_3.id},
        )

    def test_reconciliation_journal_curr_2_statement_curr_3_counterpart_curr_4(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               120.0,              -480.0,
            self.currency_2,    self.currency_3,    self.currency_4,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -120.0,      'currency_id': self.currency_3.id},
        )

    def test_reconciliation_journal_curr_1_statement_curr_2_counterpart_curr_2(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               120.0,              -120.0,
            self.currency_1,    self.currency_2,    self.currency_2,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -120.0,      'currency_id': self.currency_2.id},
        )

    def test_reconciliation_journal_curr_1_statement_curr_2_counterpart_curr_3(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               120.0,              -480.0,
            self.currency_1,    self.currency_2,    self.currency_3,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -120.0,      'currency_id': self.currency_2.id},
        )

    def test_reconciliation_journal_curr_2_statement_false_counterpart_curr_2(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               0.0,                -80.0,
            self.currency_2,    False,              self.currency_2,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -80.0,       'currency_id': self.currency_2.id},
        )

    def test_reconciliation_journal_curr_2_statement_false_counterpart_curr_3(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               0.0,                -240.0,
            self.currency_2,    False,              self.currency_3,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -80.0,       'currency_id': self.currency_2.id},
        )

    def test_reconciliation_journal_curr_1_statement_false_counterpart_curr_3(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               0.0,                -480.0,
            self.currency_1,    False,              self.currency_3,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_1.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_reconciliation_journal_curr_2_statement_curr_1_counterpart_curr_1(self):
        self._test_reconciliation_customer_and_supplier_flows(
            120.0,              80.0,               -80.0,
            self.currency_2,    self.currency_1,    self.currency_1,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_reconciliation_journal_curr_2_statement_curr_3_counterpart_curr_1(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               120.0,              -40.0,
            self.currency_2,    self.currency_3,    self.currency_1,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -120.0,      'currency_id': self.currency_3.id},
        )

    def test_reconciliation_journal_curr_1_statement_curr_2_counterpart_curr_1(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               120.0,              -80.0,
            self.currency_1,    self.currency_2,    self.currency_1,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -120.0,      'currency_id': self.currency_2.id},
        )

    def test_reconciliation_journal_curr_2_statement_false_counterpart_curr_1(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               0.0,                -40.0,
            self.currency_2,    False,              self.currency_1,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -80.0,       'currency_id': self.currency_2.id},
        )

    def test_reconciliation_journal_curr_1_statement_false_counterpart_curr_1(self):
        self._test_reconciliation_customer_and_supplier_flows(
            80.0,               0.0,                -80.0,
            self.currency_1,    False,              self.currency_1,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_1.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_reconciliation_statement_line_state(self):
        ''' Test the reconciliation on the bank statement line with a foreign currency on the journal:
        - Ensure the statement line is_reconciled field is well computed.
        - Ensure the reconciliation is working well when dealing with a foreign currency at different dates.
        - Ensure the reconciliation can be undo.
        - Ensure the reconciliation is still possible with to_check.
        '''
        self.statement.button_post()

        receivable_acc_1 = self.company_data['default_account_receivable']
        receivable_acc_2 = self.copy_account(self.company_data['default_account_receivable'])
        payment_account = self.bank_journal_1.company_id.account_journal_payment_debit_account_id
        random_acc_1 = self.company_data['default_account_revenue']
        random_acc_2 = self.copy_account(self.company_data['default_account_revenue'])
        test_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'line_ids': [
                (0, None, {
                    'name': 'counterpart of the whole move',
                    'account_id': random_acc_1.id,
                    'debit': 0.0,
                    'credit': 1030.0,
                }),
                (0, None, {
                    'name': 'test line 1 - receivable account',
                    'account_id': receivable_acc_1.id,
                    'currency_id': self.currency_2.id,
                    'debit': 500.0,
                    'credit': 0.0,
                    'amount_currency': 1500.0,
                }),
                (0, None, {
                    'name': 'test line 2 - another receivable account',
                    'account_id': receivable_acc_2.id,
                    'currency_id': self.currency_2.id,
                    'debit': 500.0,
                    'credit': 0.0,
                    'amount_currency': 1500.0,
                }),
                (0, None, {
                    'name': 'test line 3 - payment transfer account',
                    'account_id': payment_account.id,
                    'currency_id': self.currency_2.id,
                    'debit': 30.0,
                    'credit': 0.0,
                    'amount_currency': 90.0,
                }),
            ]
        })
        test_move.action_post()

        test_line_1 = test_move.line_ids.filtered(lambda line: line.account_id == receivable_acc_1)
        test_line_2 = test_move.line_ids.filtered(lambda line: line.account_id == receivable_acc_2)
        test_line_3 = test_move.line_ids.filtered(lambda line: line.account_id == payment_account)
        self.statement_line.reconcile([
            # test line 1
            # Will reconcile 300.0 in balance, 600.0 in amount_currency.
            {'id': test_line_1.id, 'balance': -600.0},
            # test line 2
            # Will reconcile 250.0 in balance, 500.0 in amount_currency.
            {'id': test_line_2.id, 'balance': -500.0},
            # test line 3
            # Will reconcile 30.0 in balance, 90.0 in amount_currency.
            {'id': test_line_3.id},
            # test line 4
            # Will reconcile 50.0 in balance, 100.0 in amount_currency.
            {'name': 'whatever', 'account_id': random_acc_1.id, 'balance': -100.0},
        ])

        self.assertBankStatementLine(self.statement_line, {
                **self.expected_st_line,
                'is_reconciled': True,
            }, [
            {
                'name': '%s: Open Balance' % self.statement_line.payment_ref,
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': receivable_acc_1.id,  # This account is retrieved on the partner.
                'debit': 0.0,
                'credit': 605.0,
                'amount_currency': -1210.0,
                'amount_residual': -605.0,
                'amount_residual_currency': -1210.0,
            },
            {
                'name': test_line_1.name,
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': receivable_acc_1.id,
                'debit': 0.0,
                'credit': 300.0,
                'amount_currency': -600.0,
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            },
            {
                'name': test_line_2.name,
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': receivable_acc_2.id,
                'debit': 0.0,
                'credit': 250.0,
                'amount_currency': -500.0,
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            },
            {
                'name': 'whatever',
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': random_acc_1.id,
                'debit': 0.0,
                'credit': 50.0,
                'amount_currency': -100.0,
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            },
            {
                'name': test_line_3.name,
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': test_line_3.account_id.id,
                'debit': 0.0,
                'credit': 45.0,
                'amount_currency': -90.0,
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            },
            {
                **self.expected_bank_line,
                'amount_residual': 1250.0,
                'amount_residual_currency': 2500.0,
            },
        ])

        # Undo the reconciliation to return to the initial state.
        self.statement_line.button_undo_reconciliation()
        self.assertBankStatementLine(self.statement_line, self.expected_st_line, [self.expected_counterpart_line, self.expected_bank_line])

        # Modify the counterpart line with to_check enabled.
        self.statement_line.reconcile([
            {'name': 'whatever', 'account_id': random_acc_1.id, 'balance': -100.0},
        ], to_check=True)

        self.assertBankStatementLine(self.statement_line, {
                **self.expected_st_line,
                'is_reconciled': True,
            }, [
            {
                'name': '%s: Open Balance' % self.statement_line.payment_ref,
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': receivable_acc_1.id,  # This account is retrieved on the partner.
                'debit': 0.0,
                'credit': 1200.0,
                'amount_currency': -2400.0,
                'amount_residual': -1200.0,
                'amount_residual_currency': -2400.0,
            },
            {
                'name': 'whatever',
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': random_acc_1.id,
                'debit': 0.0,
                'credit': 50.0,
                'amount_currency': -100.0,
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            },
            {
                **self.expected_bank_line,
                'amount_residual': 1250.0,
                'amount_residual_currency': 2500.0,
            },
        ])

        # Modify the counterpart line. Should be allowed by the to_check enabled.
        self.statement_line.reconcile([
            {'name': 'whatever again', 'account_id': random_acc_2.id, 'balance': -500.0},
        ])

        self.assertBankStatementLine(self.statement_line, {
                **self.expected_st_line,
                'is_reconciled': True,
            }, [
            {
                'name': '%s: Open Balance' % self.statement_line.payment_ref,
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': receivable_acc_1.id,  # This account is retrieved on the partner.
                'debit': 0.0,
                'credit': 1000.0,
                'amount_currency': -2000.0,
                'amount_residual': -1000.0,
                'amount_residual_currency': -2000.0,
            },
            {
                'name': 'whatever again',
                'partner_id': self.statement_line.partner_id.id,
                'currency_id': self.currency_2.id,
                'account_id': random_acc_2.id,
                'debit': 0.0,
                'credit': 250.0,
                'amount_currency': -500.0,
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            },
            {
                **self.expected_bank_line,
                'amount_residual': 1250.0,
                'amount_residual_currency': 2500.0,
            },
        ])

        # The statement line is no longer in the 'to_check' mode.
        # Reconciling again should raise an error.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.statement_line.reconcile([
                {'name': 'whatever', 'account_id': random_acc_1.id, 'balance': -100.0},
            ])

    def test_conversion_rate_rounding_issue(self):
        ''' Ensure the reconciliation is well handling the rounding issue due to multiple currency conversion rates.

        In this test, the resulting journal entry after reconciliation is:
        {'amount_currency': 7541.66,    'debit': 6446.97,   'credit': 0.0}
        {'amount_currency': 226.04,     'debit': 193.22,    'credit': 0.0}
        {'amount_currency': -7767.70,   'debit': 0.0,       'credit': 6640.19}
        ... but 226.04 / 1.1698 = 193.23. In this situation, 0.01 has been removed from this write-off line in order to
        avoid an unecessary open-balance line being an exchange difference issue.
        '''
        self.bank_journal_2.currency_id = self.currency_2
        self.currency_data['rates'][-1].rate = 1.1698

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2017-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'amount': 7541.66,
                }),
            ],
        })
        statement.button_post()
        statement_line = statement.line_ids

        payment = self.env['account.payment'].create({
            'amount': 7767.70,
            'date': '2019-01-01',
            'currency_id': self.currency_2.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })
        payment.action_post()
        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
        self.assertRecordValues(liquidity_lines, [{'amount_currency': 7767.70}])

        statement_line.reconcile([
            {'id': liquidity_lines.id},
            {'balance': 226.04, 'account_id': self.company_data['default_account_revenue'].id, 'name': "write-off"},
        ])

        self.assertRecordValues(statement_line.line_ids, [
            {'amount_currency': 7541.66,    'debit': 6446.97,   'credit': 0.0},
            {'amount_currency': 226.04,     'debit': 193.22,    'credit': 0.0},
            {'amount_currency': -7767.70,   'debit': 0.0,       'credit': 6640.19},
        ])

    def test_zero_amount_statement_line(self):
        ''' Ensure the statement line is directly marked as reconciled when having an amount of zero. '''
        self.company_data['company'].account_journal_suspense_account_id.reconcile = False

        statement = self.env['account.bank.statement'].with_context(skip_check_amounts_currencies=True).create({
            'name': 'test_statement',
            'date': '2017-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': "Happy new year",
                    'amount': 0.0,
                }),
            ],
        })
        statement_line = statement.line_ids

        self.assertRecordValues(statement_line, [{'is_reconciled': True, 'amount_residual': 0.0}])

    def test_bank_statement_line_analytic(self):
        ''' Ensure the analytic lines are generated during the reconciliation. '''
        analytic_account = self.env['account.analytic.account'].create({'name': 'analytic_account'})

        statement = self.env['account.bank.statement'].with_context(skip_check_amounts_currencies=True).create({
            'name': 'test_statement',
            'date': '2017-01-01',
            'journal_id': self.bank_journal_2.id,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': "line",
                    'amount': 100.0,
                }),
            ],
        })
        statement_line = statement.line_ids

        statement_line.reconcile([{
            'balance': -100.0,
            'account_id': self.company_data['default_account_revenue'].id,
            'name': "write-off",
            'analytic_account_id': analytic_account.id,
        }])

        # Check the analytic account is there.
        self.assertRecordValues(statement_line.line_ids.sorted('balance'), [
            {'balance': -100.0, 'analytic_account_id': analytic_account.id},
            {'balance': 100.0, 'analytic_account_id': False},
        ])

        # Check the analytic lines.
        self.assertRecordValues(statement_line.line_ids.analytic_line_ids, [
            {'amount': 100.0, 'account_id': analytic_account.id},
        ])

    def test_reconciliation_line_with_no_partner(self):
        """
        Ensure that entry lines and statement line have no partner when reconciling
        lines without partner with others with partner
        """
        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_1.id,
            'line_ids': [
                (0, 0, {
                    'date': '2022-01-01',
                    'payment_ref': "Happy new year",
                    'amount': 200.0,
                }),
            ],
        })
        statement.button_post()

        partner = self.env['res.partner'].create({'name': 'test'})

        receivable_account = self.company_data['default_account_receivable']
        outstanding_account = self.env['account.account'].search([('code', '=', '101402'), ('company_id', '=', self.env.company.id)])

        payments = self.env['account.payment'].create([
            {
                'name': 'Payment without partner',
                'date': fields.Date.from_string('2022-01-01'),
                'is_internal_transfer': False,
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'destination_account_id': receivable_account.id,
                'journal_id': self.bank_journal_1.id,
            },
            {
                'name': 'Payment with partner',
                'date': fields.Date.from_string('2022-01-01'),
                'is_internal_transfer': False,
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'destination_account_id': receivable_account.id,
                'journal_id': self.bank_journal_1.id,
            },
        ])
        payments.action_post()

        statement_line = statement.line_ids

        statement_line.reconcile([
            {'id': payments[0].move_id.line_ids.filtered(lambda line: line.account_id == outstanding_account).id},
            {'id': payments[1].move_id.line_ids.filtered(lambda line: line.account_id == outstanding_account).id},
        ])

        self.assertRecordValues(
            statement.line_ids.move_id.line_ids,
            [
                {
                    'debit': 200.0,
                    'credit': 0.0,
                    'partner_id': False,
                    'account_id': self.bank_journal_1.default_account_id.id
                },
                {
                    'debit': 0.0,
                    'credit': 100.0,
                    'partner_id': False,
                    'account_id': outstanding_account.id
                },
                {
                    'debit': 0.0,
                    'credit': 100.0,
                    'partner_id': partner.id,
                    'account_id': outstanding_account.id
                },
            ])

        self.assertRecordValues(statement.line_ids, [{
            'partner_id': False,
        }])
