# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestAccountMoveReversalWizard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # ==== SETUP ====

        cls.tax_account_1 = cls.copy_account(cls.company_data['default_account_tax_sale'])
        cls.tax_account_2 = cls.copy_account(cls.company_data['default_account_tax_sale'])
        cls.tax_account_3 = cls.copy_account(cls.company_data['default_account_tax_sale'])

        cls.tax_15 = cls.env['account.tax'].create({
            'name': 'tax_15',
            'amount_type': 'percent',
            'amount': 15.0,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                (0, 0, {
                    'factor_percent': 40,
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_1.id,
                }),
                (0, 0, {
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_2.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                (0, 0, {
                    'factor_percent': 40,
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_3.id,
                }),
                (0, 0, {
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                    # /!\ No account set.
                }),
            ],
        })

        # ==== INVOICE: company's currency ====

        cls.invoice_single_currency = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2016-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'tax_ids': [(6, 0, cls.tax_15.ids)],
            })],
        })
        tax_line_1 = cls.invoice_single_currency.line_ids.filtered(lambda line: line.tax_repartition_line_id.factor_percent == 40.0)
        tax_line_2 = cls.invoice_single_currency.line_ids.filtered(lambda line: line.tax_repartition_line_id.factor_percent == 60.0)
        cls.invoice_single_currency.write({
            'line_ids': [
                (1, tax_line_1.id, {'credit': tax_line_1.credit + 12.0}),
                (1, tax_line_2.id, {'credit': tax_line_2.credit - 12.0}),
            ],
        })
        cls.invoice_single_currency.action_post()

        # ==== INVOICE: foreign currency ====

        cls.invoice_foreign_currency = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2016-01-01',
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'tax_ids': [(6, 0, cls.tax_15.ids)],
            })],
        })
        tax_line_1 = cls.invoice_foreign_currency.line_ids.filtered(lambda line: line.tax_repartition_line_id.factor_percent == 40.0)
        tax_line_2 = cls.invoice_foreign_currency.line_ids.filtered(lambda line: line.tax_repartition_line_id.factor_percent == 60.0)
        cls.invoice_foreign_currency.write({
            'line_ids': [
                (1, tax_line_1.id, {'amount_currency': tax_line_1.amount_currency + 12.0}),
                (1, tax_line_2.id, {'amount_currency': tax_line_2.amount_currency - 12.0}),
            ],
        })
        cls.invoice_foreign_currency.action_post()

    def _test_invoice_reverse_single_currency(self, reverse_move):
        self.assertInvoiceValues(reverse_move, [
            {
                'product_id': self.product_a.id,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': self.tax_15.ids,
                'tax_line_id': False,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'account_id': self.tax_account_3.id,
                'tax_ids': [],
                'tax_line_id': self.tax_15.id,
                'debit': 72.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [],
                'tax_line_id': self.tax_15.id,
                'debit': 78.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'account_id': self.company_data['default_account_receivable'].id,
                'tax_ids': [],
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 1150.0,
            },
        ], {
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        })

    def test_invoice_reverse_refund_single_currency(self):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=self.invoice_single_currency.ids)\
            .create({
                'date': '2017-01-01',
                'reason': 'no reason',
                'refund_method': 'refund',
            })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        self._test_invoice_reverse_single_currency(reverse_move)

    def test_invoice_reverse_cancel_single_currency(self):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=self.invoice_single_currency.ids)\
            .create({
                'date': '2017-01-01',
                'reason': 'no reason',
                'refund_method': 'cancel',
            })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        self._test_invoice_reverse_single_currency(reverse_move)

    def _test_invoice_reverse_foreign_currency(self, reverse_move):
        self.assertInvoiceValues(reverse_move, [
            {
                'product_id': self.product_a.id,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': self.tax_15.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3000.0,
                'debit': 1500.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'account_id': self.tax_account_3.id,
                'tax_ids': [],
                'tax_line_id': self.tax_15.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 168.0,
                'debit': 84.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [],
                'tax_line_id': self.tax_15.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 282.0,
                'debit': 141.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'account_id': self.company_data['default_account_receivable'].id,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3450.0,
                'debit': 0.0,
                'credit': 1725.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'amount_untaxed': 3000.0,
            'amount_tax': 450.0,
            'amount_total': 3450.0,
        })

    def test_invoice_reverse_refund_foreign_currency(self):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=self.invoice_foreign_currency.ids)\
            .create({
                'date': '2017-01-01',
                'reason': 'no reason',
                'refund_method': 'refund',
            })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        self._test_invoice_reverse_foreign_currency(reverse_move)

    def test_invoice_reverse_cancel_foreign_currency(self):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=self.invoice_foreign_currency.ids)\
            .create({
                'date': '2017-01-01',
                'reason': 'no reason',
                'refund_method': 'cancel',
            })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        self._test_invoice_reverse_foreign_currency(reverse_move)

    @freeze_time('2017-01-01')
    def test_invoice_reverse_modify_future_date(self):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=self.invoice_single_currency.ids)\
            .create({
                'date': '2018-01-01',
                'reason': 'no reason',
                'refund_method': 'modify',
            })
        move_reversal.reverse_moves()
        refund = self.env['account.move'].search([
            ('move_type', '=', 'out_refund'),
            ('company_id', '=', self.company_data['company'].id),
        ])

        self.assertRecordValues(refund, [{
            'state': 'draft',
            'auto_post': True,
        }])
