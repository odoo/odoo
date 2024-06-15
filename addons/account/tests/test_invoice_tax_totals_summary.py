from odoo import Command
from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInvoiceTaxTotalsSummary(TestTaxesTaxTotalsSummary):

    def test_tax_totals_consistency_with_accounting_items(self):
        tax1 = self.fixed_tax(1, include_base_amount=True, price_include=True)
        tax2 = self.percent_tax(21, price_include=True)
        taxes = tax1 + tax2

        self.env.company.tax_calculation_rounding_method = 'round_globally'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': f'line{i}',
                    'display_type': 'product',
                    # Copy the account to multiply the tax lines.
                    'account_id': self.company_data['default_account_revenue'].copy().id,
                    # 'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 21.53,
                    'tax_ids': [Command.set(taxes.ids)],
                })
                for i in range(2)
            ],
        })

        self._assert_sub_test_tax_totals_summary(
            {
                'expected_values': {
                    'display_in_company_currency': False,
                    'same_tax_base': True,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 33.59,
                    'tax_amount_currency': 9.469999999999999,
                    'total_amount_currency': 43.06,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.59,
                            'tax_amount_currency': 9.469999999999999,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.59,
                                    'tax_amount_currency': 9.469999999999999,
                                    'display_base_amount_currency': 33.59,
                                    'group_name': self.tax_groups[0].name,
                                },
                            ],
                        },
                    ],
                },
            },
            invoice.tax_totals,
        )

        self.assertRecordValues(invoice, [{
            'amount_untaxed': invoice.tax_totals['base_amount_currency'],
            'amount_tax': invoice.tax_totals['tax_amount_currency'],
            'amount_total': invoice.tax_totals['total_amount_currency'],
        }])

    def test_tax_totals_consistency_with_tax_lines(self):
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        self.env.company.tax_calculation_rounding_method = 'round_globally'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': f'line{i}',
                    'display_type': 'product',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 16.79,
                    'tax_ids': [Command.set(taxes.ids)],
                })
                for i in range(2)
            ],
        })

        # Edit the tax line.
        tax_line = invoice.line_ids.filtered(lambda line: line.tax_line_id.amount_type == 'fixed')
        pay_term_line = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        invoice.line_ids = [
            Command.update(tax_line.id, {'balance': tax_line.balance - 5.0}),
            Command.update(pay_term_line.id, {'balance': pay_term_line.balance + 5.0}),
        ]

        self._assert_sub_test_tax_totals_summary(
            {
                'expected_values': {
                    'display_in_company_currency': False,
                    'same_tax_base': True,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 33.58,
                    'tax_amount_currency': 14.469999999999999,
                    'total_amount_currency': 48.05,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.58,
                            'tax_amount_currency': 14.469999999999999,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.58,
                                    'tax_amount_currency': 14.469999999999999,
                                    'display_base_amount_currency': 33.58,
                                    'group_name': self.tax_groups[0].name,
                                },
                            ],
                        },
                    ],
                },
            },
            invoice.tax_totals,
        )

        self.assertRecordValues(invoice, [{
            'amount_untaxed': invoice.tax_totals['base_amount_currency'],
            'amount_tax': invoice.tax_totals['tax_amount_currency'],
            'amount_total': invoice.tax_totals['total_amount_currency'],
        }])

    def test_tax_totals_with_company_currency_amounts(self):
        other_currency = self.setup_other_currency('EUR')

        self.env['res.currency.rate'].create({
            'name': '2018-01-01',
            'rate': 5.0,
            'currency_id': other_currency.id,
        })

        tax_10 = self.percent_tax(10.0, tax_group_id=self.tax_groups[0].id)
        tax_20 = self.percent_tax(20.0, tax_group_id=self.tax_groups[1].id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'currency_id': other_currency.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line',
                    'display_type': 'product',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': amount,
                    'tax_ids': [Command.set(taxes.ids)],
                })
                for amount, taxes in [(100, tax_10), (300, tax_20)]
            ],
        })

        self._assert_sub_test_tax_totals_summary(
            {
                'expected_values': {
                    'same_tax_base': False,
                    'display_in_company_currency': True,
                    'currency_id': invoice.currency_id.id,
                    'company_currency_id': invoice.company_currency_id.id,
                    'base_amount_currency': 400.0,
                    'base_amount': 80.0,
                    'tax_amount_currency': 70.0,
                    'tax_amount': 14.0,
                    'total_amount_currency': 470.0,
                    'total_amount': 94.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 400.0,
                            'base_amount': 80.0,
                            'tax_amount_currency': 70.0,
                            'tax_amount': 14.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 100.0,
                                    'base_amount': 20.0,
                                    'tax_amount_currency': 10.0,
                                    'tax_amount': 2.0,
                                    'display_base_amount_currency': 100.0,
                                    'display_base_amount': 20.0,
                                    'group_name': self.tax_groups[0].name,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 300.0,
                                    'base_amount': 60.0,
                                    'tax_amount_currency': 60.0,
                                    'tax_amount': 12.0,
                                    'display_base_amount_currency': 300.0,
                                    'display_base_amount': 60.0,
                                    'group_name': self.tax_groups[1].name,
                                },
                            ],
                        },
                    ],
                },
            },
            invoice.tax_totals,
        )
