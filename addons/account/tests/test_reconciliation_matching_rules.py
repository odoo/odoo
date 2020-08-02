# -*- coding: utf-8 -*-
from odoo import fields
from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestReconciliationMatchingRules(AccountTestInvoicingCommon):

    @classmethod
    def _create_invoice_line(cls, amount, partner, type):
        ''' Create an invoice on the fly.'''
        invoice_form = Form(cls.env['account.move'].with_context(default_type=type))
        invoice_form.invoice_date = fields.Date.from_string('2019-09-01')
        invoice_form.partner_id = partner
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'xxxx'
            invoice_line_form.quantity = 1
            invoice_line_form.price_unit = amount
            invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()
        invoice.post()
        lines = invoice.line_ids
        return lines.filtered(lambda l: l.account_id.user_type_id.type in ('receivable', 'payable'))

    def _check_statement_matching(self, rules, expected_values, statements=None):
        if statements is None:
            statements = self.bank_st + self.cash_st
        statement_lines = statements.mapped('line_ids').sorted()
        matching_values = rules._apply_rules(statement_lines)
        for st_line_id, values in matching_values.items():
            values.pop('reconciled_lines', None)
            self.assertDictEqual(values, expected_values[st_line_id])

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        
        cls.account_pay = cls.company_data['default_account_payable']
        cls.account_rcv = cls.company_data['default_account_receivable']
        cls.account_bnk = cls.company_data['default_journal_bank'].default_debit_account_id
        cls.account_cash = cls.company_data['default_journal_cash'].default_debit_account_id

        cls.partner_1 = cls.env['res.partner'].create({'name': 'partner_1'})
        cls.partner_2 = cls.env['res.partner'].create({'name': 'partner_2'})

        # Generate invoice starting at a fixed sequence to avoid matching multiple lines depending the current date.
        cls.company_data['default_journal_sale'].sequence_id._get_current_sequence(sequence_date='2019-01-01').number_next = 5

        cls.invoice_line_1 = cls._create_invoice_line(100, cls.partner_1, 'out_invoice')
        cls.invoice_line_2 = cls._create_invoice_line(200, cls.partner_1, 'out_invoice')
        cls.invoice_line_3 = cls._create_invoice_line(300, cls.partner_1, 'in_refund')
        cls.invoice_line_4 = cls._create_invoice_line(1000, cls.partner_2, 'in_invoice')

        cls.rule_0 = cls.env['account.reconcile.model'].search([('company_id', '=', cls.company_data['company'].id), ('rule_type', '=', 'invoice_matching')])
        cls.rule_1 = cls.rule_0.copy()
        cls.rule_1.account_id = cls.company_data['default_account_revenue']
        cls.rule_1.match_partner = True
        cls.rule_1.match_partner_ids |= cls.partner_1 + cls.partner_2
        cls.rule_2 = cls.env['account.reconcile.model'].create({
            'name': 'write-off model',
            'rule_type': 'writeoff_suggestion',
            'match_partner': True,
            'match_partner_ids': [],
            'account_id': cls.company_data['default_account_revenue'].id,
        })

        cls.bank_st = cls.env['account.bank.statement'].create({
            'name': 'test bank journal', 'journal_id': cls.company_data['default_journal_bank'].id,
        })
        cls.bank_line_1 = cls.env['account.bank.statement.line'].create({
            'statement_id': cls.bank_st.id,
            'name': 'invoice 2019-0005',
            'partner_id': cls.partner_1.id,
            'amount': 100,
            'sequence': 1,
        })
        cls.bank_line_2 = cls.env['account.bank.statement.line'].create({
            'statement_id': cls.bank_st.id,
            'name': 'xxxxx',
            'partner_id': cls.partner_1.id,
            'amount': 600,
            'sequence': 2,
        })

        cls.cash_st = cls.env['account.bank.statement'].create({
            'name': 'test cash journal', 'journal_id': cls.company_data['default_journal_cash'].id,
        })
        cls.cash_line_1 = cls.env['account.bank.statement.line'].create({
            'statement_id': cls.cash_st.id,
            'name': 'yyyyy',
            'partner_id': cls.partner_2.id,
            'amount': -1000,
            'sequence': 1,
        })

        cls.tax21 = cls.env['account.tax'].create({
            'name': '21%',
            'type_tax_use': 'purchase',
            'amount': 21,
        })

    def test_matching_fields(self):
        ''' Test all fields used to restrict the rules's applicability.'''

        # Check without restriction.
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })

        # Check match_journal_ids.
        self.rule_1.match_journal_ids |= self.cash_st.journal_id
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_journal_ids |= self.bank_st.journal_id + self.cash_st.journal_id

        # Check match_nature.
        self.rule_1.match_nature = 'amount_received'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': []},
        })
        self.rule_1.match_nature = 'amount_paid'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_nature = 'both'

        # Check match_amount.
        self.rule_1.match_amount = 'lower'
        self.rule_1.match_amount_max = 150
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': []},
        })
        self.rule_1.match_amount = 'greater'
        self.rule_1.match_amount_min = 200
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_1.id,
                self.invoice_line_2.id,
                self.invoice_line_3.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_amount = 'between'
        self.rule_1.match_amount_min = 200
        self.rule_1.match_amount_max = 800
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_1.id,
                self.invoice_line_2.id,
                self.invoice_line_3.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': []},
        })
        self.rule_1.match_amount = False

        # Check match_label.
        self.rule_1.match_label = 'contains'
        self.rule_1.match_label_param = 'yyyyy'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_label = 'not_contains'
        self.rule_1.match_label_param = 'xxxxx'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_label = 'match_regex'
        self.rule_1.match_label_param = 'xxxxx|yyyyy'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_1.id,
                self.invoice_line_2.id,
                self.invoice_line_3.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_label = False

        # Check match_total_amount: line amount >= total residual amount.
        self.rule_1.match_total_amount_param = 90.0
        self.bank_line_1.amount += 5
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'status': 'write_off'},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_total_amount_param = 100.0
        self.bank_line_1.amount -= 5

        # Check match_total_amount: line amount <= total residual amount.
        self.rule_1.match_total_amount_param = 90.0
        self.bank_line_1.amount -= 5
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'status': 'write_off'},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_total_amount_param = 100.0
        self.bank_line_1.amount += 5

        # Check match_partner_category_ids.
        test_category = self.env.ref('base.res_partner_category_8')
        self.partner_2.category_id = test_category
        self.rule_1.match_partner_category_ids |= test_category
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })
        self.rule_1.match_partner_category_ids = False

    def test_mixin_rules(self):
        ''' Test usage of rules together.'''

        # rule_1 is used before rule_2.
        self.rule_1.sequence = 1
        self.rule_2.sequence = 2

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })

        # rule_2 is used before rule_1.
        self.rule_1.sequence = 2
        self.rule_2.sequence = 1

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off'},
            self.bank_line_2.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off'},
            self.cash_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off'},
        })

        # rule_2 is used before rule_1 but only on partner_1.
        self.rule_2.match_partner_ids |= self.partner_1

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off'},
            self.bank_line_2.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off'},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1},
        })

    def test_auto_reconcile(self):
        ''' Test auto reconciliation.'''

        self.rule_1.sequence = 2
        self.rule_1.auto_reconcile = True
        self.rule_1.match_total_amount_param = 90
        self.rule_2.sequence = 1
        self.rule_2.match_partner_ids |= self.partner_2
        self.rule_2.auto_reconcile = True

        self.bank_line_1.amount += 5

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'status': 'reconciled'},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'reconciled'},
        })

        # Check first line has been well reconciled.
        self.assertRecordValues(self.bank_line_1.journal_entry_ids, [
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 5.0},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 100.0},
            {'partner_id': self.partner_1.id, 'debit': 105.0, 'credit': 0.0},
        ])

        # Check second line has been well reconciled.
        self.assertRecordValues(self.cash_line_1.journal_entry_ids, [
            {'partner_id': self.partner_2.id, 'debit': 1000.0, 'credit': 0.0},
            {'partner_id': self.partner_2.id, 'debit': 0.0, 'credit': 1000.0},
        ])

    def test_auto_reconcile_with_tax(self):
        ''' Test auto reconciliation with a tax amount included in the bank statement line'''

        self.rule_1.write({
            'auto_reconcile': True,
            'force_tax_included': True,
            'tax_ids': [(6, 0, self.tax21.ids)],
            'rule_type': 'writeoff_suggestion',
        })

        self.bank_line_2.unlink()
        self.bank_line_1.amount = -121

        self._check_statement_matching(
            self.rule_1,
            {
                self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_1, 'status': 'reconciled'},
            },
            self.bank_st
        )

        # Check first line has been well reconciled.
        self.assertRecordValues(self.bank_line_1.journal_entry_ids, [
            {'partner_id': self.partner_1.id, 'debit': 100.0, 'credit': 0.0, 'tax_ids': [self.tax21.id], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 21.0, 'credit': 0.0, 'tax_ids': [], 'tax_line_id': self.tax21.id},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 121.0, 'tax_ids': [], 'tax_line_id': False},
        ])

    def test_reverted_move_matching(self):
        AccountMove = self.env['account.move']
        move = AccountMove.create({
            'name': 'To Revert',
            'journal_id': self.company_data['default_journal_bank'].id,
        })

        partner = self.env['res.partner'].create({'name': 'Eugene'})
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        AccountMoveLine.create({
            'account_id': self.account_pay.id,
            'move_id': move.id,
            'partner_id': partner.id,
            'name': 'One of these days',
            'debit': 10,
        })
        payment_bnk_line = AccountMoveLine.create({
            'account_id': self.account_bnk.id,
            'move_id': move.id,
            'partner_id': partner.id,
            'name': 'I\'m gonna cut you into little pieces',
            'credit': 10,
        })

        move.post()
        move_reversed = move._reverse_moves()
        self.assertTrue(move_reversed.exists())

        bank_st = self.env['account.bank.statement'].create({
            'name': 'test bank journal', 'journal_id': self.company_data['default_journal_bank'].id,
        })
        bank_line_1 = self.env['account.bank.statement.line'].create({
            'statement_id': bank_st.id,
            'name': '8',
            'partner_id': partner.id,
            'amount': -10,
            'sequence': 1,
        })

        expected_values = {
            bank_line_1.id: {'aml_ids': [payment_bnk_line.id], 'model': self.rule_0}
        }
        self._check_statement_matching(self.rule_0, expected_values, statements=bank_st)

    def test_match_multi_currencies(self):
        ''' Ensure the matching of candidates is made using the right statement line currency.
        In this test, the value of the statement line is 100 USD = 300 GOL = 600 DAR and we want to match two journal
        items of:
        - 100 USD = 200 GOL (= 400 DAR from the statement line point of view)
        - 11 USD = 220 DAR
        Both journal items should be suggested to the user because they represents >95% of the statement line amount (620/600 ~=97)
        (DAR).
        '''
        currency_data_2 = self.setup_multi_currency_data(default_values={
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=6.0, rate2017=4.0)


        partner = self.env['res.partner'].create({'name': 'Bernard Perdant'})

        journal = self.env['account.journal'].create({
            'name': 'test_match_multi_currencies',
            'code': 'xxxx',
            'type': 'bank',
            'currency_id': self.currency_data['currency'].id,
        })

        matching_rule = self.env['account.reconcile.model'].create({
            'name': 'test_match_multi_currencies',
            'rule_type': 'invoice_matching',
            'match_partner': True,
            'match_partner_ids': [(6, 0, partner.ids)],
            'match_total_amount': True,
            'match_total_amount_param': 95.0,
            'match_same_currency': False,
            'company_id': self.company_data['company'].id,
        })

        statement = self.env['account.bank.statement'].create({
            'name': 'test_match_multi_currencies',
            'journal_id': journal.id,
            'line_ids': [
                (0, 0, {
                    'journal_id': journal.id,
                    'date': '2016-01-01',
                    'name': 'line',
                    'partner_id': partner.id,
                    'currency_id': currency_data_2['currency'].id,
                    'amount': 300.0,            # Rate is 3 GOL = 1 USD in 2016.
                    'amount_currency': 600.0,   # Rate is 6 DAR = 1 USD in 2016
                }),
            ],
        })
        statement_line = statement.line_ids

        statement.button_open()

        move = self.env['account.move'].create({
            'type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                # Rate is 2 GOL = 1 USD in 2017.
                # The statement line will consider this line equivalent to 400 DAR.
                (0, 0, {
                    'account_id': self.company_data['default_account_receivable'].id,
                    'partner_id': partner.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                # Rate is 20 GOL = 1 USD in 2017.
                (0, 0, {
                    'account_id': self.company_data['default_account_receivable'].id,
                    'partner_id': partner.id,
                    'currency_id': currency_data_2['currency'].id,
                    'debit': 11.0,
                    'credit': 0.0,
                    'amount_currency': 220.0,
                }),
                # Line to balance the journal entry:
                (0, 0, {
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 111.0,
                }),
            ],
        })
        move.post()

        move_line_1 = move.line_ids.filtered(lambda line: line.debit == 100.0)
        move_line_2 = move.line_ids.filtered(lambda line: line.debit == 11.0)

        self.env['account.reconcile.model'].flush()
        self._check_statement_matching(matching_rule, {
            statement_line.id: {'aml_ids': (move_line_1 + move_line_2).ids, 'model': matching_rule}
        }, statements=statement)
