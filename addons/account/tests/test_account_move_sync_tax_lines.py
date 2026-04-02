from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged
from odoo import fields, Command
from odoo.exceptions import UserError, ValidationError

from collections import defaultdict
from unittest.mock import patch
from datetime import timedelta
from freezegun import freeze_time



@tagged('post_install', '-at_install')
class TestAccountMoveSyncTaxLines(AccountTestInvoicingCommon):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tax_21 = cls.percent_tax(21.0)
        cls.tax_6 = cls.percent_tax(6.0)
        cls.eur = cls.setup_other_currency('EUR', rates=[
            ('2017-01-01', 2.0),
            ('2018-01-01', 4.0),
        ])

    @freeze_time('2017-01-01')
    def test_manual_tax_amount_foreign_currency_flow(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)
    
        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30})]

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100},
            {'amount_currency': -30},
            {'amount_currency': 130},
        ])

        invoice.currency_id = self.eur

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100, 'balance': -50},
            {'amount_currency': -30, 'balance': -15},
            {'amount_currency': 130, 'balance': 65},
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30})]

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100, 'balance': -50},
            {'amount_currency': -30, 'balance': -15},
            {'amount_currency': 130, 'balance': 65},
        ])

        invoice.invoice_date = '2018-01-01'

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100, 'balance': -25},
            {'amount_currency': -30, 'balance': -7.5},
            {'amount_currency': 130, 'balance': 32.5},
        ])

    def test_manual_tax_amount_adding_removing_lines(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_6),
            self._prepare_invoice_line(price_unit=100),
        ])
    
        tax_line_6 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_6)
        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [
            Command.update(tax_line_6.id, {'amount_currency': -10}),
            Command.update(tax_line_21.id, {'amount_currency': -30}),
        ]

        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -30},
            {'amount_currency': -10},
            {'amount_currency': 340},
        ])

        # Removing a base line not affecting the tax line should not trigger a recomputation.
        base_line = invoice.invoice_line_ids.filtered(lambda line: not line.tax_ids)
        invoice.line_ids = [Command.unlink(base_line.id)]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -30},
            {'amount_currency': -10},
            {'amount_currency': 240},
        ])

        # Removing a base line affecting a specific tax line should only trigger the recomputation of that one.
        base_line = invoice.invoice_line_ids.filtered(lambda line: line.tax_ids == self.tax_6)
        invoice.line_ids = [Command.unlink(base_line.id)]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -30},
            {'amount_currency': 130},
        ])

        # Triggering the recomputation of the tax line but editing its amount at the same time should
        # keep the user input.
        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            Command.update(tax_line.id, {'amount_currency': -50}),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -50},
            {'amount_currency': 250},
        ])

    def test_analytic_distribution_and_analytic_checkbox_on_taxes(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Default'})
        anal_acc_a = self.env['account.analytic.account'].create({
            'name': 'anal_acc_a',
            'plan_id': analytic_plan.id,
        })
        anal_distr_a = {str(anal_acc_a.id): 100.0}
        anal_acc_b = self.env['account.analytic.account'].create({
            'name': 'anal_acc_b',
            'plan_id': analytic_plan.id,
        })
        anal_distr_b = {str(anal_acc_b.id): 100.0}
        anal_acc_c = self.env['account.analytic.account'].create({
            'name': 'anal_acc_c',
            'plan_id': analytic_plan.id,
        })
        anal_distr_c = {str(anal_acc_c.id): 100.0}

        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, analytic_distribution=anal_distr_a, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=100, analytic_distribution=anal_distr_b, tax_ids=self.tax_21),
        ])
        # There are 2 tax lines because the repartition lines are not 'use_in_tax_closing'.
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_b},
            {'amount_currency': 242, 'analytic_distribution': None},
        ])

        # All the tax lines should now be merged into one.
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True
        invoice.invoice_line_ids = [
            self._prepare_invoice_line(price_unit=100, analytic_distribution=anal_distr_c, tax_ids=self.tax_21),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_c},
            {'amount_currency': -63, 'analytic_distribution': None},
            {'amount_currency': 363, 'analytic_distribution': None},
        ])

        # Custom tax amount.
        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -70})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_c},
            {'amount_currency': -70, 'analytic_distribution': None},
            {'amount_currency': 370, 'analytic_distribution': None},
        ])

        # Changing the analytic accounts should not recompute the tax line.
        base_line_b = invoice.invoice_line_ids.filtered(lambda line: line.analytic_distribution == anal_distr_b)
        base_line_c = invoice.invoice_line_ids.filtered(lambda line: line.analytic_distribution == anal_distr_c)
        invoice.with_context(blu=True).line_ids = [
            Command.update(base_line_b.id, {'analytic_distribution': anal_distr_a}),
            Command.update(base_line_c.id, {'analytic_distribution': anal_distr_a}),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -70, 'analytic_distribution': None},
            {'amount_currency': 370, 'analytic_distribution': None},
        ])

        # Same with the 'analytic' ticked on the tax. This time, changing the analytic distribution
        # will impact the tax lines.
        self.tax_21.analytic = True
        invoice.line_ids = [
            Command.update(invoice.invoice_line_ids[0].id, {'analytic_distribution': anal_distr_a}),
            Command.update(invoice.invoice_line_ids[1].id, {'analytic_distribution': anal_distr_b}),
            Command.update(invoice.invoice_line_ids[2].id, {'analytic_distribution': anal_distr_c}),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_c},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_c},
            {'amount_currency': 363, 'analytic_distribution': None},
        ])

