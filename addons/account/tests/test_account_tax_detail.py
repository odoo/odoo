# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields, Command
from odoo.tests import Form, tagged

from collections import defaultdict


@tagged('post_install', '-at_install')
class TestAccountTaxDetail(AccountTestInvoicingCommon):
    ''' Test about the taxes computation stored using the account.tax.detail model for journal entries. '''

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.fake_country = cls.env['res.country'].create({
            'name': "The Island of the Fly",
            'code': 'YY',
        })

        cls.tax_tags = cls.env['account.account.tag'].create({
            'name': 'tax_tag_%s' % str(i),
            'applicability': 'taxes',
            'country_id': cls.fake_country.id,
        } for i in range(6))

        cls.tax_10 = cls.env['account.tax'].create({
            'name': "tax_10",
            'amount': 10.0,
        })
        cls.tax_10_price_include = cls.env['account.tax'].create({
            'name': "tax_10_price_include",
            'amount': 10.0,
            'price_include': True,
            'include_base_amount': True,
        })
        cls.tax_15_fixed = cls.env['account.tax'].create({
            'name': "tax_15_fixed",
            'amount': 15.0,
            'amount_type': 'fixed',
        })
        cls.tax_20_multi_rep_lines = cls.env['account.tax'].create({
            'name': "tax_20_multi_rep_lines",
            'amount': 20.0,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100.0,
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(cls.tax_tags[0].ids)],
                }),
                (0, 0, {
                    'factor_percent': 40.0,
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(cls.tax_tags[1].ids)],
                }),
                (0, 0, {
                    'factor_percent': 60.0,
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(cls.tax_tags[2].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100.0,
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(cls.tax_tags[3].ids)],
                }),
                (0, 0, {
                    'factor_percent': 40.0,
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(cls.tax_tags[4].ids)],
                }),
                (0, 0, {
                    'factor_percent': 60.0,
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(cls.tax_tags[5].ids)],
                }),
            ],
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _create_invoice(self, move_type, line_vals_list):
        return self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'account_id': self.company_data['default_account_revenue'].id,
                **vals,
            }) for vals in line_vals_list],
        })

    def _create_misc_operation(self, line_vals_list):
        move = self.env['account.move'].with_context(check_move_validity=False).create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [Command.create({
                'account_id': self.company_data['default_account_revenue'].id,
                **vals,
            }) for vals in line_vals_list],
        })
        move._recompute_dynamic_lines(recompute_all_taxes=True)
        move = move.with_context(check_move_validity=True)

        delta_balance = sum(move.line_ids.mapped('balance'))
        self.env['account.move.line'].create({
            'move_id': move.id,
            'name': 'auto_balance',
            'debit': -delta_balance if delta_balance < 0.0 else 0.0,
            'credit': delta_balance if delta_balance > 0.0 else 0.0,
            'account_id': self.company_data['default_account_receivable'].id,
        })
        return move

    def _create_move(self, move_type, line_vals_list):
        if move_type in self.env['account.move'].get_invoice_types(include_receipts=True):
            return self._create_invoice(move_type, line_vals_list)
        else:
            return self._create_misc_operation(line_vals_list)

    def assert_tax_details(self, move, expected_tax_details_list):
        # Track all lines having at least one tax detail.

        lines_with_tax_detail = move.line_ids.filtered('tax_detail_ids')

        # Check the account.tax.detail values.

        for line, expected_tax_details in expected_tax_details_list:
            self.assertRecordValues(line.tax_detail_ids, expected_tax_details)
            lines_with_tax_detail -= line

        # Check there is no unexpected tax detail.

        if lines_with_tax_detail:
            self.assertRecordValues(lines_with_tax_detail, [{'tax_detail_ids': []}] * len(lines_with_tax_detail))

    def _get_rep_line(self, tax, index=0, refund=False):
        field = 'refund_repartition_line_ids' if refund else 'invoice_repartition_line_ids'
        return tax[field].filtered(lambda rep_line: rep_line.repartition_type == 'tax').sorted('factor')[index]

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------

    def test_simple_case_single_currency(self):
        ''' Test the account.tax.details are well created and aggregated together. '''

        def assert_tax_details(move, sign, refund=False):
            self.assert_tax_details(move, [
                (move.line_ids.filtered(lambda line: len(line.tax_ids) == 2 and not line.tax_line_id), [
                    {
                        'tax_amount': sign * 10.0,
                        'tax_amount_currency': sign * 10.0,
                        'tax_base_amount': sign * 100.0,
                        'tax_base_amount_currency': sign * 100.0,
                        'tax_ids': self.tax_15_fixed.ids,
                        'tag_ids': [],
                        'tax_repartition_line_id': self._get_rep_line(self.tax_10_price_include, refund=refund).id,
                    },
                    {
                        'tax_amount': sign * 15.0,
                        'tax_amount_currency': sign * 15.0,
                        'tax_base_amount': sign * 110.0,
                        'tax_base_amount_currency': sign * 110.0,
                        'tax_ids': [],
                        'tag_ids': [],
                        'tax_repartition_line_id': self._get_rep_line(self.tax_15_fixed, refund=refund).id,
                    },
                ]),
                (move.line_ids.filtered(lambda line: len(line.tax_ids) == 1 and not line.tax_line_id), [
                    {
                        'tax_amount': sign * 16.0,
                        'tax_amount_currency': sign * 16.0,
                        'tax_base_amount': sign * 200.0,
                        'tax_base_amount_currency': sign * 200.0,
                        'tax_ids': [],
                        'tag_ids': self.tax_tags[4 if refund else 1].ids,
                        'tax_repartition_line_id': self._get_rep_line(self.tax_20_multi_rep_lines, index=0, refund=refund).id,
                    },
                    {
                        'tax_amount': sign * 24.0,
                        'tax_amount_currency': sign * 24.0,
                        'tax_base_amount': sign * 200.0,
                        'tax_base_amount_currency': sign * 200.0,
                        'tax_ids': [],
                        'tag_ids': self.tax_tags[5 if refund else 2].ids,
                        'tax_repartition_line_id': self._get_rep_line(self.tax_20_multi_rep_lines, index=1, refund=refund).id,
                    },
                ]),
            ])

        tax_commands1 = [Command.set((self.tax_10_price_include + self.tax_15_fixed).ids)]
        tax_commands2 = [Command.set(self.tax_20_multi_rep_lines.ids)]

        move = self._create_move('entry', [
            {'debit': 100.0, 'tax_ids': tax_commands1},
            {'debit': 200.0, 'tax_ids': tax_commands2},
        ])
        assert_tax_details(move, 1, refund=True)

        invoice = self._create_move('out_invoice', [
            {'price_unit': 110.0, 'tax_ids': tax_commands1},
            {'price_unit': 200.0, 'tax_ids': tax_commands2},
        ])
        assert_tax_details(invoice, -1)

        bill = self._create_move('in_invoice', [
            {'price_unit': 110.0, 'tax_ids': tax_commands1},
            {'price_unit': 200.0, 'tax_ids': tax_commands2},
        ])
        assert_tax_details(bill, 1)

    def test_import_journal_entry_with_tax_lines(self):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'name': 'base line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': 190.0,
                    'debit': 100.0,
                    'credit': 0.0,
                    'tax_ids': [Command.set(self.tax_15_fixed.ids)],
                }),
                (0, 0, {
                    'name': 'tax line',
                    'account_id': self.company_data['default_account_expense'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'tax_repartition_line_id': self._get_rep_line(self.tax_15_fixed, refund=True).id,
                    'amount_currency': 25.0,
                    'debit': 13.0,
                    'credit': 0.0,
                    'tax_tag_ids': [Command.set(self.tax_tags[:2].ids)],
                }),
                (0, 0, {
                    'name': 'balance',
                    'account_id': self.company_data['default_account_receivable'].id,
                    'debit': 0.0,
                    'credit': 113.0,
                }),
            ],
        })

        self.assert_tax_details(move, [
            (move.line_ids.filtered('tax_ids'), [{
                'tax_amount': 7.890000000000001, # 15.0 / (190.0 / 100.0)
                'tax_amount_currency': 15.0,
                'tax_base_amount': 100.0,
                'tax_base_amount_currency': 190.0,
                'tax_repartition_line_id': self._get_rep_line(self.tax_15_fixed, refund=True).id,
            }]),
        ])

    def test_rounding_issue_foreign_currency(self):
        move = self._create_move('entry', [{
            'currency_id': self.currency_data['currency'].id,
            'amount_currency': 123.456,
            'tax_ids': self.tax_20_multi_rep_lines,
        }])
        rep_line1 = self._get_rep_line(self.tax_20_multi_rep_lines, index=0, refund=True)
        rep_line2 = self._get_rep_line(self.tax_20_multi_rep_lines, index=1, refund=True)

        self.assert_tax_details(move, [
            (move.line_ids.filtered('tax_ids'), [
                {
                    'tax_amount': 4.94,
                    'tax_amount_currency': 9.876,
                    'tax_base_amount': 61.73, # 123.456 / 2.0
                    'tax_base_amount_currency': 123.456,
                    'tax_ids': [],
                    'tag_ids': self.tax_tags[4].ids,
                    'tax_repartition_line_id': rep_line1.id,
                },
                {
                    'tax_amount': 7.41,
                    'tax_amount_currency': 14.815,
                    'tax_base_amount': 61.73, # 123.456 / 2.0
                    'tax_base_amount_currency': 123.456,
                    'tax_ids': [],
                    'tag_ids': self.tax_tags[5].ids,
                    'tax_repartition_line_id': rep_line2.id,
                },
            ]),
        ])

    def test_rounding_issue_tax_calculation_round_per_line(self):
        move = self._create_move('entry', [
            {'credit': 0.15, 'tax_ids': [Command.set(self.tax_10.ids)]},
            {'credit': 0.15, 'tax_ids': [Command.set(self.tax_10.ids)]},
        ])

        self.assert_tax_details(move, [
            (move.line_ids.filtered('tax_ids')[0], [{
                'tax_amount_currency': -0.02,
                'tax_base_amount_currency': -0.15,
                'tax_repartition_line_id': self._get_rep_line(self.tax_10).id,
            }]),
            (move.line_ids.filtered('tax_ids')[1], [{
                'tax_amount_currency': -0.02,
                'tax_base_amount_currency': -0.15,
                'tax_repartition_line_id': self._get_rep_line(self.tax_10).id,
            }]),
        ])

    def test_rounding_issue_tax_calculation_round_globally(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'

        move = self._create_move('entry', [
            {'credit': 0.15, 'tax_ids': [Command.set(self.tax_10.ids)]},
            {'credit': 0.15, 'tax_ids': [Command.set(self.tax_10.ids)]},
        ])

        self.assert_tax_details(move, [
            (move.line_ids.filtered('tax_ids')[0], [{
                'tax_amount_currency': -0.015,
                'tax_base_amount_currency': -0.15,
                'tax_repartition_line_id': self._get_rep_line(self.tax_10).id,
            }]),
            (move.line_ids.filtered('tax_ids')[1], [{
                'tax_amount_currency': -0.015,
                'tax_base_amount_currency': -0.15,
                'tax_repartition_line_id': self._get_rep_line(self.tax_10).id,
            }]),
        ])
