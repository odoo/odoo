# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.exceptions import ValidationError, UserError
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestAccountBankStatementLine(AccountTestInvoicingCommon):

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

        cls.statement = cls.env['account.bank.statement'].create({
            'name': 'test_statement',
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': cls.partner_a.id,
                    'foreign_currency_id': cls.currency_2.id,
                    'journal_id': cls.bank_journal_1.id,
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
            'currency_id': cls.currency_1.id,
            'account_id': cls.statement.journal_id.default_account_id.id,
            'debit': 1250.0,
            'credit': 0.0,
            'amount_currency': 1250.0,
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

    def assertBankStatementLine(self, statement_line, expected_statement_line_vals, expected_move_line_vals):
        self.assertRecordValues(statement_line, [expected_statement_line_vals])
        self.assertRecordValues(statement_line.line_ids.sorted('balance'), expected_move_line_vals)

    def create_bank_transaction(self, amount, date, amount_currency=None, currency=None, statement=None,
                                partner=None, journal=None, sequence=0):
        values = {
            'payment_ref': str(amount),
            'amount': amount,
            'date': date,
            'partner_id': partner and partner.id,
            'sequence': sequence,
        }
        if amount_currency:
            values['amount_currency'] = amount_currency
            values['foreign_currency_id'] = currency.id
        if statement and journal and statement.journal_id != journal:
            raise (ValidationError("The statement and the journal are contradictory"))
        if statement:
            values['journal_id'] = statement.journal_id.id
            values['statement_id'] = statement.id
        if journal:
            values['journal_id'] = journal.id
        if not values.get('journal_id'):
            values['journal_id'] = (self.company_data_2['default_journal_bank']
                                    if self.env.company == self.company_data_2['company']
                                    else self.company_data['default_journal_bank']
                                    ).id
        return self.env['account.bank.statement.line'].create(values)

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

        statement_line = self.env['account.bank.statement.line'].create({
            'date': '2019-01-01',
            'journal_id': journal.id,
            'payment_ref': 'line_1',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': foreign_currency and foreign_currency.id,
            'amount': amount,
            'amount_currency': amount_currency,
        })

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
            # pylint: disable=bad-whitespace
            80.0,               120.0,
            self.currency_2,    self.currency_3,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -120.0,      'currency_id': self.currency_3.id},
        )

    def test_edition_journal_curr_2_statement_curr_1(self):
        self._test_edition_customer_and_supplier_flows(
            # pylint: disable=bad-whitespace
            120.0,              80.0,
            self.currency_2,    self.currency_1,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 120.0,       'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_edition_journal_curr_1_statement_curr_2(self):
        self._test_edition_customer_and_supplier_flows(
            # pylint: disable=bad-whitespace
            80.0,               120.0,
            self.currency_1,    self.currency_2,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_1.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -120.0,      'currency_id': self.currency_2.id},
        )

    def test_edition_journal_curr_2_statement_false(self):
        self._test_edition_customer_and_supplier_flows(
            # pylint: disable=bad-whitespace
            80.0,               0.0,
            self.currency_2,    False,
            {'debit': 40.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 40.0,     'amount_currency': -80.0,       'currency_id': self.currency_2.id},
        )

    def test_edition_journal_curr_1_statement_false(self):
        self._test_edition_customer_and_supplier_flows(
            # pylint: disable=bad-whitespace
            80.0,               0.0,
            self.currency_1,    False,
            {'debit': 80.0,     'credit': 0.0,      'amount_currency': 80.0,        'currency_id': self.currency_1.id},
            {'debit': 0.0,      'credit': 80.0,     'amount_currency': -80.0,       'currency_id': self.currency_1.id},
        )

    def test_zero_amount_journal_curr_1_statement_curr_2(self):
        self.bank_journal_2.currency_id = self.currency_1

        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.bank_journal_2.id,
            'date': '2019-01-01',
            'payment_ref': 'line_1',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': self.currency_2.id,
            'amount': 0.0,
            'amount_currency': 10.0,
        })

        self.assertRecordValues(statement_line.move_id.line_ids, [
            # pylint: disable=bad-whitespace
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,         'currency_id': self.currency_1.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -10.0,       'currency_id': self.currency_2.id},
        ])

    def test_zero_amount_journal_curr_2_statement_curr_1(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.bank_journal_2.id,
            'date': '2019-01-01',
            'payment_ref': 'line_1',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': self.currency_1.id,
            'amount': 0.0,
            'amount_currency': 10.0,
        })

        self.assertRecordValues(statement_line.move_id.line_ids, [
            # pylint: disable=bad-whitespace
            {'debit': 10.0,     'credit': 0.0,      'amount_currency': 0.0,         'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 10.0,     'amount_currency': -10.0,       'currency_id': self.currency_1.id},
        ])

    def test_zero_amount_journal_curr_2_statement_curr_3(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.bank_journal_2.id,
            'date': '2019-01-01',
            'payment_ref': 'line_1',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': self.currency_3.id,
            'amount': 0.0,
            'amount_currency': 10.0,
        })

        self.assertRecordValues(statement_line.move_id.line_ids, [
            # pylint: disable=bad-whitespace
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,         'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -10.0,       'currency_id': self.currency_3.id},
        ])

    def test_constraints(self):
        def assertStatementLineConstraint(statement_line_vals):
            with self.assertRaises(Exception), self.cr.savepoint():
                self.env['account.bank.statement.line'].create(statement_line_vals)

        statement_line_vals = {
            'journal_id': self.bank_journal_2.id,
            'date': '2019-01-01',
            'payment_ref': 'line_1',
            'partner_id': self.partner_a.id,
            'foreign_currency_id': False,
            'amount': 10.0,
            'amount_currency': 0.0,
        }

        # ==== Test constraints at creation ====

        # Can't have a stand alone amount in foreign currency without foreign currency set.
        assertStatementLineConstraint({
            **statement_line_vals,
            'amount_currency': 10.0,
        })

        # Can't have a foreign currency set without amount in foreign currency.
        assertStatementLineConstraint({
            **statement_line_vals,
            'foreign_currency_id': self.currency_2.id,
        })

        # ==== Test constraints at edition ====

        st_line = self.env['account.bank.statement.line'].create(statement_line_vals)

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

    def test_statement_line_move_onchange_1(self):
        ''' Test the consistency between the account.bank.statement.line and the generated account.move.lines
        using the form view emulator.
        '''

        # Check the initial state of the statement line.
        self.assertBankStatementLine(self.statement_line, self.expected_st_line,
                                     [self.expected_counterpart_line, self.expected_bank_line])

        # Inverse the amount + change them.
        self.statement_line.write({
            'amount': -2000.0,
            'amount_currency': -4000.0,
            'foreign_currency_id': self.currency_3.id,
        })

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
                'amount_currency': -2000.0,
                'currency_id': self.currency_1.id,
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
        self.statement_line.write({
            'payment_ref': 'line_1 (bis)',
            'partner_id': self.partner_b.id,
        })

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
                'amount_currency': -2000.0,
                'currency_id': self.currency_1.id,
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

    def test_prepare_counterpart_amounts_using_st_line_rate(self):

        def assertAppliedRate(
            journal_currency, foreign_currency, aml_currency,
            amount, amount_currency, aml_amount_currency, aml_balance,
            expected_amount_currency, expected_balance,
        ):
            journal = self.bank_journal_1.copy()
            journal.currency_id = journal_currency

            statement_line = self.env['account.bank.statement.line'].create({
                'journal_id': journal.id,
                'date': '2019-01-01',
                'payment_ref': 'test_prepare_counterpart_amounts_using_st_line_rate',
                'foreign_currency_id': foreign_currency.id if foreign_currency != journal_currency else None,
                'amount': amount,
                'amount_currency': amount_currency if foreign_currency != journal_currency else 0.0,
            })

            res = statement_line._prepare_counterpart_amounts_using_st_line_rate(aml_currency, -aml_balance,
                                                                                 -aml_amount_currency)
            self.assertAlmostEqual(res['amount_currency'], expected_amount_currency)
            self.assertAlmostEqual(res['balance'], expected_balance)

        for params in (
            (self.currency_2, self.currency_3, self.currency_3, 80.0, 120.0, 120.0, 20.0, -120.0, -40.0),
            (self.currency_2, self.currency_1, self.currency_2, 120.0, 80.0, 120.0, 40.0, -80.0, -80.0),
            (self.currency_2, self.currency_3, self.currency_2, 80.0, 120.0, 80.0, 26.67, -120.0, -40.0),
            (self.currency_2, self.currency_3, self.currency_4, 80.0, 120.0, 480.0, 40.0, -120.0, -40.0),
            (self.currency_1, self.currency_2, self.currency_2, 80.0, 120.0, 120.0, 40.0, -120.0, -80.0),
            (self.currency_1, self.currency_2, self.currency_3, 80.0, 120.0, 480.0, 80.0, -120.0, -80.0),
            (self.currency_2, self.currency_2, self.currency_2, 80.0, 80.0, 80.0, 26.67, -80.0, -40.0),
            (self.currency_2, self.currency_2, self.currency_3, 80.0, 80.0, 240.0, 40.0, -80.0, -40.0),
            (self.currency_1, self.currency_1, self.currency_3, 80.0, 80.0, 480.0, 80.0, -80.0, -80.0),
            (self.currency_2, self.currency_1, self.currency_1, 120.0, 80.0, 80.0, 80.0, -80.0, -80.0),
            (self.currency_2, self.currency_3, self.currency_1, 80.0, 120.0, 40.0, 40.0, -120.0, -40.0),
            (self.currency_1, self.currency_2, self.currency_1, 80.0, 120.0, 80.0, 80.0, -120.0, -80.0),
            (self.currency_2, self.currency_2, self.currency_1, 80.0, 80.0, 40.0, 40.0, -80.0, -40.0),
            (self.currency_1, self.currency_1, self.currency_1, 80.0, 80.0, 80.0, 80.0, -80.0, -80.0),
        ):
            with self.subTest(params=params):
                assertAppliedRate(*params)

    def test_zero_amount_statement_line(self):
        ''' Ensure the statement line is directly marked as reconciled when having an amount of zero. '''
        self.company_data['company'].account_journal_suspense_account_id.reconcile = False

        statement = self.env['account.bank.statement'].with_context(skip_check_amounts_currencies=True).create({
            'name': 'test_statement',
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': "Happy new year",
                    'amount': 0.0,
                    'journal_id': self.bank_journal_2.id,
                }),
            ],
        })
        statement_line = statement.line_ids

        self.assertRecordValues(statement_line, [{'is_reconciled': True, 'amount_residual': 0.0}])

    def test_statement_valid_complete_1(self):
        self.env.user.company_id = self.company_data_2['company']

        # create a valid and complete statement as the first lines (no statement before)
        line1 = self.create_bank_transaction(1, '2020-01-10')
        line2 = self.create_bank_transaction(2, '2020-01-11')
        statement1 = self.env['account.bank.statement'].create({
            'line_ids': [Command.set((line1 + line2).ids)],
            'balance_start': 0,
            'balance_end_real': 3,
        })
        self.assertRecordValues(statement1, [{
            'is_complete': True,
            'is_valid': True,
        }])
        # remove the first line, so not complete but it is still valid because there is no statement before
        line1.statement_id = False
        statement1.invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_complete': False,
            'is_valid': True,
        }])
        # create a new line in the statement to make it complete again. Starting value does not match the last line
        # but it is still valid because the previous line has no statement
        line3 = self.create_bank_transaction(1, '2020-01-12', statement=statement1)
        statement1.invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_complete': True,
            'is_valid': True,
        }])
        # add a statement to the first line, statement1 is still complete but not valid because balance start
        # does not match the previous statement
        statement2 = self.env['account.bank.statement'].create({
            'line_ids': [Command.set(line1.ids)],
            'balance_end_real': 1,
        })
        (statement1 + statement2).invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1 + statement2, [{
            'is_complete': True,
            'is_valid': False,
        }, {
            'is_complete': True,
            'is_valid': True,  # first statement
        }])
        # Fix the statement balance start, so the statement is not complete (end - start = 2, vs sum lines = 3)
        # but it is matched with the previous statements balance end
        statement1.balance_start = 1
        statement1.invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_complete': False,
            'is_valid': True,
        }])
        # change the prev statement so the end balance does not match the start balance of statement 1
        statement2.balance_end_real = 10
        statement2.flush_recordset(['balance_end_real'])
        statement1.invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_complete': False,
            'is_valid': False,
        }])
        # make the statement valid again
        statement1.balance_start = 10
        statement1.invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_complete': False,
            'is_valid': True,
        }])
        # and complete again by adding a new transaction to it
        line4 = self.create_bank_transaction(-10, '2020-01-13', statement=statement1)
        (statement1 + statement2).invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1 + statement2, [{
            'is_complete': True,
            'is_valid': True,
            'date': fields.Date.from_string('2020-01-13'),
        }, {
            'is_complete': False,
            'is_valid': True,
            'date': fields.Date.from_string('2020-01-10'),
        }])
        # check point
        self.assertRecordValues(line1 + line2 + line3 + line4, [
            {'date': fields.Date.from_string('2020-01-10'), 'statement_id': statement2.id},
            {'date': fields.Date.from_string('2020-01-11'), 'statement_id': statement1.id},
            {'date': fields.Date.from_string('2020-01-12'), 'statement_id': statement1.id},
            {'date': fields.Date.from_string('2020-01-13'), 'statement_id': statement1.id},
        ])

        # changing statement 2 balance makes statement 1 valid,
        # but making statement 1 the first statement should make it valid again
        statement2.balance_end_real = 100
        statement2.flush_recordset(['balance_end_real'])
        statement1.invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_valid': False,
        }])
        line1.statement_id = False
        line1.flush_model()
        statement2.flush_model()
        statement1.invalidate_model(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_valid': True,
        }])

        # having a gap in the statement shouldn't make it invalid
        line3.statement_id = False
        statement1.flush_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_valid': True,
        }])

        # Change the statement on one of the lines of statement 1
        statement3 = self.env['account.bank.statement'].create({
            'line_ids': [Command.set(line4.ids)],
            'balance_start': -5,
        })
        (statement1 + statement3).flush_recordset(['is_valid'])
        self.assertRecordValues(statement1 + statement3, [{
            'is_valid': True,
        }, {
            'is_valid': False,  # balance does not match with statement1
        }])

        # changing statement1 end_balance should change the validity of statement3
        statement1.balance_end_real = -5
        statement1.flush_recordset(['balance_end_real'])
        (statement1 + statement3).invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1 + statement3, [{
            'is_valid': True,
        }, {
            'is_valid': True,  # balance start matches previous end, despite the gap
        }])
        # check point
        self.assertRecordValues(line1 + line2 + line3 + line4, [
            {'date': fields.Date.from_string('2020-01-10'), 'statement_id': False},
            {'date': fields.Date.from_string('2020-01-11'), 'statement_id': statement1.id},
            {'date': fields.Date.from_string('2020-01-12'), 'statement_id': False},
            {'date': fields.Date.from_string('2020-01-13'), 'statement_id': statement3.id},
        ])
        self.assertRecordValues(statement1 + statement2 + statement3, [
            {'is_valid': True, 'balance_start': 10, 'balance_end_real': -5,
             'date': fields.Date.from_string('2020-01-11')},
            {'is_valid': True, 'balance_start': False, 'balance_end_real': 100, 'date': False},
            {'is_valid': True, 'balance_start': -5, 'balance_end_real': False,
             'date': fields.Date.from_string('2020-01-13')},
        ])

        # adding a statement to the first line should make statement1 invalid
        line1.statement_id = statement2
        statement2.flush_model()
        (statement1 + statement2).invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1 + statement2, [{'is_valid': False}, {'is_valid': True}])

        # moving statement2 the line between statement1 and statement3 should make statement1 valid again
        # and statement3 invalid
        statement2.line_ids = line3
        statement2.flush_model()
        (statement1 + statement2 + statement3).invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1 + statement2 + statement3, [
            {'is_valid': True}, {'is_valid': False}, {'is_valid': False},
        ])

    def test_statement_line_ordering(self):
        self.env.user.company_id = self.company_data_2['company']

        # the line numbers are chosen based on the order of the lines in the list view
        line7 = self.create_bank_transaction(7, '2020-01-10', sequence=1)
        line8 = self.create_bank_transaction(8, '2020-01-10', sequence=2)
        line2 = self.create_bank_transaction(2, '2020-01-13')
        line6 = self.create_bank_transaction(6, '2020-01-11')
        line5 = self.create_bank_transaction(5, '2020-01-12', sequence=3)
        line4 = self.create_bank_transaction(4, '2020-01-12', sequence=2)
        line1 = self.create_bank_transaction(1, '2020-01-13')
        line3 = self.create_bank_transaction(3, '2020-01-12', sequence=1)

        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': False},
                {'amount': 3, 'running_balance': 33, 'statement_id': False},
                {'amount': 4, 'running_balance': 30, 'statement_id': False},
                {'amount': 5, 'running_balance': 26, 'statement_id': False},
                {'amount': 6, 'running_balance': 21, 'statement_id': False},
                {'amount': 7, 'running_balance': 15, 'statement_id': False},
                {'amount': 8, 'running_balance': 8, 'statement_id': False},
            ],
        )

        # Same but with a subset of lines to ensure the balance is not only computed based on selected records.
        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([
                ('company_id', '=', self.env.company.id),
                ('amount', '>=', 3),
                ('amount', '<=', 6),
            ]),
            [
                {'amount': 3, 'running_balance': 33},
                {'amount': 4, 'running_balance': 30},
                {'amount': 5, 'running_balance': 26},
                {'amount': 6, 'running_balance': 21},
            ],
        )

        # Put line2 -> line4 inside a statement with a wrong balance_end_real.
        (line2 + line3 + line4).statement_id = statement1 = \
            self.env['account.bank.statement'].create({'balance_end_real': 9})
        self.assertRecordValues(statement1, [{
            'is_complete': True,
        }])

        statement1.invalidate_recordset(['is_valid'])
        statement1.balance_start = 26
        self.assertRecordValues(statement1, [{
            'is_complete': False,
        }])

        statement1.invalidate_recordset(['is_valid'])
        statement1.balance_end_real = 35
        self.assertRecordValues(statement1, [{
            'is_complete': True,
        }])
        # line3, line4 and line5 have the same date. Move line5 at the first place using the sequence.
        line5.sequence = -1
        statement1.invalidate_recordset(['is_valid'])
        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(statement1, [{
            'is_complete': True,
        }])

        statement1.balance_start = 21
        statement1.invalidate_recordset(['is_valid'])
        self.assertRecordValues(statement1, [{
            'is_complete': False,
        }])

        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': statement1.id},
                {'amount': 5, 'running_balance': 33, 'statement_id': False},
                {'amount': 3, 'running_balance': 28, 'statement_id': statement1.id},
                {'amount': 4, 'running_balance': 25, 'statement_id': statement1.id},
                {'amount': 6, 'running_balance': 21, 'statement_id': False},
                {'amount': 7, 'running_balance': 15, 'statement_id': False},
                {'amount': 8, 'running_balance': 8, 'statement_id': False},
            ],
        )

        line8.amount = 18

        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': statement1.id},
                {'amount': 5, 'running_balance': 33, 'statement_id': False},
                {'amount': 3, 'running_balance': 28, 'statement_id': statement1.id},
                {'amount': 4, 'running_balance': 25, 'statement_id': statement1.id},
                {'amount': 6, 'running_balance': 31, 'statement_id': False},
                {'amount': 7, 'running_balance': 25, 'statement_id': False},
                {'amount': 18, 'running_balance': 18, 'statement_id': False},
            ],
        )
        line5.amount = 15

        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 46, 'statement_id': False},
                {'amount': 2, 'running_balance': 45, 'statement_id': statement1.id},
                {'amount': 15, 'running_balance': 43, 'statement_id': False},
                {'amount': 3, 'running_balance': 28, 'statement_id': statement1.id},
                {'amount': 4, 'running_balance': 25, 'statement_id': statement1.id},
                {'amount': 6, 'running_balance': 31, 'statement_id': False},
                {'amount': 7, 'running_balance': 25, 'statement_id': False},
                {'amount': 18, 'running_balance': 18, 'statement_id': False},
            ],
        )

        line7.unlink()

        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 46, 'statement_id': False},
                {'amount': 2, 'running_balance': 45, 'statement_id': statement1.id},
                {'amount': 15, 'running_balance': 43, 'statement_id': False},
                {'amount': 3, 'running_balance': 28, 'statement_id': statement1.id},
                {'amount': 4, 'running_balance': 25, 'statement_id': statement1.id},
                {'amount': 6, 'running_balance': 24, 'statement_id': False},
                {'amount': 18, 'running_balance': 18, 'statement_id': False},
            ],
        )
        line1.move_id.button_cancel()
        line6.move_id.button_cancel()
        line6.move_id.button_draft()
        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 45, 'statement_id': False},
                {'amount': 2, 'running_balance': 45, 'statement_id': statement1.id},
                {'amount': 15, 'running_balance': 43, 'statement_id': False},
                {'amount': 3, 'running_balance': 28, 'statement_id': statement1.id},
                {'amount': 4, 'running_balance': 25, 'statement_id': statement1.id},
                {'amount': 6, 'running_balance': 18, 'statement_id': False},
                {'amount': 18, 'running_balance': 18, 'statement_id': False},
            ],
        )

        # remove the anchor point
        statement1.line_ids = False
        self.env['account.bank.statement.line'].invalidate_model(fnames=['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 42, 'statement_id': False},
                {'amount': 2, 'running_balance': 42, 'statement_id': False},
                {'amount': 15, 'running_balance': 40, 'statement_id': False},
                {'amount': 3, 'running_balance': 25, 'statement_id': False},
                {'amount': 4, 'running_balance': 22, 'statement_id': False},
                {'amount': 6, 'running_balance': 18, 'statement_id': False},
                {'amount': 18, 'running_balance': 18, 'statement_id': False},
            ],
        )

    def test_statement_split(self):
        self.env.user.company_id = self.company_data_2['company']

        # the line numbers are chosen based on the order of the lines in the list view
        line7 = self.create_bank_transaction(7, '2020-01-10', sequence=1)
        line8 = self.create_bank_transaction(8, '2020-01-10', sequence=2)
        line2 = self.create_bank_transaction(2, '2020-01-13')
        line6 = self.create_bank_transaction(6, '2020-01-11')
        _line5 = self.create_bank_transaction(5, '2020-01-12', sequence=3)
        line4 = self.create_bank_transaction(4, '2020-01-12', sequence=2)
        line1 = self.create_bank_transaction(1, '2020-01-13')
        line3 = self.create_bank_transaction(3, '2020-01-12', sequence=1)

        # Split the last 2 lines by splitting on the line before last.
        statement1 = self.env['account.bank.statement'].with_context({'split_line_id': line7.id}).create({})
        self.assertRecordValues(statement1, [{
            'is_complete': True,
            'balance_end_real': 15,
            'balance_end': 15,
            'balance_start': 0,
        }])
        self.assertRecordValues(line7 + line8, [
            {'amount': 7, 'statement_id': statement1.id},
            {'amount': 8, 'statement_id': statement1.id},
        ])

        # Split on a line adjutant to another statement
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement2 = self.env['account.bank.statement'].with_context({'split_line_id': line6.id}).create({})
        self.assertRecordValues(statement1, [{
            'is_complete': True,
            'balance_end_real': 15,
            'balance_start': 0,
        }])
        self.assertRecordValues(statement2, [{
            'is_complete': True,
            'balance_end_real': 21,
            'balance_start': 15,
        }])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': False},
                {'amount': 3, 'running_balance': 33, 'statement_id': False},
                {'amount': 4, 'running_balance': 30, 'statement_id': False},
                {'amount': 5, 'running_balance': 26, 'statement_id': False},
                {'amount': 6, 'running_balance': 21, 'statement_id': statement2.id},
                {'amount': 7, 'running_balance': 15, 'statement_id': statement1.id},
                {'amount': 8, 'running_balance': 8,  'statement_id': statement1.id},
            ],
        )

        # Split on a line with a gap to another statement
        statement1.unlink()
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement3 = self.env['account.bank.statement'].with_context({'split_line_id': line3.id}).create({})
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': False},
                {'amount': 3, 'running_balance': 33, 'statement_id': statement3.id},
                {'amount': 4, 'running_balance': 30, 'statement_id': statement3.id},
                {'amount': 5, 'running_balance': 26, 'statement_id': statement3.id},
                {'amount': 6, 'running_balance': 21, 'statement_id': statement2.id},
                {'amount': 7, 'running_balance': 15, 'statement_id': False},
                {'amount': 8, 'running_balance': 8,  'statement_id': False},
            ],
        )
        # Split on a line with a single line statement
        statement4 = self.env['account.bank.statement'].with_context({'split_line_id': line6.id}).create({})
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': False},
                {'amount': 3, 'running_balance': 33, 'statement_id': statement3.id},
                {'amount': 4, 'running_balance': 30, 'statement_id': statement3.id},
                {'amount': 5, 'running_balance': 26, 'statement_id': statement3.id},
                {'amount': 6, 'running_balance': 21, 'statement_id': statement4.id},
                {'amount': 7, 'running_balance': 15, 'statement_id': statement4.id},
                {'amount': 8, 'running_balance': 8,  'statement_id': statement4.id},
            ],
        )
        # check double split on a single line
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement5 = self.env['account.bank.statement'].with_context({'split_line_id': line2.id}).create({})
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': statement5.id},
                {'amount': 3, 'running_balance': 33, 'statement_id': statement3.id},
                {'amount': 4, 'running_balance': 30, 'statement_id': statement3.id},
                {'amount': 5, 'running_balance': 26, 'statement_id': statement3.id},
                {'amount': 6, 'running_balance': 21, 'statement_id': statement4.id},
                {'amount': 7, 'running_balance': 15, 'statement_id': statement4.id},
                {'amount': 8, 'running_balance': 8,  'statement_id': statement4.id},
            ],
        )
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement6 = self.env['account.bank.statement'].with_context({'split_line_id': line2.id}).create({})
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': statement6.id},
                {'amount': 3, 'running_balance': 33, 'statement_id': statement3.id},
                {'amount': 4, 'running_balance': 30, 'statement_id': statement3.id},
                {'amount': 5, 'running_balance': 26, 'statement_id': statement3.id},
                {'amount': 6, 'running_balance': 21, 'statement_id': statement4.id},
                {'amount': 7, 'running_balance': 15, 'statement_id': statement4.id},
                {'amount': 8, 'running_balance': 8,  'statement_id': statement4.id},
            ],
        )

        # Split in the middle of a statement
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement7 = self.env['account.bank.statement'].with_context({'split_line_id': line4.id}).create({})
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'running_balance': 36, 'statement_id': False},
                {'amount': 2, 'running_balance': 35, 'statement_id': statement6.id},
                {'amount': 3, 'running_balance': 33, 'statement_id': statement3.id},
                {'amount': 4, 'running_balance': 30, 'statement_id': statement7.id},
                {'amount': 5, 'running_balance': 26, 'statement_id': statement7.id},
                {'amount': 6, 'running_balance': 21, 'statement_id': statement4.id},
                {'amount': 7, 'running_balance': 15, 'statement_id': statement4.id},
                {'amount': 8, 'running_balance': 8,  'statement_id': statement4.id},
            ],
        )
        self.assertRecordValues(statement3 + statement7, [
            {'balance_end_real': 33, 'balance_start': 30, 'is_complete': True, 'is_valid': True, },
            {'balance_end_real': 30, 'balance_start': 21, 'is_complete': True, 'is_valid': True, },
        ])

        # split at start of another statement
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement8 = self.env['account.bank.statement'].with_context({'split_line_id': line6.id}).create({})
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'statement_id': False},
                {'amount': 2, 'statement_id': statement6.id},
                {'amount': 3, 'statement_id': statement3.id},
                {'amount': 4, 'statement_id': statement7.id},
                {'amount': 5, 'statement_id': statement7.id},
                {'amount': 6, 'statement_id': statement8.id},
                {'amount': 7, 'statement_id': statement8.id},
                {'amount': 8, 'statement_id': statement8.id},
            ],
        )

        # split at end of another statement
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement9 = self.env['account.bank.statement'].with_context({'split_line_id': line8.id}).create({})
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'statement_id': False},
                {'amount': 2, 'statement_id': statement6.id},
                {'amount': 3, 'statement_id': statement3.id},
                {'amount': 4, 'statement_id': statement7.id},
                {'amount': 5, 'statement_id': statement7.id},
                {'amount': 6, 'statement_id': statement8.id},
                {'amount': 7, 'statement_id': statement8.id},
                {'amount': 8, 'statement_id': statement9.id},
            ],
        )
        self.assertRecordValues(statement8 + statement9, [
            {'balance_end_real': 21, 'balance_start': 8, 'is_complete': True, 'is_valid': True, },
            {'balance_end_real': 8, 'balance_start': 0, 'is_complete': True, 'is_valid': True, },
        ])

        # split at most recent line
        self.env['account.bank.statement.line'].invalidate_model(['running_balance'])
        statement10 = self.env['account.bank.statement'].with_context({'split_line_id': line1.id}).create({})
        self.assertRecordValues(
            self.env['account.bank.statement.line'].search([('company_id', '=', self.env.company.id)]),
            [
                # pylint: disable=C0326
                {'amount': 1, 'statement_id': statement10.id},
                {'amount': 2, 'statement_id': statement6.id},
                {'amount': 3, 'statement_id': statement3.id},
                {'amount': 4, 'statement_id': statement7.id},
                {'amount': 5, 'statement_id': statement7.id},
                {'amount': 6, 'statement_id': statement8.id},
                {'amount': 7, 'statement_id': statement8.id},
                {'amount': 8, 'statement_id': statement9.id},
            ],
        )

        all_statements = self.env['account.bank.statement'].search([
            ('line_ids', '!=', False),
            ('company_id', '=', self.env.company.id),
        ])
        all_statements.invalidate_recordset(['is_valid'])
        self.assertEqual(len(all_statements), 6)
        self.assertEqual(all_statements.mapped('is_valid'), [True] * len(all_statements))
        self.assertEqual(all_statements.mapped('is_complete'), [True] * len(all_statements))

    def test_statement_with_canceled_lines(self):
        line1 = self.create_bank_transaction(1, '2020-01-10')
        line2 = self.create_bank_transaction(2, '2020-01-11')
        statement1 = self.env['account.bank.statement'].create({
            'line_ids': [Command.set((line1 + line2).ids)],
            'balance_start': 0,
            'balance_end_real': 3,
        })
        self.assertRecordValues(statement1, [{
            'is_complete': True,
            'date': fields.Date.from_string(line2.date),
        }])
        # test canceling a line
        line2.move_id.button_cancel()
        self.assertRecordValues(statement1, [{
            'is_complete': False,
            'balance_end': 1,
            'date': fields.Date.from_string(line1.date),
        }])
        # test add a line with same amount as a canceled line makes statement complete again
        line3 = self.create_bank_transaction(2, '2020-01-12', statement=statement1)
        self.assertRecordValues(statement1, [{
            'is_complete': True,
            'balance_end': 3,
            'date': fields.Date.from_string(line3.date),
        }])
        # test adding a draft line to a statement, nothing should be changed in statement
        line4 = self.create_bank_transaction(4, '2020-01-13')
        line4.move_id.button_cancel()
        line4.move_id.button_draft()
        statement1.line_ids |= line4
        self.assertRecordValues(statement1, [{
            'is_complete': True,
            'balance_end': 3,
            'date': fields.Date.from_string(line3.date),
        }])
        # test split with canceled/draft lines
        statement2 = self.env['account.bank.statement'].with_context({'split_line_id': line2.id}).create({})
        self.assertRecordValues(statement1 + statement2, [{
            'is_complete': True,
            'balance_end': 3,
            'balance_start': 1,
            'line_ids': [line4.id, line3.id],
        }, {
            'is_complete': True,
            'balance_start': 0,
            'balance_end': 1,
            'line_ids': [line1.id, line2.id],
        }])

        # test cancel/draft all statement lines
        # line 4 is draft, and we cancel line 3 so the statement should be empty
        line3.move_id.button_cancel()
        self.assertRecordValues(statement1, [{
            'is_complete': False,
            'balance_start': 1,
            'balance_end': 1,
        }])
        # create a statement line with already canceled lines
        statement3 = self.env['account.bank.statement'].create({
            'line_ids': [Command.set((line3 + line4).ids)],
        })
        self.assertRecordValues(statement1 + statement3, [{
            'is_complete': False,
            'balance_start': 1,
            'balance_end': 1,
        }, {
            'is_complete': False,
            'balance_start': 0,  # no value is given for balance start and it is not a split
            'balance_end': 0,
        }])

    def test_create_statement_line_with_inconsistent_currencies(self):
        statement_line = self.env['account.bank.statement.line'].create({
            'date': '2019-01-01',
            'journal_id': self.bank_journal_1.id,
            'payment_ref': "Happy new year",
            'amount': 200.0,
            'amount_currency': 200.0,
            'foreign_currency_id': self.env.company.currency_id.id,
        })

        self.assertRecordValues(statement_line, [{
            'currency_id': self.env.company.currency_id.id,
            'foreign_currency_id': False,
            'amount': 200.0,
            'amount_currency': 0.0,
        }])
