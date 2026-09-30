from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command

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
            {'amount_currency': -100.0},
            {'amount_currency': -30.0},
            {'amount_currency': 130.0},
        ])

        invoice.currency_id = self.eur

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -30.0, 'balance': -15.0},
            {'amount_currency': 130.0, 'balance': 65.0},
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -30.0, 'balance': -15.0},
            {'amount_currency': 130.0, 'balance': 65.0},
        ])

        invoice.invoice_date = '2018-01-01'

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100.0, 'balance': -25.0},
            {'amount_currency': -30.0, 'balance': -7.5},
            {'amount_currency': 130.0, 'balance': 32.5},
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
        invoice.line_ids = [
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

    @freeze_time('2017-01-01')
    def test_currency_rate_change_only(self):
        # Regression for the rate-only path inside _sync_tax_lines: when only the currency rate
        # changes, a manually-edited tax line keeps its 'amount_currency' and 'balance' is re-rated.
        invoice = self._create_invoice_one_line(
            price_unit=100,
            tax_ids=self.tax_21,
            currency_id=self.eur.id,
        )
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -21.0, 'balance': -10.5},
            {'amount_currency': 121.0, 'balance': 60.5},
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -19.0})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -19.0, 'balance': -9.5},
            {'amount_currency': 119.0, 'balance': 59.5},
        ])

        invoice.invoice_date = '2018-01-01'
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100.0, 'balance': -25.0},
            {'amount_currency': -19.0, 'balance': -4.75},
            {'amount_currency': 119.0, 'balance': 29.75},
        ])

    def test_python_tax_and_regular_tax_on_same_line(self):
        # Smoke test for the multi-tax bucketing path in _sync_tax_lines.track_base_lines_values:
        # a base line carrying both a python_tax (depends on the product) and a percent_tax
        # (does not) must bucket consistently across snapshots regardless of tax order, so a
        # neutral edit doesn't recompute manually-set tax amounts.
        self.ensure_installed('account_tax_python')
        py_tax = self.python_tax(formula="product.list_price * 0.1")

        invoice = self._create_invoice_one_line(
            price_unit=100,
            product_id=self.product_a.id,
            tax_ids=py_tax + self.tax_21,
        )

        py_tax_line = invoice.line_ids.filtered(lambda l: l.tax_line_id == py_tax)
        invoice.line_ids = [Command.update(py_tax_line.id, {'amount_currency': -7})]

        py_tax_line = invoice.line_ids.filtered(lambda l: l.tax_line_id == py_tax)
        self.assertEqual(py_tax_line.amount_currency, -7, "manual tax amount should be set")

        # Neutral edit: change the product label. Manual tax amount must survive.
        base_line = invoice.invoice_line_ids
        invoice.line_ids = [Command.update(base_line.id, {'name': 'renamed'})]

        py_tax_line = invoice.line_ids.filtered(lambda l: l.tax_line_id == py_tax)
        self.assertEqual(py_tax_line.amount_currency, -7, "manual tax amount must be preserved on neutral edit")

    def test_manual_tax_amount_preserved_on_analytic_change(self):
        # Test that a manually adjusted tax amount is preserved when
        # an unrelated field like analytic_distribution is modified.
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Test Plan'})
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Test Account',
            'plan_id': analytic_plan.id,
        })
        analytic_dist = {str(analytic_account.id): 100.0}

        invoice = self._create_invoice_one_line(
            price_unit=82.64,
            tax_ids=self.tax_21,
        )
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -82.64},
            {'amount_currency': -17.35},
            {'amount_currency': 99.99},
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -17.36})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -82.64},
            {'amount_currency': -17.36},
            {'amount_currency': 100.00},
        ])

        base_line = invoice.invoice_line_ids
        invoice.line_ids = [Command.update(base_line.id, {'analytic_distribution': analytic_dist})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -82.64, 'analytic_distribution': analytic_dist},
            {'amount_currency': -17.36, 'analytic_distribution': False},
            {'amount_currency': 100.00, 'analytic_distribution': False},
        ])

    def test_trust_precalculated_tax_lines_on_creation(self):
        """
        Test that when a move is created with explicitly provided tax lines and balances
        (like hr.expense does), the synchronization is skipped to prevent penny drift
        and preserve line ordering.
        """
        self.tax_21.analytic = False
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True

        move_vals = {
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'account_id': self.company_data['default_account_revenue'].id,
                    'balance': -100.0,
                    'tax_ids': [Command.set(self.tax_21.ids)],
                }),
                Command.create({
                    'account_id': self.company_data['default_account_tax_sale'].id,
                    'balance': -21.01,  # Forced drifted penny
                    'tax_repartition_line_id': self.tax_21.invoice_repartition_line_ids.filtered(
                        lambda l: l.repartition_type == 'tax').id,
                }),
                Command.create({
                    'account_id': self.company_data['default_account_receivable'].id,
                    'balance': 121.01,
                }),
            ]
        }

        move = self.env['account.move'].create(move_vals)

        tax_line = move.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.balance, -21.01, "The pre-calculated tax amount must be trusted on creation.")

    def test_trust_injected_tax_lines(self):
        """
        Test that when an external engine (like Avatax) injects a tax line into an
        existing move, Odoo hits the safety block instead of deleting and recalculating it.
        """
        self.tax_21.analytic = False
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True

        invoice = self._create_invoice_one_line(
            price_unit=800.0,
            tax_ids=self.env['account.tax'],  # Empty
        )

        # Simulate Avatax injecting a computed tax line
        invoice.write({
            'line_ids': [
                Command.create({
                    'display_type': 'tax',
                    'name': 'Injected External Tax',
                    'amount_currency': -96.0,
                    'tax_repartition_line_id': self.tax_21.invoice_repartition_line_ids.filtered(
                        lambda l: l.repartition_type == 'tax').id,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                })
            ]
        })

        tax_line = invoice.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.amount_currency, -96.0, "Injected tax lines must survive synchronization.")

    def test_injection_survives_subsequent_writes(self):
        """
        When an external API (like Avatax) calculates taxes, it injects them directly via write().
        Any subsequent, completely unrelated write will wake up the diffing engine. The engine will
        see the injected tax, assume it's an unprotected error, and recalculate it (or delete it).
        """
        self.tax_21.analytic = False

        invoice = self._create_invoice_one_line(
            price_unit=1000.0,
            tax_ids=self.env['account.tax'],  # Explicitly empty
        )

        tax_rep_line = self.tax_21.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax')

        invoice.write({
            'line_ids': [
                Command.create({
                    'display_type': 'tax',
                    'name': 'API Injected Tax',
                    'amount_currency': -123.45,
                    'tax_repartition_line_id': tax_rep_line.id,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                })
            ]
        })

        # Confirm tax line is not recalculated
        tax_line = invoice.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.amount_currency, -123.45, "Initial injection failed.")

        # Do unrelated write to invoice to make sure tax is not recalculated
        invoice.write({'payment_reference': 'API_PROCESSED_001'})
        tax_line_after = invoice.line_ids.filtered('tax_repartition_line_id')

        self.assertTrue(
            tax_line_after,
            "The API-injected tax was completely deleted by the diffing engine!"
        )
        self.assertEqual(
            tax_line_after.amount_currency,
            -123.45,
            "The API-injected tax amount was overwritten by the diffing engine!"
        )
