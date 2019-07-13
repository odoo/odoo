# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests.common import Form
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestReconciliationMatchingRules(AccountingTestCase):
    def _create_invoice_line(self, amount, partner, type):
        ''' Create an invoice on the fly.'''
        self_ctx = self.env['account.invoice'].with_context(type=type)
        journal_id = self_ctx._default_journal().id
        self_ctx = self_ctx.with_context(journal_id=journal_id)
        view = type in ('in_invoice', 'in_refund') and 'account.invoice_supplier_form' or 'account.invoice_form'
        with Form(self_ctx, view=view) as invoice_form:
            invoice_form.partner_id = partner
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.name = 'xxxx'
                invoice_line_form.quantity = 1
                invoice_line_form.price_unit = amount
                invoice_line_form.invoice_line_tax_ids.clear()
        invoice = invoice_form.save()
        invoice.action_invoice_open()
        lines = invoice.move_id.line_ids
        return lines.filtered(lambda l: l.account_id == invoice.account_id)

    def _check_statement_matching(self, rules, expected_values, statements=None):
        if statements is None:
            statements = self.bank_st + self.cash_st
        statement_lines = statements.mapped('line_ids')
        matching_values = rules._apply_rules(statement_lines)
        for st_line_id, values in matching_values.items():
            values.pop('reconciled_lines', None)
            self.assertDictEqual(values, expected_values[st_line_id])

    def setUp(self):
        super(AccountingTestCase, self).setUp()

        self.account_pay = self.env['account.account'].search([('internal_type', '=', 'payable')], limit=1)
        self.account_liq = self.env['account.account'].search([('internal_type', '=', 'liquidity')], limit=1)
        self.account_rcv = self.env['account.account'].search([('internal_type', '=', 'receivable')], limit=1)

        self.partner_1 = self.env['res.partner'].create({'name': 'partner_1'})
        self.partner_2 = self.env['res.partner'].create({'name': 'partner_2'})

        self.invoice_line_1 = self._create_invoice_line(100, self.partner_1, 'out_invoice')
        self.invoice_line_2 = self._create_invoice_line(200, self.partner_1, 'out_invoice')
        self.invoice_line_3 = self._create_invoice_line(300, self.partner_1, 'in_refund')
        self.invoice_line_4 = self._create_invoice_line(1000, self.partner_2, 'in_invoice')

        current_assets_account = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id)], limit=1)

        self.rule_0 = self.env.ref('account.reconciliation_model_default_rule')
        self.rule_1 = self.rule_0.copy()
        self.rule_1.account_id = current_assets_account
        self.rule_1.match_partner = True
        self.rule_1.match_partner_ids |= self.partner_1 + self.partner_2
        self.rule_2 = self.env['account.reconcile.model'].create({
            'name': 'write-off model',
            'rule_type': 'writeoff_suggestion',
            'match_partner': True,
            'match_partner_ids': [6, 0, (self.partner_1 + self.partner_2).ids],
            'account_id': current_assets_account.id,
        })

        invoice_number = self.invoice_line_1.move_id.name

        self.bank_journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

        self.bank_st = self.env['account.bank.statement'].create({
            'name': 'test bank journal', 'journal_id': self.bank_journal.id,
        })
        self.bank_line_1 = self.env['account.bank.statement.line'].create({
            'statement_id': self.bank_st.id,
            'name': 'invoice %s-%s' % (invoice_number.split('/')[1], invoice_number.split('/')[2]),
            'partner_id': self.partner_1.id,
            'amount': 100,
            'sequence': 1,
        })
        self.bank_line_2 = self.env['account.bank.statement.line'].create({
            'statement_id': self.bank_st.id,
            'name': 'xxxxx',
            'partner_id': self.partner_1.id,
            'amount': 600,
            'sequence': 2,
        })

        cash_journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        self.cash_st = self.env['account.bank.statement'].create({
            'name': 'test cash journal', 'journal_id': cash_journal.id,
        })
        self.cash_line_1 = self.env['account.bank.statement.line'].create({
            'statement_id': self.cash_st.id,
            'name': 'yyyyy',
            'partner_id': self.partner_2.id,
            'amount': -1000,
            'sequence': 1,
        })

        self.tax21 = self.env['account.tax'].create({
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
            {'partner_id': self.partner_1.id, 'debit': 105.0, 'credit': 0.0},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 100.0},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 5.0},
        ])

        # Check second line has been well reconciled.
        self.assertRecordValues(self.cash_line_1.journal_entry_ids, [
            {'partner_id': self.partner_2.id, 'debit': 0.0, 'credit': 1000.0},
            {'partner_id': self.partner_2.id, 'debit': 1000.0, 'credit': 0.0},
        ])

    def test_auto_reconcile_with_tax(self):
        ''' Test auto reconciliation with a tax amount included in the bank statement line'''

        self.rule_1.write({
            'auto_reconcile': True,
            'force_tax_included': True,
            'tax_id': self.tax21.id,
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
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 121.0},
            {'partner_id': self.partner_1.id, 'debit': 21.0, 'credit': 0.0, 'tax_line_id': self.tax21.id},
            {'partner_id': self.partner_1.id, 'debit': 100.0, 'credit': 0.0, 'tax_ids': [self.tax21.id]}
        ])

    def test_reverted_move_matching(self):
        AccountMove = self.env['account.move']
        move = AccountMove.create({
            'name': 'To Revert',
            'journal_id': self.bank_journal.id,
        })

        partner = self.env['res.partner'].create({'name': 'Eugene'})
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        payment_payable_line = AccountMoveLine.create({
            'account_id': self.account_pay.id,
            'move_id': move.id,
            'partner_id': partner.id,
            'name': 'One of these days',
            'debit': 10,
        })
        payment_bnk_line = AccountMoveLine.create({
            'account_id': self.account_liq.id,
            'move_id': move.id,
            'partner_id': partner.id,
            'name': 'I\'m gonna cut you into little pieces',
            'credit': 10,
        })

        move.post()
        move_reversed = AccountMove.browse(move.reverse_moves())
        self.assertTrue(move_reversed.exists())

        bank_st = self.env['account.bank.statement'].create({
            'name': 'test bank journal', 'journal_id': self.bank_journal.id,
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
