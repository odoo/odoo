# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestReconciliationMatchingRules(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        #################
        # Company setup #
        #################
        cls.currency_data_2 = cls.setup_multi_currency_data({
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=10.0, rate2017=20.0)

        cls.company = cls.company_data['company']

        cls.account_pay = cls.company_data['default_account_payable']
        cls.current_assets_account = cls.env['account.account'].search([
            ('user_type_id', '=', cls.env.ref('account.data_account_type_current_assets').id),
            ('company_id', '=', cls.company.id)], limit=1)

        cls.bank_journal = cls.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', cls.company.id)], limit=1)
        cls.cash_journal = cls.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', cls.company.id)], limit=1)

        cls.tax21 = cls.env['account.tax'].create({
            'name': '21%',
            'type_tax_use': 'purchase',
            'amount': 21,
        })

        cls.tax12 = cls.env['account.tax'].create({
            'name': '12%',
            'type_tax_use': 'purchase',
            'amount': 12,
        })

        cls.partner_1 = cls.env['res.partner'].create({'name': 'partner_1', 'company_id': cls.company.id})
        cls.partner_2 = cls.env['res.partner'].create({'name': 'partner_2', 'company_id': cls.company.id})
        cls.partner_3 = cls.env['res.partner'].create({'name': 'partner_3', 'company_id': cls.company.id})

        ###############
        # Rules setup #
        ###############
        cls.rule_1 = cls.env['account.reconcile.model'].create({
            'name': 'Invoices Matching Rule',
            'sequence': '1',
            'rule_type': 'invoice_matching',
            'auto_reconcile': False,
            'match_nature': 'both',
            'match_same_currency': True,
            'allow_payment_tolerance': True,
            'payment_tolerance_type': 'percentage',
            'payment_tolerance_param': 0.0,
            'match_partner': True,
            'match_partner_ids': [(6, 0, (cls.partner_1 + cls.partner_2 + cls.partner_3).ids)],
            'company_id': cls.company.id,
            'line_ids': [(0, 0, {'account_id': cls.current_assets_account.id})],
        })
        cls.rule_2 = cls.env['account.reconcile.model'].create({
            'name': 'write-off model',
            'rule_type': 'writeoff_suggestion',
            'match_partner': True,
            'match_partner_ids': [],
            'line_ids': [(0, 0, {'account_id': cls.current_assets_account.id})],
        })

        ##################
        # Invoices setup #
        ##################
        cls.invoice_line_1 = cls._create_invoice_line(100, cls.partner_1, 'out_invoice')
        cls.invoice_line_2 = cls._create_invoice_line(200, cls.partner_1, 'out_invoice')
        cls.invoice_line_3 = cls._create_invoice_line(300, cls.partner_1, 'in_refund', name="RBILL/2019/09/0013")
        cls.invoice_line_4 = cls._create_invoice_line(1000, cls.partner_2, 'in_invoice')
        cls.invoice_line_5 = cls._create_invoice_line(600, cls.partner_3, 'out_invoice')
        cls.invoice_line_6 = cls._create_invoice_line(600, cls.partner_3, 'out_invoice', ref="RF12 3456")
        cls.invoice_line_7 = cls._create_invoice_line(200, cls.partner_3, 'out_invoice', pay_reference="RF12 3456")

        ####################
        # Statements setup #
        ####################
        # TODO : account_number, partner_name, transaction_type, narration
        invoice_number = cls.invoice_line_1.move_id.name
        cls.bank_st, cls.bank_st_2, cls.cash_st = cls.env['account.bank.statement'].create([
            {
                'name': 'test bank journal',
                'journal_id': cls.bank_journal.id,
                'line_ids': [
                    (0, 0, {
                        'date': '2020-01-01',
                        'payment_ref': 'invoice %s-%s' % tuple(invoice_number.split('/')[1:]),
                        'partner_id': cls.partner_1.id,
                        'amount': 100,
                        'sequence': 1,
                    }),
                    (0, 0, {
                        'date': '2020-01-01',
                        'payment_ref': 'xxxxx',
                        'partner_id': cls.partner_1.id,
                        'amount': 600,
                        'sequence': 2,
                    }),
                ],
            }, {
                'name': 'second test bank journal',
                'journal_id': cls.bank_journal.id,
                'line_ids': [
                    (0, 0, {
                        'date': '2020-01-01',
                        'payment_ref': 'nawak',
                        'narration': 'Communication: RF12 3456',
                        'partner_id': cls.partner_3.id,
                        'amount': 600,
                        'sequence': 1,
                    }),
                    (0, 0, {
                        'date': '2020-01-01',
                        'payment_ref': 'RF12 3456',
                        'partner_id': cls.partner_3.id,
                        'amount': 600,
                        'sequence': 2,
                    }),
                    (0, 0, {
                        'date': '2020-01-01',
                        'payment_ref': 'baaaaah',
                        'ref': 'RF12 3456',
                        'partner_id': cls.partner_3.id,
                        'amount': 600,
                        'sequence': 2,
                    }),
                ],
            }, {
                'name': 'test cash journal',
                'journal_id': cls.cash_journal.id,
                'line_ids': [
                    (0, 0, {
                        'date': '2020-01-01',
                        'payment_ref': 'yyyyy',
                        'partner_id': cls.partner_2.id,
                        'amount': -1000,
                        'sequence': 1,
                    }),
                ],
            }
        ])

        cls.bank_line_1, cls.bank_line_2 = cls.bank_st.line_ids
        cls.bank_line_3, cls.bank_line_4, cls.bank_line_5 = cls.bank_st_2.line_ids
        cls.cash_line_1 = cls.cash_st.line_ids
        cls._post_statements(cls)

    @classmethod
    def _create_invoice_line(cls, amount, partner, move_type, currency=None, pay_reference=None, ref=None, name=None, inv_date='2019-09-01'):
        ''' Create an invoice on the fly.'''
        invoice_form = Form(cls.env['account.move'].with_context(default_move_type=move_type, default_invoice_date=inv_date, default_date=inv_date))
        invoice_form.partner_id = partner
        if currency:
            invoice_form.currency_id = currency
        if pay_reference:
            invoice_form.payment_reference = pay_reference
        if ref:
            invoice_form.ref = ref
        if name:
            invoice_form.name = name
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'xxxx'
            invoice_line_form.quantity = 1
            invoice_line_form.price_unit = amount
            invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()
        invoice.action_post()
        lines = invoice.line_ids
        return lines.filtered(lambda l: l.account_id.user_type_id.type in ('receivable', 'payable'))

    @classmethod
    def _create_st_line(cls, amount=1000.0, date='2019-01-01', payment_ref='turlututu', **kwargs):
        st = cls.env['account.bank.statement'].create({
            'name': 'test_allow_payment_tolerance_1',
            'journal_id': kwargs.get('journal_id', cls.bank_journal.id),
            'line_ids': [Command.create({
                'amount': amount,
                'date': date,
                'payment_ref': payment_ref,
                'partner_id': cls.partner_a.id,
                **kwargs,
            })],
        })
        st.balance_end_real = st.balance_end
        st.button_post()
        return st.line_ids

    @classmethod
    def _create_reconcile_model(cls, **kwargs):
        return cls.env['account.reconcile.model'].create({
            'name': "test",
            'rule_type': 'invoice_matching',
            'allow_payment_tolerance': True,
            'payment_tolerance_type': 'percentage',
            'payment_tolerance_param': 0.0,
            **kwargs,
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'amount_type': 'percentage',
                    'label': f"test {i}",
                    **line_vals,
                })
                for i, line_vals in enumerate(kwargs.get('line_ids', []))
            ],
        })

    def _post_statements(self):
        self.bank_st.balance_end_real = self.bank_st.balance_end
        self.bank_st_2.balance_end_real = self.bank_st_2.balance_end
        self.cash_st.balance_end_real = self.cash_st.balance_end
        (self.bank_st + self.bank_st_2 + self.cash_st).button_post()

    @freeze_time('2020-01-01')
    def _check_statement_matching(self, rules, expected_values, statements=None):
        if statements is None:
            statements = self.bank_st + self.cash_st
        statement_lines = statements.mapped('line_ids').sorted()
        matching_values = rules._apply_rules(statement_lines, None)

        for st_line_id, values in matching_values.items():
            values.pop('reconciled_lines', None)
            values.pop('write_off_vals', None)
            self.assertDictEqual(values, expected_values[st_line_id])

    def test_matching_fields(self):
        # Check without restriction.
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1,
               'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })

    def test_matching_fields_match_text_location(self):
        self.rule_1.match_text_location_label = True
        self.rule_1.match_text_location_reference = False
        self.rule_1.match_text_location_note = False
        self.rule_1.allow_payment_tolerance = False
        self._check_statement_matching(self.rule_1, {
            self.bank_line_3.id: {'aml_ids': [self.invoice_line_5.id], 'model': self.rule_1, 'partner': self.bank_line_3.partner_id},
            self.bank_line_4.id: {'aml_ids': [self.invoice_line_7.id], 'model': self.rule_1, 'partner': self.bank_line_4.partner_id},
            self.bank_line_5.id: {'aml_ids': [self.invoice_line_6.id], 'model': self.rule_1, 'partner': self.bank_line_5.partner_id},
        }, statements=self.bank_st_2)

        self.rule_1.match_text_location_label = True
        self.rule_1.match_text_location_reference = False
        self.rule_1.match_text_location_note = True
        self._check_statement_matching(self.rule_1, {
            self.bank_line_3.id: {'aml_ids': [self.invoice_line_6.id], 'model': self.rule_1, 'partner': self.bank_line_3.partner_id},
            self.bank_line_4.id: {'aml_ids': [self.invoice_line_7.id], 'model': self.rule_1, 'partner': self.bank_line_4.partner_id},
            self.bank_line_5.id: {'aml_ids': [self.invoice_line_5.id], 'model': self.rule_1, 'partner': self.bank_line_5.partner_id},
        }, statements=self.bank_st_2)

        self.rule_1.match_text_location_label = True
        self.rule_1.match_text_location_reference = True
        self.rule_1.match_text_location_note = False
        self._check_statement_matching(self.rule_1, {
            self.bank_line_3.id: {'aml_ids': [self.invoice_line_5.id], 'model': self.rule_1, 'partner': self.bank_line_3.partner_id},
            self.bank_line_4.id: {'aml_ids': [self.invoice_line_7.id], 'model': self.rule_1, 'partner': self.bank_line_4.partner_id},
            self.bank_line_5.id: {'aml_ids': [self.invoice_line_7.id], 'model': self.rule_1, 'partner': self.bank_line_5.partner_id},
        }, statements=self.bank_st_2)

        self.rule_1.match_text_location_label = True
        self.rule_1.match_text_location_reference = True
        self.rule_1.match_text_location_note = True
        self._check_statement_matching(self.rule_1, {
            self.bank_line_3.id: {'aml_ids': [self.invoice_line_6.id], 'model': self.rule_1, 'partner': self.bank_line_3.partner_id},
            self.bank_line_4.id: {'aml_ids': [self.invoice_line_7.id], 'model': self.rule_1, 'partner': self.bank_line_4.partner_id},
            self.bank_line_5.id: {'aml_ids': [self.invoice_line_7.id], 'model': self.rule_1, 'partner': self.bank_line_5.partner_id},
        }, statements=self.bank_st_2)

        self.rule_1.match_text_location_label = False
        self.rule_1.match_text_location_reference = False
        self.rule_1.match_text_location_note = False
        self._check_statement_matching(self.rule_1, {
            self.bank_line_3.id: {'aml_ids': [self.invoice_line_5.id], 'model': self.rule_1, 'partner': self.bank_line_3.partner_id},
            self.bank_line_4.id: {'aml_ids': [self.invoice_line_5.id], 'model': self.rule_1, 'partner': self.bank_line_4.partner_id},
            self.bank_line_5.id: {'aml_ids': [self.invoice_line_6.id], 'model': self.rule_1, 'partner': self.bank_line_5.partner_id},
        }, statements=self.bank_st_2)

    def test_matching_fields_match_text_location_no_partner(self):
        self.bank_line_2.unlink() # One line is enough for this test
        self.bank_line_1.partner_id = None

        self.partner_1.name = "Bernard Gagnant"

        self.rule_1.write({
            'match_partner': False,
            'match_partner_ids': [(5, 0, 0)],
            'line_ids': [(5, 0, 0)],
        })

        st_line_initial_vals = {'ref': None, 'payment_ref': 'nothing', 'narration': None}
        recmod_initial_vals = {'match_text_location_label': False, 'match_text_location_note': False, 'match_text_location_reference': False}

        rec_mod_options_to_fields = {
            'match_text_location_label': 'payment_ref',
            'match_text_location_note': 'narration',
            'match_text_location_reference': 'ref',
        }

        for rec_mod_field, st_line_field in rec_mod_options_to_fields.items():
            self.rule_1.write({**recmod_initial_vals, rec_mod_field: True})
            # Fully reinitialize the statement line
            self.bank_line_1.write(st_line_initial_vals)

            # Nothing should match
            self._check_statement_matching(self.rule_1, {
                self.bank_line_1.id: {'aml_ids': []},
            }, statements=self.bank_st)

            # Test matching with the invoice ref
            self.bank_line_1.write({st_line_field: self.invoice_line_1.move_id.payment_reference})

            self._check_statement_matching(self.rule_1, {
                self.bank_line_1.id: {'aml_ids': self.invoice_line_1.ids, 'model': self.rule_1, 'partner': self.env['res.partner']},
            }, statements=self.bank_st)

            # Test matching with the partner name (reinitializing the statement line first)
            self.bank_line_1.write({**st_line_initial_vals, st_line_field: self.partner_1.name})

            self._check_statement_matching(self.rule_1, {
                self.bank_line_1.id: {'aml_ids': self.invoice_line_1.ids, 'model': self.rule_1, 'partner': self.env['res.partner']},
            }, statements=self.bank_st)

    def test_matching_fields_match_journal_ids(self):
        self.rule_1.match_journal_ids |= self.cash_st.journal_id
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })
        self.rule_1.match_journal_ids |= self.bank_st.journal_id + self.cash_st.journal_id

    def test_matching_fields_match_nature(self):
        self.rule_1.match_nature = 'amount_received'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': []},
        })
        self.rule_1.match_nature = 'amount_paid'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })
        self.rule_1.match_nature = 'both'

    def test_matching_fields_match_amount(self):
        self.rule_1.match_amount = 'lower'
        self.rule_1.match_amount_max = 150
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
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
            ], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
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
            ], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': []},
        })
        self.rule_1.match_amount = False

    def test_matching_fields_match_label(self):
        self.rule_1.match_label = 'contains'
        self.rule_1.match_label_param = 'yyyyy'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })
        self.rule_1.match_label = 'not_contains'
        self.rule_1.match_label_param = 'xxxxx'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })
        self.rule_1.match_label = 'match_regex'
        self.rule_1.match_label_param = 'xxxxx|yyyyy'
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_1.id,
                self.invoice_line_2.id,
                self.invoice_line_3.id,
            ], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })
        self.rule_1.match_label = False

    @freeze_time('2019-01-01')
    def test_zero_payment_tolerance(self):
        rule = self._create_reconcile_model(line_ids=[{}])

        for inv_type, bsl_sign in (('out_invoice', 1), ('in_invoice', -1)):

            invl = self._create_invoice_line(1000.0, self.partner_a, inv_type, inv_date='2019-01-01')

            # Exact matching.
            st_line = self._create_st_line(amount=bsl_sign * 1000.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id}},
                statements=st_line.statement_id,
            )

            # No matching because there is no tolerance.
            st_line = self._create_st_line(amount=bsl_sign * 990.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': []}},
                statements=st_line.statement_id,
            )

            # The payment amount is higher than the invoice one.
            st_line = self._create_st_line(amount=bsl_sign * 1010.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id}},
                statements=st_line.statement_id,
            )

    @freeze_time('2019-01-01')
    def test_zero_payment_tolerance_auto_reconcile(self):
        rule = self._create_reconcile_model(
            auto_reconcile=True,
            line_ids=[{}],
        )

        for inv_type, bsl_sign in (('out_invoice', 1), ('in_invoice', -1)):

            invl = self._create_invoice_line(1000.0, self.partner_a, inv_type, pay_reference='123456', inv_date='2019-01-01')

            # No matching because there is no tolerance.
            st_line = self._create_st_line(amount=bsl_sign * 990.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': []}},
                statements=st_line.statement_id,
            )

            # The payment amount is higher than the invoice one.
            st_line = self._create_st_line(amount=bsl_sign * 1010.0, payment_ref='123456')
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id, 'status': 'reconciled'}},
                statements=st_line.statement_id,
            )

            self.assertRecordValues(st_line.line_ids.sorted(lambda x: abs(x.balance)), [
                # pylint: disable=bad-whitespace
                {'balance': bsl_sign * -10.0,   'account_id': invl.account_id.id,                       'reconciled': False},
                {'balance': bsl_sign * -1000.0, 'account_id': invl.account_id.id,                       'reconciled': True},
                {'balance': bsl_sign * 1010.0,  'account_id': self.bank_journal.default_account_id.id,  'reconciled': False},
            ])

    @freeze_time('2019-01-01')
    def test_not_enough_payment_tolerance(self):
        rule = self._create_reconcile_model(
            payment_tolerance_param=0.5,
            line_ids=[{}],
        )

        for inv_type, bsl_sign in (('out_invoice', 1), ('in_invoice', -1)):

            invl = self._create_invoice_line(1000.0, self.partner_a, inv_type, inv_date='2019-01-01')

            # No matching because there is no enough tolerance.
            st_line = self._create_st_line(amount=bsl_sign * 990.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': []}},
                statements=st_line.statement_id,
            )

            # The payment amount is higher than the invoice one.
            # However, since the invoice amount is lower than the payment amount,
            # the tolerance is not checked and the invoice line is matched.
            st_line = self._create_st_line(amount=bsl_sign * 1010.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id}},
                statements=st_line.statement_id,
            )

    @freeze_time('2019-01-01')
    def test_enough_payment_tolerance(self):
        rule = self._create_reconcile_model(
            payment_tolerance_param=1.0,
            line_ids=[{}],
        )

        for inv_type, bsl_sign in (('out_invoice', 1), ('in_invoice', -1)):

            invl = self._create_invoice_line(1000.0, self.partner_a, inv_type, inv_date='2019-01-01')

            # Enough tolerance to match the invoice line.
            st_line = self._create_st_line(amount=bsl_sign * 990.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id, 'status': 'write_off'}},
                statements=st_line.statement_id,
            )

            # The payment amount is higher than the invoice one.
            # However, since the invoice amount is lower than the payment amount,
            # the tolerance is not checked and the invoice line is matched.
            st_line = self._create_st_line(amount=bsl_sign * 1010.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id}},
                statements=st_line.statement_id,
            )

    @freeze_time('2019-01-01')
    def test_enough_payment_tolerance_auto_reconcile_not_full(self):
        rule = self._create_reconcile_model(
            payment_tolerance_param=1.0,
            auto_reconcile=True,
            line_ids=[{'amount_type': 'percentage_st_line', 'amount_string': '200.0'}],
        )

        for inv_type, bsl_sign in (('out_invoice', 1), ('in_invoice', -1)):

            invl = self._create_invoice_line(1000.0, self.partner_a, inv_type, pay_reference='123456', inv_date='2019-01-01')

            # Enough tolerance to match the invoice line.
            st_line = self._create_st_line(amount=bsl_sign * 990.0, payment_ref='123456')
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id, 'status': 'reconciled'}},
                statements=st_line.statement_id,
            )

            self.assertRecordValues(st_line.line_ids.sorted(lambda x: abs(x.balance)), [
                # pylint: disable=bad-whitespace
                {'balance': bsl_sign * 990.0,   'account_id': self.bank_journal.default_account_id.id,          'reconciled': False},
                {'balance': bsl_sign * -1000.0, 'account_id': invl.account_id.id,                               'reconciled': True},
                {'balance': bsl_sign * -1980.0, 'account_id': self.company_data['default_account_revenue'].id,  'reconciled': False},
                {'balance': bsl_sign * 1990.0,  'account_id': invl.account_id.id,                               'reconciled': False},
            ])

    @freeze_time('2019-01-01')
    def test_allow_payment_tolerance_lower_amount(self):
        rule = self._create_reconcile_model(line_ids=[{'amount_type': 'percentage_st_line'}])

        for inv_type, bsl_sign in (('out_invoice', 1), ('in_invoice', -1)):

            invl = self._create_invoice_line(990.0, self.partner_a, inv_type, inv_date='2019-01-01')
            st_line = self._create_st_line(amount=bsl_sign * 1000)

            # Partial reconciliation.
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id}},
                statements=st_line.statement_id,
            )

    @freeze_time('2019-01-01')
    def test_enough_payment_tolerance_auto_reconcile(self):
        rule = self._create_reconcile_model(
            payment_tolerance_param=1.0,
            auto_reconcile=True,
            line_ids=[{}],
        )

        for inv_type, bsl_sign in (('out_invoice', 1), ('in_invoice', -1)):

            invl = self._create_invoice_line(1000.0, self.partner_a, inv_type, pay_reference='123456', inv_date='2019-01-01')

            # Enough tolerance to match the invoice line.
            st_line = self._create_st_line(amount=bsl_sign * 990.0, payment_ref='123456')
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': invl.ids, 'model': rule, 'partner': st_line.partner_id, 'status': 'reconciled'}},
                statements=st_line.statement_id,
            )

            self.assertRecordValues(st_line.line_ids.sorted(lambda x: abs(x.balance)), [
                # pylint: disable=bad-whitespace
                {'balance': bsl_sign * 10.0,    'account_id': self.company_data['default_account_revenue'].id, 'reconciled': False},
                {'balance': bsl_sign * 990.0,   'account_id': self.bank_journal.default_account_id.id,         'reconciled': False},
                {'balance': bsl_sign * -1000.0, 'account_id': invl.account_id.id,                              'reconciled': True},
            ])

    @freeze_time('2019-01-01')
    def test_percentage_st_line_auto_reconcile(self):
        rule = self._create_reconcile_model(
            payment_tolerance_param=1.0,
            rule_type='writeoff_suggestion',
            auto_reconcile=True,
            line_ids=[
                {'amount_type': 'percentage_st_line', 'amount_string': '100.0', 'label': 'A'},
                {'amount_type': 'percentage_st_line', 'amount_string': '-100.0', 'label': 'B'},
                {'amount_type': 'percentage_st_line', 'amount_string': '100.0', 'label': 'C'},
            ],
        )

        for bsl_sign in (1, -1):

            st_line = self._create_st_line(amount=bsl_sign * 1000.0)
            self._check_statement_matching(
                rule,
                {st_line.id: {'aml_ids': [], 'model': rule, 'partner': st_line.partner_id, 'status': 'reconciled'}},
                statements=st_line.statement_id,
            )

            self.assertRecordValues(st_line.line_ids.sorted(lambda x: x.account_id), [
                # pylint: disable=bad-whitespace
                {'balance': bsl_sign * 1000.0,  'account_id': self.bank_journal.default_account_id.id,         'reconciled': False},
                {'balance': bsl_sign * -1000.0, 'account_id': self.company_data['default_account_revenue'].id, 'reconciled': False},
                {'balance': bsl_sign * 1000.0,  'account_id': self.company_data['default_account_revenue'].id, 'reconciled': False},
                {'balance': bsl_sign * -1000.0, 'account_id': self.company_data['default_account_revenue'].id, 'reconciled': False},
            ])

    def test_matching_fields_match_partner_category_ids(self):
        test_category = self.env['res.partner.category'].create({'name': 'Consulting Services'})
        self.partner_2.category_id = test_category
        self.rule_1.match_partner_category_ids |= test_category
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': []},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })
        self.rule_1.match_partner_category_ids = False

    def test_mixin_rules(self):
        ''' Test usage of rules together.'''
        # rule_1 is used before rule_2.
        self.rule_1.sequence = 1
        self.rule_2.sequence = 2

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [
                self.invoice_line_2.id,
                self.invoice_line_3.id,
                self.invoice_line_1.id,
            ], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })

        # rule_2 is used before rule_1.
        self.rule_1.sequence = 2
        self.rule_2.sequence = 1

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off', 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off', 'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off', 'partner': self.cash_line_1.partner_id},
        })

        # rule_2 is used before rule_1 but only on partner_1.
        self.rule_2.match_partner_ids |= self.partner_1

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off', 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'write_off', 'partner': self.bank_line_2.partner_id},
            self.cash_line_1.id: {'aml_ids': [self.invoice_line_4.id], 'model': self.rule_1, 'partner': self.cash_line_1.partner_id},
        })

    def test_auto_reconcile(self):
        ''' Test auto reconciliation.'''
        self.bank_line_1.amount += 5

        self.rule_1.sequence = 2
        self.rule_1.auto_reconcile = True
        self.rule_1.payment_tolerance_param = 10.0
        self.rule_2.sequence = 1
        self.rule_2.match_partner_ids |= self.partner_2
        self.rule_2.auto_reconcile = True

        self._check_statement_matching(self.rule_1 + self.rule_2, {
            self.bank_line_1.id: {
                'aml_ids': self.invoice_line_1.ids,
                'model': self.rule_1,
                'status': 'reconciled',
                'partner': self.bank_line_1.partner_id,
            },
            self.bank_line_2.id: {
                'aml_ids': (self.invoice_line_2 + self.invoice_line_3).ids,
                'model': self.rule_1,
                'partner': self.bank_line_2.partner_id,
            },
            self.cash_line_1.id: {'aml_ids': [], 'model': self.rule_2, 'status': 'reconciled', 'partner': self.cash_line_1.partner_id},
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

    def test_larger_invoice_auto_reconcile(self):
        ''' Test auto reconciliation with an invoice with larger amount than the
        statement line's, for rules without write-offs.'''
        self.bank_line_1.amount = 40
        self.invoice_line_1.move_id.payment_reference = self.bank_line_1.payment_ref

        self.rule_1.sequence = 2
        self.rule_1.allow_payment_tolerance = False
        self.rule_1.auto_reconcile = True
        self.rule_1.line_ids = [(5, 0, 0)]

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {
                'aml_ids': self.invoice_line_1.ids,
                'model': self.rule_1,
                'status': 'reconciled',
                'partner': self.bank_line_1.partner_id,
            },
            self.bank_line_2.id: {
                'aml_ids': (self.invoice_line_2 + self.invoice_line_3).ids,
                'model': self.rule_1,
                'partner': self.bank_line_1.partner_id,
            },
        }, statements=self.bank_st)

        # Check first line has been well reconciled.
        self.assertRecordValues(self.bank_line_1.line_ids, [
            {'partner_id': self.partner_1.id, 'debit': 40.0, 'credit': 0.0},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 40.0},
        ])

        self.assertEqual(self.invoice_line_1.amount_residual, 60.0, "The invoice should have been partially reconciled")

    def test_auto_reconcile_with_duplicate_match(self):
        """ If multiple bank statement lines match with the same invoice, ensure the
         correct line is auto-validated and no crashing happens.
        """

        # Only the invoice defined in this test should have this partner
        partner = self.env['res.partner'].create({'name': "The Only One"})
        invoice_line = self._create_invoice_line(
            2000, partner, 'out_invoice', ref="REF 7788")

        # Enable auto-validation and don't restrict the partners that can be matched on
        # so our newly created partner can be matched.
        self.rule_1.write({
            'auto_reconcile': True,
            'match_partner_ids': [(5, 0, 0)],
        })
        self.rule_1.match_partner_ids = []

        # This line has a matching payment reference and the exact amount of the
        # invoice. As a result it should auto-validate.
        self.bank_line_1.amount = 2000
        self.bank_line_1.partner_id = partner
        self.bank_line_1.payment_ref = "REF 7788"

        # This line doesn't have a matching amount or reference, but it does have a
        # matching partner.
        self.bank_line_2.amount = 1800
        self.bank_line_2.partner_id = partner
        self.bank_line_2.payment_ref = "something"

        # Verify the auto-validation happens with the first line, and no exceptions.
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {
                'aml_ids': [invoice_line.id],
                'model': self.rule_1,
                'status': 'reconciled',
                'partner': self.bank_line_1.partner_id
            },
            self.bank_line_2.id: {
                'aml_ids': []
            },
        }, statements=self.bank_st)

    def test_auto_reconcile_with_tax(self):
        ''' Test auto reconciliation with a tax amount included in the bank statement line'''
        self.rule_1.write({
            'auto_reconcile': True,
            'rule_type': 'writeoff_suggestion',
            'line_ids': [(1, self.rule_1.line_ids.id, {
                'amount': 50,
                'force_tax_included': True,
                'tax_ids': [(6, 0, self.tax21.ids)],
            }), (0, 0, {
                'amount': 100,
                'force_tax_included': False,
                'tax_ids': [(6, 0, self.tax12.ids)],
                'account_id': self.current_assets_account.id,
            })]
        })

        self.bank_line_1.amount = -121

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_1, 'status': 'reconciled', 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [], 'model': self.rule_1, 'status': 'reconciled', 'partner': self.bank_line_2.partner_id},
        }, statements=self.bank_st)

        # Check first line has been well reconciled.
        self.assertRecordValues(self.bank_line_1.line_ids, [
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 121.0, 'tax_ids': [], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 7.26, 'tax_ids': [], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 50.0, 'credit': 0.0, 'tax_ids': [self.tax21.id], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 10.5, 'credit': 0.0, 'tax_ids': [], 'tax_line_id': self.tax21.id},
            {'partner_id': self.partner_1.id, 'debit': 60.5, 'credit': 0.0, 'tax_ids': [self.tax12.id], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 7.26, 'credit': 0.0, 'tax_ids': [], 'tax_line_id': self.tax12.id},
        ])

    def test_auto_reconcile_with_tax_fpos(self):
        """ Test the fiscal positions are applied by reconcile models when using taxes.
        """
        self.rule_1.write({
            'auto_reconcile': True,
            'rule_type': 'writeoff_suggestion',
            'line_ids': [(1, self.rule_1.line_ids.id, {
                'amount': 100,
                'force_tax_included': True,
                'tax_ids': [(6, 0, self.tax21.ids)],
            })]
        })

        self.partner_1.country_id = self.env.ref('base.lu')
        belgium = self.env.ref('base.be')
        self.partner_2.country_id = belgium

        self.bank_line_2.partner_id = self.partner_2

        self.bank_line_1.amount = -121
        self.bank_line_2.amount = -112

        self.env['account.fiscal.position'].create({
            'name': "Test",
            'country_id': belgium.id,
            'auto_apply': True,
            'tax_ids': [
                Command.create({
                    'tax_src_id': self.tax21.id,
                    'tax_dest_id': self.tax12.id,
                }),
            ]
        })

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [], 'model': self.rule_1, 'status': 'reconciled', 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [], 'model': self.rule_1, 'status': 'reconciled', 'partner': self.bank_line_2.partner_id},
        }, statements=self.bank_st)

        self.assertRecordValues(self.bank_line_1.line_ids, [
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 121.0, 'tax_ids': [], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 100.0, 'credit': 0.0, 'tax_ids': [self.tax21.id], 'tax_line_id': False},
            {'partner_id': self.partner_1.id, 'debit': 21.0, 'credit': 0.0, 'tax_ids': [], 'tax_line_id': self.tax21.id},
        ])

        self.assertRecordValues(self.bank_line_2.line_ids, [
            {'partner_id': self.partner_2.id, 'debit': 0.0, 'credit': 112.0, 'tax_ids': [], 'tax_line_id': False},
            {'partner_id': self.partner_2.id, 'debit': 100.0, 'credit': 0.0, 'tax_ids': [self.tax12.id], 'tax_line_id': False},
            {'partner_id': self.partner_2.id, 'debit': 12.0, 'credit': 0.0, 'tax_ids': [], 'tax_line_id': self.tax12.id},
        ])


    def test_reverted_move_matching(self):
        partner = self.partner_1
        AccountMove = self.env['account.move']
        move = AccountMove.create({
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_pay.id,
                    'partner_id': partner.id,
                    'name': 'One of these days',
                    'debit': 10,
                }),
                (0, 0, {
                    'account_id': self.bank_journal.company_id.account_journal_payment_credit_account_id.id,
                    'partner_id': partner.id,
                    'name': 'I\'m gonna cut you into little pieces',
                    'credit': 10,
                })
            ],
        })

        payment_bnk_line = move.line_ids.filtered(lambda l: l.account_id == self.bank_journal.company_id.account_journal_payment_credit_account_id)

        move.action_post()
        move_reversed = move._reverse_moves()
        self.assertTrue(move_reversed.exists())

        self.bank_line_1.write({
            'payment_ref': '8',
            'partner_id': partner.id,
            'amount': -10,
        })
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [payment_bnk_line.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': [self.invoice_line_1.id, self.invoice_line_2.id, self.invoice_line_3.id], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
        }, statements=self.bank_st)

    def test_match_different_currencies(self):
        partner = self.env['res.partner'].create({'name': 'Bernard Gagnant'})
        self.rule_1.write({'match_partner_ids': [(6, 0, partner.ids)], 'match_same_currency': False})

        currency_inv = self.env.ref('base.EUR')
        currency_inv.active = True
        currency_statement = self.env.ref('base.JPY')

        currency_statement.active = True

        invoice_line = self._create_invoice_line(100, partner, 'out_invoice', currency=currency_inv)

        self.bank_line_1.write({'partner_id': partner.id, 'foreign_currency_id': currency_statement.id, 'amount_currency': 100, 'payment_ref': 'test'})
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': invoice_line.ids, 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': []},
        }, statements=self.bank_st)

    def test_invoice_matching_rule_no_partner(self):
        """ Tests that a statement line without any partner can be matched to the
        right invoice if they have the same payment reference.
        """
        self.invoice_line_1.move_id.write({'payment_reference': 'Tournicoti66'})
        self.rule_1.allow_payment_tolerance = False

        self.bank_line_1.write({
            'payment_ref': 'Tournicoti66',
            'partner_id': None,
            'amount': 95,
        })

        self.rule_1.write({
            'line_ids': [(5, 0, 0)],
            'match_partner': False,
            'match_label': 'contains',
            'match_label_param': 'Tournicoti',  # So that we only match what we want to test
        })

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': []},
        }, self.bank_st)

    def test_inv_matching_rule_auto_rec_no_partner_with_writeoff(self):
        self.invoice_line_1.move_id.write({'payment_reference': 'doudlidou355'})

        self.bank_line_1.write({
            'payment_ref': 'doudlidou355',
            'partner_id': None,
            'amount': 95,
        })

        self.rule_1.write({
            'match_partner': False,
            'match_label': 'contains',
            'match_label_param': 'doudlidou',  # So that we only match what we want to test
            'payment_tolerance_param': 10.0,
            'auto_reconcile': True,
        })

        # Check bank reconciliation

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id, 'status': 'reconciled'},
            self.bank_line_2.id: {'aml_ids': []},
        }, self.bank_st)

        # Check invoice line has been fully reconciled, with a write-off.
        self.assertRecordValues(self.bank_line_1.line_ids, [
            {'partner_id': self.partner_1.id, 'debit': 95.0, 'credit': 0.0, 'account_id': self.bank_journal.default_account_id.id, 'reconciled': False},
            {'partner_id': self.partner_1.id, 'debit': 5.0, 'credit': 0.0, 'account_id': self.current_assets_account.id, 'reconciled': False},
            {'partner_id': self.partner_1.id, 'debit': 0.0, 'credit': 100.0, 'account_id': self.invoice_line_1.account_id.id, 'reconciled': True},
        ])

        self.assertEqual(self.invoice_line_1.amount_residual, 0.0, "The invoice should have been fully reconciled")

    def test_partner_mapping_rule(self):
        self.bank_line_1.write({'partner_id': None, 'payment_ref': 'toto42', 'narration': None})
        self.bank_line_2.write({'partner_id': None})

        # Do the test for both rule 1 and 2, so that we check invoice matching and write-off rules
        for rule in (self.rule_1 + self.rule_2):

            # To cope for minor differences in rule results
            matching_amls = rule.rule_type == 'invoice_matching' and self.invoice_line_1.ids or []
            result_status = rule.rule_type == 'writeoff_suggestion' and {'status': 'write_off'} or {}

            match_result = {**result_status, 'aml_ids': matching_amls, 'model': rule, 'partner': self.partner_1}
            no_match_result = {'aml_ids': []}

            # Without mapping, there should be no match
            self._check_statement_matching(rule, {
                self.bank_line_1.id: no_match_result,
                self.bank_line_2.id: no_match_result,
            }, self.bank_st)

            # We add some mapping for payment reference to rule_1
            rule.write({
                'partner_mapping_line_ids': [(0, 0, {
                    'partner_id': self.partner_1.id,
                    'payment_ref_regex': 'toto.*',
                })]
            })

            # bank_line_1 should now match
            self._check_statement_matching(rule, {
                self.bank_line_1.id: match_result,
                self.bank_line_2.id: no_match_result,
            }, self.bank_st)

            # If we now add a narration regex to the same mapping line, nothing should match
            rule.partner_mapping_line_ids.write({'narration_regex': ".*coincoin"})
            self.bank_line_1.write({'narration': None}) # Reset from possible previous iteration

            self._check_statement_matching(rule, {
                self.bank_line_1.id: no_match_result,
                self.bank_line_2.id: no_match_result,
            }, self.bank_st)

            # If we set the narration so that it matches the new mapping criterium, line_1 matches
            self.bank_line_1.write({'narration': "42coincoin"})

            self._check_statement_matching(rule, {
                self.bank_line_1.id: match_result,
                self.bank_line_2.id: no_match_result,
            }, self.bank_st)

    def test_partner_name_in_communication(self):
        self.invoice_line_1.partner_id.write({'name': "Archibald Haddock"})
        self.bank_line_1.write({'partner_id': None, 'payment_ref': '1234//HADDOCK-Archibald'})
        self.bank_line_2.write({'partner_id': None})
        self.rule_1.write({'match_partner': False})

        # bank_line_1 should match, as its communication contains the invoice's partner name
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': []},
        }, self.bank_st)

    def test_partner_name_with_regexp_chars(self):
        self.invoice_line_1.partner_id.write({'name': "Archibald + Haddock"})
        self.bank_line_1.write({'partner_id': None, 'payment_ref': '1234//HADDOCK+Archibald'})
        self.bank_line_2.write({'partner_id': None})
        self.rule_1.write({'match_partner': False})

        # The query should still work
        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': [self.invoice_line_1.id], 'model': self.rule_1, 'partner': self.bank_line_1.partner_id},
            self.bank_line_2.id: {'aml_ids': []},
        }, self.bank_st)

    def test_match_multi_currencies(self):
        ''' Ensure the matching of candidates is made using the right statement line currency.

        In this test, the value of the statement line is 100 USD = 300 GOL = 900 DAR and we want to match two journal
        items of:
        - 100 USD = 200 GOL (= 600 DAR from the statement line point of view)
        - 14 USD = 280 DAR

        Both journal items should be suggested to the user because they represents 98% of the statement line amount
        (DAR).
        '''
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
            'allow_payment_tolerance': True,
            'payment_tolerance_type': 'percentage',
            'payment_tolerance_param': 5.0,
            'match_same_currency': False,
            'company_id': self.company_data['company'].id,
            'past_months_limit': False,
        })

        statement = self.env['account.bank.statement'].create({
            'name': 'test_match_multi_currencies',
            'journal_id': journal.id,
            'line_ids': [
                (0, 0, {
                    'journal_id': journal.id,
                    'date': '2016-01-01',
                    'payment_ref': 'line',
                    'partner_id': partner.id,
                    'foreign_currency_id': self.currency_data_2['currency'].id,
                    'amount': 300.0,            # Rate is 3 GOL = 1 USD in 2016.
                    'amount_currency': 900.0,   # Rate is 10 DAR = 1 USD in 2016 but the rate used by the bank is 9:1.
                }),
            ],
        })
        statement_line = statement.line_ids

        statement.button_post()

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                # Rate is 2 GOL = 1 USD in 2017.
                # The statement line will consider this line equivalent to 600 DAR.
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
                    'currency_id': self.currency_data_2['currency'].id,
                    'debit': 14.0,
                    'credit': 0.0,
                    'amount_currency': 280.0,
                }),
                # Line to balance the journal entry:
                (0, 0, {
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 114.0,
                }),
            ],
        })
        move.action_post()

        move_line_1 = move.line_ids.filtered(lambda line: line.debit == 100.0)
        move_line_2 = move.line_ids.filtered(lambda line: line.debit == 14.0)

        self._check_statement_matching(matching_rule, {
            statement_line.id: {'aml_ids': (move_line_1 + move_line_2).ids, 'model': matching_rule, 'partner': statement_line.partner_id}
        }, statements=statement)

    @freeze_time('2020-01-01')
    def test_inv_matching_with_write_off(self):
        self.rule_1.payment_tolerance_param = 10.0
        self.bank_st.line_ids[1].unlink() # We don't need this one here
        statement_line = self.bank_st.line_ids[0]
        statement_line.write({
            'payment_ref': self.invoice_line_1.move_id.payment_reference,
            'amount': 90,
        })

        # Test the invoice-matching part
        self._check_statement_matching(self.rule_1, {
            statement_line.id: {'aml_ids': self.invoice_line_1.ids, 'model': self.rule_1, 'partner': self.invoice_line_1.partner_id, 'status': 'write_off'},
        }, self.bank_st)

        # Test the write-off part
        expected_write_off = {
            'balance': 10,
            'currency_id': self.company_data['currency'].id,
            'reconcile_model_id': self.rule_1.id,
            'account_id': self.current_assets_account.id,
        }

        matching_result = self.rule_1._apply_rules(statement_line)

        self.assertEqual(len(matching_result[statement_line.id].get('write_off_vals', [])), 1, "Exactly one write-off line should be proposed.")

        full_write_off_dict = matching_result[statement_line.id]['write_off_vals'][0]
        to_compare = {key: full_write_off_dict[key] for key in expected_write_off}

        self.assertDictEqual(expected_write_off, to_compare)

    @freeze_time('2020-01-01')
    def test_matching_with_write_off_foreign_currency(self):
        journal_foreign_curr = self.company_data['default_journal_bank'].copy()
        journal_foreign_curr.currency_id = self.currency_data['currency']

        reco_model = self._create_reconcile_model(
            auto_reconcile=True,
            rule_type='writeoff_suggestion',
            line_ids=[{
                'amount_type': 'percentage',
                'amount': 100.0,
                'account_id': self.company_data['default_account_revenue'].id,
            }],
        )

        st_line = self._create_st_line(amount=100.0, payment_ref='123456', journal_id=journal_foreign_curr.id)

        reco_model._apply_rules(st_line)

        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(st_line.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100.0, 'currency_id': self.currency_data['currency'].id, 'balance': -50.0},
            {'amount_currency': 100.0, 'currency_id': self.currency_data['currency'].id, 'balance': 50.0},
        ])

    def test_inv_matching_with_write_off_autoreconcile(self):
        self.bank_line_1.amount = 95

        self.rule_1.sequence = 2
        self.rule_1.auto_reconcile = True
        self.rule_1.payment_tolerance_param = 10.0

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {
                'aml_ids': self.invoice_line_1.ids,
                'model': self.rule_1,
                'status': 'reconciled',
                'partner': self.bank_line_1.partner_id,
            },
            self.bank_line_2.id: {
                'aml_ids': (self.invoice_line_2 + self.invoice_line_3).ids,
                'model': self.rule_1,
                'partner': self.bank_line_2.partner_id,
            },
        }, statements=self.bank_st)

        # Check first line has been properly reconciled.
        self.assertRecordValues(self.bank_line_1.line_ids, [
            # pylint: disable=bad-whitespace
            {'partner_id': self.partner_1.id,   'debit': 95.0,  'credit': 0.0,      'account_id': self.bank_journal.default_account_id.id,  'reconciled': False},
            {'partner_id': self.partner_1.id,   'debit': 5.0,   'credit': 0.0,      'account_id': self.current_assets_account.id,           'reconciled': False},
            {'partner_id': self.partner_1.id,   'debit': 0.0,   'credit': 100.0,    'account_id': self.invoice_line_1.account_id.id,        'reconciled': True},
        ])

        self.assertEqual(self.invoice_line_1.amount_residual, 0.0, "The invoice should have been fully reconciled")

    def test_payment_similar_communications(self):
        def create_payment_line(amount, memo, partner):
            payment = self.env['account.payment'].create({
                'amount': amount,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'ref': memo,
                'destination_account_id': self.company_data['default_account_receivable'].id,
            })
            payment.action_post()

            return payment.line_ids.filtered(lambda x: x.account_id.user_type_id.type not in {'receivable', 'payable'})

        payment_partner = self.env['res.partner'].create({
            'name': "Bernard Gagnant",
        })

        self.rule_1.match_partner_ids = [(6, 0, payment_partner.ids)]

        pmt_line_1 = create_payment_line(500, 'a1b2c3', payment_partner)
        pmt_line_2 = create_payment_line(500, 'a1b2c3', payment_partner)
        create_payment_line(500, 'd1e2f3', payment_partner)

        self.bank_line_1.write({
            'amount': 1000,
            'payment_ref': 'a1b2c3',
            'partner_id': payment_partner.id,
        })
        self.bank_line_2.unlink()
        self.rule_1.allow_payment_tolerance = False

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': (pmt_line_1 + pmt_line_2).ids, 'model': self.rule_1, 'partner': payment_partner},
        }, statements=self.bank_line_1.statement_id)

    def test_no_amount_check_keep_first(self):
        """ In case the reconciliation model doesn't check the total amount of the candidates,
        we still don't want to suggest more than are necessary to match the statement.
        For example, if a statement line amounts to 250 and is to be matched with three invoices
        of 100, 200 and 300 (retrieved in this order), only 100 and 200 should be proposed.
        """
        self.rule_1.allow_payment_tolerance = False
        self.bank_line_2.amount = 250
        self.bank_line_1.partner_id = None

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': [self.invoice_line_1.id, self.invoice_line_2.id], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
        }, statements=self.bank_st)

    def test_no_amount_check_exact_match(self):
        """ If a reconciliation model finds enough candidates for a full reconciliation,
        it should still check the following candidates, in case one of them exactly
        matches the amount of the statement line. If such a candidate exist, all the
        other ones are disregarded.
        """
        self.rule_1.allow_payment_tolerance = False
        self.bank_line_2.amount = 300
        self.bank_line_1.partner_id = None

        self._check_statement_matching(self.rule_1, {
            self.bank_line_1.id: {'aml_ids': []},
            self.bank_line_2.id: {'aml_ids': [self.invoice_line_3.id], 'model': self.rule_1, 'partner': self.bank_line_2.partner_id},
        }, statements=self.bank_st)
