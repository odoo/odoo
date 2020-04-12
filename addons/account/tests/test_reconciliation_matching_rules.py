# -*- coding: utf-8 -*-
from odoo import fields, tools
from odoo.addons.account.tests.common import AccountTestCommon
from odoo.tests.common import Form
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestReconciliationMatchingRules(AccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestReconciliationMatchingRules, cls).setUpClass()
        cls.company = cls.env.user.company_id
        cls.account_pay = cls.a_pay
        cls.account_rcv = cls.a_recv

        cls.partner_1 = cls.env['res.partner'].create({'name': 'partner_1', 'company_id': cls.company.id})
        cls.partner_2 = cls.env['res.partner'].create({'name': 'partner_2', 'company_id': cls.company.id})

        cls.invoice_line_1 = cls._create_invoice_line(100, cls.partner_1, 'out_invoice')
        cls.invoice_line_2 = cls._create_invoice_line(200, cls.partner_1, 'out_invoice')
        cls.invoice_line_3 = cls._create_invoice_line(300, cls.partner_1, 'in_refund')
        cls.invoice_line_3.move_id.name = "RBILL/2019/09/0013" # Without demo data, avoid to match with the first invoice
        cls.invoice_line_4 = cls._create_invoice_line(1000, cls.partner_2, 'in_invoice')

        current_assets_account = cls.env['account.account'].search([
            ('user_type_id', '=', cls.env.ref('account.data_account_type_current_assets').id),
            ('company_id', '=', cls.company.id)], limit=1)

        cls.rule_0 = cls.env['account.reconcile.model'].search([('company_id', '=', cls.env.company.id), ('rule_type', '=', 'invoice_matching')])
        if not cls.rule_0:
            cls.rule_0 = cls.env['account.reconcile.model'].sudo().create({
                "name": 'Invoices Matching Rule',
                "sequence": '1',
                "rule_type": 'invoice_matching',
                "auto_reconcile": False,
                "match_nature": 'both',
                "match_same_currency": True,
                "match_total_amount": True,
                "match_total_amount_param": 100,
                "match_partner": True,
                "company_id": cls.company.id,
            })

        cls.rule_1 = cls.rule_0.copy()
        cls.rule_1.write({'line_ids': [(0, 0, {'account_id': current_assets_account.id})]})
        cls.rule_1.match_partner = True
        cls.rule_1.match_partner_ids |= cls.partner_1 + cls.partner_2
        cls.rule_2 = cls.env['account.reconcile.model'].create({
            'name': 'write-off model',
            'rule_type': 'writeoff_suggestion',
            'match_partner': True,
            'match_partner_ids': [],
            'line_ids': [(0, 0, {'account_id': current_assets_account.id})],
        })

        invoice_number = cls.invoice_line_1.move_id.name

        cls.bank_journal = cls.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', cls.company.id)], limit=1)

        cls.bank_st = cls.env['account.bank.statement'].create({
            'name': 'test bank journal', 'journal_id': cls.bank_journal.id,
        })
        cls.bank_line_1 = cls.env['account.bank.statement.line'].create({
            'statement_id': cls.bank_st.id,
            'payment_ref': 'invoice %s-%s-%s' % (invoice_number.split('/')[1], invoice_number.split('/')[2], invoice_number.split('/')[3]),
            'partner_id': cls.partner_1.id,
            'amount': 100,
            'sequence': 1,
        })
        cls.bank_line_2 = cls.env['account.bank.statement.line'].create({
            'statement_id': cls.bank_st.id,
            'payment_ref': 'xxxxx',
            'partner_id': cls.partner_1.id,
            'amount': 600,
            'sequence': 2,
        })

        cash_journal = cls.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', cls.company.id)], limit=1)
        cls.cash_st = cls.env['account.bank.statement'].create({
            'name': 'test cash journal', 'journal_id': cash_journal.id,
        })
        cls.cash_line_1 = cls.env['account.bank.statement.line'].create({
            'statement_id': cls.cash_st.id,
            'payment_ref': 'yyyyy',
            'partner_id': cls.partner_2.id,
            'amount': -1000,
            'sequence': 1,
        })

        cls.tax21 = cls.env['account.tax'].create({
            'name': '21%',
            'type_tax_use': 'purchase',
            'amount': 21,
        })

    @classmethod
    def _create_invoice_line(cls, amount, partner, type):
        ''' Create an invoice on the fly.'''
        invoice_form = Form(cls.env['account.move'].with_context(default_move_type=type, default_invoice_date='2019-09-01', default_date='2019-09-01'))
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

    def _post_statements(self):
        self.bank_st.balance_end_real = self.bank_st.balance_end
        self.cash_st.balance_end_real = self.cash_st.balance_end
        (self.bank_st + self.cash_st).button_post()

    def _check_statement_matching(self, rules, expected_values, statements=None):
        if statements is None:
            statements = self.bank_st + self.cash_st
        statement_lines = statements.mapped('line_ids').sorted()
        matching_values = rules._apply_rules(statement_lines)
        for st_line_id, values in matching_values.items():
            values.pop('reconciled_lines', None)
            self.assertDictEqual(values, expected_values[st_line_id])

    def test_matching_fields(self):
        ''' Test all fields used to restrict the rules's applicability.'''
        self._post_statements()

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
        test_category = self.env['res.partner.category'].create({'name': 'Consulting Services'})
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
        self._post_statements()

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
        self.bank_line_1.amount += 5
        self._post_statements()

        self.rule_1.sequence = 2
        self.rule_1.auto_reconcile = True
        self.rule_1.match_total_amount_param = 90
        self.rule_2.sequence = 1
        self.rule_2.match_partner_ids |= self.partner_2
        self.rule_2.auto_reconcile = True

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'status': 'reconciled'},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'reconciled'},
        })

        # Check first line has been well reconciled.
        self.assertRecordValues(self.bank_line_1.line_ids, [
            {'partner_id': self.partner_1.id, 'debit': 105.0, 'credit': 0.0},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 5.0},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 100.0},
        ])

        # Check second line has been well reconciled.
        self.assertRecordValues(self.cash_line_1.line_ids, [
            {'partner_id': self.partner_2.id, 'debit': 0.0, 'credit': 1000.0},
            {'partner_id': self.partner_2.id, 'debit': 1000.0, 'credit': 0.0},
        ])

    def test_auto_reconcile_with_tax(self):
        ''' Test auto reconciliation with a tax amount included in the bank statement line'''
        self.rule_1.write({
            'auto_reconcile': True,
            'rule_type': 'writeoff_suggestion',
            'line_ids': [(1, self.rule_1.line_ids.id, {
                'force_tax_included': True,
                'tax_ids': [(6, 0, self.tax21.ids)],
            })]
        })

        self.bank_line_2.unlink()
        self.bank_line_1.amount = -121
        self._post_statements()

        self._check_statement_matching(
            self.rule_1,
            {
                self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_1, 'status': 'reconciled'},
            },
            self.bank_st
        )

        # Check first line has been well reconciled.
        self.assertRecordValues(self.bank_line_1.line_ids, [
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 121.0, 'tax_ids': [], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 100.0, 'credit': 0.0, 'tax_ids': [self.tax21.id], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 21.0, 'credit': 0.0, 'tax_ids': [], 'tax_line_id': self.tax21.id},
        ])

    def test_reverted_move_matching(self):
        partner = self.env['res.partner'].create({'name': 'Eugene'})
        AccountMove = self.env['account.move']
        move = AccountMove.create({
            'name': 'To Revert',
            'journal_id': self.bank_journal.id,
        })

        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        payment_payable_line = AccountMoveLine.create({
            'account_id': self.account_pay.id,
            'move_id': move.id,
            'partner_id': partner.id,
            'name': 'One of these days',
            'debit': 10,
        })
        payment_bnk_line = AccountMoveLine.create({
            'account_id': self.bank_journal.payment_credit_account_id.id,
            'move_id': move.id,
            'partner_id': partner.id,
            'name': 'I\'m gonna cut you into little pieces',
            'credit': 10,
        })

        move.post()
        move_reversed = move._reverse_moves()

        self.assertTrue(move_reversed.exists())

        bank_st = self.env['account.bank.statement'].create({
            'name': 'test bank journal', 'journal_id': self.bank_journal.id,
        })
        bank_st.journal_id.default_credit_account_id = payment_bnk_line.account_id
        bank_st.journal_id.default_debit_account_id = payment_bnk_line.account_id
        bank_line_1 = self.env['account.bank.statement.line'].create({
            'statement_id': bank_st.id,
            'payment_ref': '8',
            'partner_id': partner.id,
            'amount': -10,
            'sequence': 1,
        })
        bank_st.flush()
        expected_values = {
            bank_line_1.id: {'aml_ids': [payment_bnk_line.id], 'model': self.rule_0}
        }
        self._check_statement_matching(self.rule_0, expected_values, statements=bank_st)
