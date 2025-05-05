from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.test_taxes_downpayment import TestTaxesDownPayment
from odoo.addons.sale.tests.common import TestTaxCommonSale


@tagged('post_install', '-at_install')
class TestTaxesDownPaymentSale(TestTaxCommonSale, TestTaxesDownPayment):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def assert_sale_order_down_payment(
        self,
        sale_order,
        amount_type,
        amount,
        expected_values,
        soft_checking=False,
    ):
        """ Assert the expected values for the tax totals summary of the
        down payment invoice generated from the sale order passed as parameter.
        Then, generate the final invoice and assert its total is well the original
        total amount of the sale order minus the previously generated down payment.

        :param sale_order:      The SO as a sale.order record.
        :param amount_type:     The type of the global discount: 'percent' or 'fixed'.
        :param amount:          The amount to consider.
                                For 'percent', it should be a percentage [0-100].
                                For 'fixed', any amount.
        :param expected_values: The expected values for the tax_total_summary.
        :param soft_checking:   Limit the asserted values to the ones in 'expected_results'
                                and don't go deeper inside the tax_total_summary.
                                It allows to assert only the totals without asserting all the
                                tax details.
        """
        if amount_type == 'percent':
            advance_payment_method = 'percentage'
            percent_amount = amount
            fixed_amount = None
        else:  # amount_type == 'fixed'
            advance_payment_method = 'fixed'
            percent_amount = None
            fixed_amount = amount

        original_amount_total = sale_order.amount_total
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context({'active_model': sale_order._name, 'active_ids': sale_order.ids})
            .create({
                'advance_payment_method': advance_payment_method,
                'amount': percent_amount,
                'fixed_amount': fixed_amount,
            })
        )
        action_values = wizard.create_invoices()
        invoice = self.env['account.move'].browse(action_values['res_id'])
        self._assert_tax_totals_summary(
            invoice.tax_totals,
            expected_values,
            soft_checking=soft_checking,
        )

        # Full invoice.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context({'active_model': sale_order._name, 'active_ids': sale_order.ids})
            .create({
                'advance_payment_method': 'delivered',
                'amount': percent_amount,
                'fixed_amount': fixed_amount,
            })
        )
        action_values = wizard.create_invoices()
        invoice = self.env['account.move'].browse(action_values['res_id'])
        self.assertRecordValues(invoice, [
            {'amount_total': original_amount_total - expected_values['total_amount_currency']},
        ])

    # -------------------------------------------------------------------------
    # GENERIC TAXES TEST SUITE
    # -------------------------------------------------------------------------

    def test_taxes_l10n_in_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_br_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_be_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_fixed_tax_last_position_sale_orders(self):
        for test_mode, document, amount_type, amount, expected_values in self._test_taxes_fixed_tax_last_position():
            with self.subTest(test_code=test_mode):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values)

    def test_no_taxes_sale_orders(self):
        document, amount_type, amount, expected_values = self._test_no_taxes()
        sale_order = self.convert_document_to_sale_order(document)
        sale_order.action_confirm()
        self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values)

    # -------------------------------------------------------------------------
    # SPECIFIC TESTS
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def test_down_payment_invoice_multiple_taxes_and_accounts(self):
        revenue_account_1 = self.company_data['default_account_revenue']
        revenue_account_2 = revenue_account_1.copy()
        tax_account = self.company_data['default_account_tax_sale']
        receivable = self.company_data['default_account_receivable']
        product_1 = self.company_data['product_order_cost']
        product_1.property_account_income_id = revenue_account_1
        product_2 = self.company_data['product_order_sales_price']
        product_2.property_account_income_id = revenue_account_1
        product_3 = self.company_data['product_order_no']
        product_3.property_account_income_id = revenue_account_2
        tax_10 = self.percent_tax(10.0)
        tax_15 = self.percent_tax(15.0)
        (tax_10 + tax_15).invoice_repartition_line_ids.account_id = tax_account

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                # Standalone line, no tax:
                Command.create({
                    'name': 'line_1',
                    'product_id': product_1.id,
                    'price_unit': 2000.0,
                    'discount': 50.0,
                    'tax_ids': [],
                }),
                # Those lines will be merged together because same account, same tax:
                Command.create({
                    'name': 'line_2',
                    'product_id': product_1.id,
                    'price_unit': 4000.0,
                    'discount': 50.0,
                    'tax_ids': [Command.set(tax_15.ids)],
                }),
                Command.create({
                    'name': 'line_3',
                    'product_id': product_2.id,
                    'price_unit': 3000.0,
                    'tax_ids': [Command.set(tax_15.ids)],
                }),
                # Line linked to the same tax as the ones above but doesn't have the same account:
                Command.create({
                    'name': 'line_4',
                    'product_id': product_3.id,
                    'price_unit': 3000.0,
                    'tax_ids': [Command.set(tax_15.ids)],
                }),
                # Multiple taxes on the line. One tax detail will be squashed but not the other.
                Command.create({
                    'name': 'line_5',
                    'product_id': product_1.id,
                    'price_unit': 5000.0,
                    'tax_ids': [Command.set((tax_10 + tax_15).ids)],
                }),
            ],
        })
        so.action_confirm()
        self.assertRecordValues(so, [{
            'amount_untaxed': 14000.0,
            'amount_tax': 2450.0,
            'amount_total': 16450.0,
        }])

        # Create a down payment invoice of 30%.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({
                'advance_payment_method': 'percentage',
                'amount': 30,
            })
        )
        action_values = wizard.create_invoices()

        down_payment_label = f"Down Payment: {so.create_date.strftime('%m/%d/%Y')} (Draft)"
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',              'tax_ids': [],                          'price_subtotal': 1000.0},
            {'name': 'line_2',              'tax_ids': tax_15.ids,                  'price_subtotal': 2000.0},
            {'name': 'line_3',              'tax_ids': tax_15.ids,                  'price_subtotal': 3000.0},
            {'name': 'line_4',              'tax_ids': tax_15.ids,                  'price_subtotal': 3000.0},
            {'name': 'line_5',              'tax_ids': (tax_10 + tax_15).ids,       'price_subtotal': 5000.0},
            {'name': "Down Payments",       'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_label,    'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_label,    'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
            {'name': down_payment_label,    'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
            {'name': down_payment_label,    'tax_ids': (tax_10 + tax_15).ids,       'price_subtotal': 0.0},
        ])

        dp_invoice = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice.action_post()
        self.assertRecordValues(dp_invoice, [{
            'amount_untaxed': 4200.0,
            'amount_tax': 735.0,
            'amount_total': 4935.0,
        }])
        self.assertRecordValues(dp_invoice.line_ids, [
            # Down payment product lines:
            {'account_id': revenue_account_1.id,    'tax_ids': [],                      'balance': -300.0},
            {'account_id': revenue_account_1.id,    'tax_ids': tax_15.ids,              'balance': -1500.0},
            {'account_id': revenue_account_2.id,    'tax_ids': tax_15.ids,              'balance': -900.0},
            {'account_id': revenue_account_1.id,    'tax_ids': (tax_10 + tax_15).ids,   'balance': -1500.0},
            # Tax 15%:
            {'account_id': tax_account.id,          'tax_ids': [],                      'balance': -585.0},
            # Tax 10%:
            {'account_id': tax_account.id,          'tax_ids': [],                      'balance': -150.0},
            # Receivable line:
            {'account_id': receivable.id,           'tax_ids': [],                      'balance': 4935.0},
        ])

        # Create the final invoice.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({'advance_payment_method': 'delivered'})
        )
        action_values = wizard.create_invoices()

        final_invoice = self.env['account.move'].browse(action_values['res_id'])
        self.assertRecordValues(final_invoice, [{
            'amount_untaxed': so.amount_untaxed - dp_invoice.amount_untaxed,
            'amount_tax': so.amount_tax - dp_invoice.amount_tax,
            'amount_total': so.amount_total - dp_invoice.amount_total,
        }])
        self.assertRecordValues(final_invoice.line_ids, [
            # Product lines:
            {'account_id': revenue_account_1.id,    'tax_ids': [],                      'balance': -1000.0},
            {'account_id': revenue_account_1.id,    'tax_ids': tax_15.ids,              'balance': -2000.0},
            {'account_id': revenue_account_1.id,    'tax_ids': tax_15.ids,              'balance': -3000.0},
            {'account_id': revenue_account_2.id,    'tax_ids': tax_15.ids,              'balance': -3000.0},
            {'account_id': revenue_account_1.id,    'tax_ids': (tax_10 + tax_15).ids,   'balance': -5000.0},
            # Down payment section line:
            {'account_id': False,                   'tax_ids': [],                      'balance': 0.0},
            # Down payment product lines:
            {'account_id': revenue_account_1.id,    'tax_ids': [],                      'balance': 300.0},
            {'account_id': revenue_account_1.id,    'tax_ids': tax_15.ids,              'balance': 1500.0},
            {'account_id': revenue_account_2.id,    'tax_ids': tax_15.ids,              'balance': 900.0},
            {'account_id': revenue_account_1.id,    'tax_ids': (tax_10 + tax_15).ids,   'balance': 1500.0},
            # Tax 15%:
            {'account_id': tax_account.id,          'tax_ids': [],                      'balance': -1365.0},
            # Tax 10%:
            {'account_id': tax_account.id,          'tax_ids': [],                      'balance': -350.0},
            # Receivable line:
            {'account_id': receivable.id,           'tax_ids': [],                      'balance': 11515.0},
        ])

    def test_down_payment_invoice_manual_removing_of_tax(self):
        product = self.company_data['product_order_cost']
        tax_15 = self.percent_tax(15.0)

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'line_1',
                    'product_id': product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_15.ids)],
                }),
            ],
        })
        so.action_confirm()
        self.assertRecordValues(so, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        }])

        # First down payment of 30% but remove the tax from the invoice.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({
                'advance_payment_method': 'percentage',
                'amount': 30,
            })
        )
        action_values = wizard.create_invoices()

        dp_invoice_1 = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice_1.invoice_line_ids.tax_ids = [Command.clear()]
        dp_invoice_1.action_post()
        self.assertRecordValues(dp_invoice_1, [{
            'amount_untaxed': 300.0,
            'amount_tax': 0.0,
            'amount_total': 300.0,
        }])

        # Second down payment of 20%.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({
                'advance_payment_method': 'percentage',
                'amount': 20,
            })
        )
        action_values = wizard.create_invoices()

        dp_invoice_2 = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice_2.action_post()
        self.assertRecordValues(dp_invoice_2, [{
            'amount_untaxed': 200.0,
            'amount_tax': 30.0,
            'amount_total': 230.0,
        }])

        # Create the final invoice.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({'advance_payment_method': 'delivered'})
        )
        action_values = wizard.create_invoices()

        final_invoice = self.env['account.move'].browse(action_values['res_id'])
        self.assertRecordValues(final_invoice, [{
            'amount_untaxed': so.amount_untaxed - dp_invoice_1.amount_untaxed - dp_invoice_2.amount_untaxed,
            'amount_tax': so.amount_tax - dp_invoice_1.amount_tax - dp_invoice_2.amount_tax,
            'amount_total': so.amount_total - dp_invoice_1.amount_total - dp_invoice_2.amount_total,
        }])
        self.assertRecordValues(final_invoice.line_ids, [
            # Product line:
            {'tax_ids': tax_15.ids,             'balance': -1000.0},
            # Down payment section line:
            {'tax_ids': [],                     'balance': 0.0},
            # Down payment 1:
            {'tax_ids': [],                     'balance': 300.0},
            # Down payment 2:
            {'tax_ids': tax_15.ids,             'balance': 200.0},
            # Tax 15%:
            {'tax_ids': [],                     'balance': -120.0},
            # Receivable line:
            {'tax_ids': [],                     'balance': 620.0},
        ])

    def test_down_payment_invoice_foreign_currency_different_dates(self):
        product = self.company_data['product_order_cost']
        tax_15 = self.percent_tax(15.0)

        with freeze_time('2016-01-01'):
            self.foreign_currency_pricelist.currency_id = self.other_currency
            so = self.env['sale.order'].create({
                'partner_id': self.partner_a.id,
                'currency_id': self.other_currency.id,
                'pricelist_id': self.foreign_currency_pricelist.id,
                'order_line': [
                    Command.create({
                        'name': 'line_1',
                        'product_id': product.id,
                        'price_unit': 1200.0,
                        'tax_ids': [Command.set(tax_15.ids)],
                    }),
                ],
            })
            so.action_confirm()
        self.assertRecordValues(so, [{
            'amount_untaxed': 1200.0,
            'amount_tax': 180.0,
            'amount_total': 1380.0,
        }])

        # First down payment of 30% but remove the tax from the invoice.
        with freeze_time('2016-01-01'):
            wizard = (
                self.env['sale.advance.payment.inv']
                .with_context(active_model=so._name, active_ids=so.ids)
                .create({
                    'advance_payment_method': 'percentage',
                    'amount': 30,
                })
            )
            action_values = wizard.create_invoices()

            dp_invoice = self.env['account.move'].browse(action_values['res_id'])
            dp_invoice.action_post()
            self.assertRecordValues(dp_invoice, [{
                'amount_untaxed': 360.0,
                'amount_tax': 54.0,
                'amount_total': 414.0,
            }])
            self.assertRecordValues(dp_invoice.line_ids, [
                # Product line:
                {'tax_ids': tax_15.ids,             'amount_currency': -360.0,      'balance': -120.0},
                # Tax 15%:
                {'tax_ids': [],                     'amount_currency': -54.0,       'balance': -18.0},
                # Receivable line:
                {'tax_ids': [],                     'amount_currency': 414.0,       'balance': 138.0},
            ])

        # Create the final invoice.
        with freeze_time('2017-01-01'):
            wizard = (
                self.env['sale.advance.payment.inv']
                .with_context(active_model=so._name, active_ids=so.ids)
                .create({'advance_payment_method': 'delivered'})
            )
            action_values = wizard.create_invoices()

            final_invoice = self.env['account.move'].browse(action_values['res_id'])
            self.assertRecordValues(final_invoice, [{
                'amount_untaxed': so.amount_untaxed - dp_invoice.amount_untaxed,
                'amount_tax': so.amount_tax - dp_invoice.amount_tax,
                'amount_total': so.amount_total - dp_invoice.amount_total,
            }])
            self.assertRecordValues(final_invoice.line_ids, [
                # Product line:
                {'tax_ids': tax_15.ids,             'amount_currency': -1200.0,     'balance': -600.0},
                # Down payment section line:
                {'tax_ids': [],                     'amount_currency': 0.0,         'balance': 0.0},
                # Down payment:
                {'tax_ids': tax_15.ids,             'amount_currency': 360.0,       'balance': 180.0},
                # Tax 15%:
                {'tax_ids': [],                     'amount_currency': -126.0,      'balance': -63.0},
                # Receivable line:
                {'tax_ids': [],                     'amount_currency': 966.0,       'balance': 483.0},
            ])

    def test_down_payment_invoice_then_refunded_then_invoiced_again(self):
        product = self.company_data['product_order_cost']
        tax_15 = self.percent_tax(15.0)

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'line_1',
                    'product_id': product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_15.ids)],
                }),
            ],
        })
        so.action_confirm()
        self.assertRecordValues(so, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        }])

        # First down payment of 30%.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({
                'advance_payment_method': 'percentage',
                'amount': 30,
            })
        )
        action_values = wizard.create_invoices()

        draft_down_payment_label = f"Down Payment: {so.create_date.strftime('%m/%d/%Y')} (Draft)"
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                  'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",           'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': draft_down_payment_label,  'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        dp_invoice_1 = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice_1.action_post()
        self.assertRecordValues(dp_invoice_1, [{
            'amount_untaxed': 300.0,
            'amount_tax': 45.0,
            'amount_total': 345.0,
        }])

        down_payment_dp_invoice_1 = f"Down Payment (ref: {dp_invoice_1.name} on {so.create_date.strftime('%m/%d/%Y')})"
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                      'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",               'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1,     'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        # Credit note on the down payment.
        action_values = (
            self.env['account.move.reversal']
            .with_context(active_model='account.move', active_ids=dp_invoice_1.ids)
            .create({'journal_id': dp_invoice_1.journal_id.id})
            .reverse_moves()
        )
        dp_credit_note = self.env['account.move'].browse(action_values['res_id'])
        dp_credit_note.action_post()

        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                      'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",               'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1,     'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        # Second down payment of 50%.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({
                'advance_payment_method': 'percentage',
                'amount': 50,
            })
        )
        action_values = wizard.create_invoices()

        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                  'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",           'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1, 'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
            {'name': draft_down_payment_label,  'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        dp_invoice_2 = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice_2.action_post()
        self.assertRecordValues(dp_invoice_2, [{
            'amount_untaxed': 500.0,
            'amount_tax': 75.0,
            'amount_total': 575.0,
        }])

        down_payment_dp_invoice_2 = f"Down Payment (ref: {dp_invoice_2.name} on {so.create_date.strftime('%m/%d/%Y')})"
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                  'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",           'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1, 'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_2, 'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        # Create the final invoice.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({'advance_payment_method': 'delivered'})
        )
        action_values = wizard.create_invoices()

        final_invoice_1 = self.env['account.move'].browse(action_values['res_id'])
        final_invoice_1.action_post()
        self.assertRecordValues(final_invoice_1, [{
            'amount_untaxed': so.amount_untaxed - dp_invoice_2.amount_untaxed,
            'amount_tax': so.amount_tax - dp_invoice_2.amount_tax,
            'amount_total': so.amount_total - dp_invoice_2.amount_total,
        }])

        # Credit note on the final invoice.
        action_values = (
            self.env['account.move.reversal']
            .with_context(active_model='account.move', active_ids=final_invoice_1.ids)
            .create({'journal_id': final_invoice_1.journal_id.id})
            .reverse_moves()
        )
        final_credit_note = self.env['account.move'].browse(action_values['res_id'])
        final_credit_note.action_post()

        # Create a new final invoice.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({'advance_payment_method': 'delivered'})
        )
        action_values = wizard.create_invoices()

        final_invoice_2 = self.env['account.move'].browse(action_values['res_id'])
        final_invoice_2.action_post()
        self.assertRecordValues(final_invoice_2, [{
            'amount_untaxed': so.amount_untaxed - dp_invoice_2.amount_untaxed,
            'amount_tax': so.amount_tax - dp_invoice_2.amount_tax,
            'amount_total': so.amount_total - dp_invoice_2.amount_total,
        }])

    def test_down_payment_100_first_then_0_final_invoice(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        product = self.company_data['product_order_cost']
        tax_23 = self.percent_tax(23.0)

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'line_1',
                    'product_id': product.id,
                    'price_unit': price_unit,
                    'product_uom_qty': quantity,
                    'discount': discount,
                    'tax_ids': [Command.set(tax_23.ids)],
                })
                for quantity, price_unit, discount in (
                    (1.0, 519.03, 2.0),
                    (2.0, 211.97, 2.0),
                    (2.0, 75.16, 2.0),
                    (1.0, 82.84, 2.0),
                    (4.0, 1.19, 0.0),
                    (2.0, 13.63, 2.0),
                    (1.0, 2.86, 2.0),
                    (1.0, 10.0, 0.0),
                )
            ],
        })
        so.action_confirm()
        self.assertRecordValues(so, [{
            'amount_untaxed': 1196.89,
            'amount_tax': 275.28,
            'amount_total': 1472.17,
        }])

        # Create a down payment invoice of 100%.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({
                'advance_payment_method': 'percentage',
                'amount': 100,
            })
        )
        action_values = wizard.create_invoices()
        dp_invoice = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice.action_post()
        self.assertRecordValues(dp_invoice, [{
            'amount_untaxed': 1196.89,
            'amount_tax': 275.28,
            'amount_total': 1472.17,
        }])

        # Create the final invoice.
        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({'advance_payment_method': 'delivered'})
        )
        action_values = wizard.create_invoices()
        final_invoice = self.env['account.move'].browse(action_values['res_id'])
        self.assertRecordValues(final_invoice, [{
            'amount_untaxed': 0.0,
            'amount_tax': 0.0,
            'amount_total': 0.0,
        }])

    def test_down_payment_analytic_distribution_aggregation(self):
        tax_account = self.company_data['default_account_tax_sale']
        product = self.company_data['product_order_cost']
        analytic_plan = self.env['account.analytic.plan'].create({'name': "Plan Test"})
        an_acc_1 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_2 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        tax_10 = self.percent_tax(10.0)
        tax_15 = self.percent_tax(15.0)
        tax_20 = self.percent_tax(20.0)
        (tax_10 + tax_15 + tax_20).invoice_repartition_line_ids.account_id = tax_account

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                # Aggregate distributions with positive amounts.
                Command.create({
                    'name': 'line_1',
                    'product_id': product.id,
                    'price_unit': 1000.0,
                    'analytic_distribution': {an_acc_1: 100.0},
                    'tax_ids': [Command.set(tax_15.ids)],
                }),
                Command.create({
                    'name': 'line_2',
                    'product_id': product.id,
                    'price_unit': 2000.0,
                    'analytic_distribution': {an_acc_1: 50.0, an_acc_2: 50.0},
                    'tax_ids': [Command.set(tax_15.ids)],
                }),
                # Aggregate distributions with mix of positive/negative amounts.
                Command.create({
                    'name': 'line_3',
                    'product_id': product.id,
                    'price_unit': 1000.0,
                    'analytic_distribution': {an_acc_2: 100.0},
                    'tax_ids': [Command.set(tax_10.ids)],
                }),
                Command.create({
                    'name': 'line_4',
                    'product_id': product.id,
                    'price_unit': 2000.0,
                    'analytic_distribution': {an_acc_1: 125.0, an_acc_2: -25.0},
                    'tax_ids': [Command.set(tax_10.ids)],
                }),
                # Aggregate distributions of lines that lead to an empty distribution.
                Command.create({
                    'name': 'line_5',
                    'product_id': product.id,
                    'price_unit': 2000.0,
                    'analytic_distribution': {an_acc_1: 75.0, an_acc_2: 25.0},
                    'tax_ids': [Command.set(tax_20.ids)],
                }),
                Command.create({
                    'name': 'line_6',
                    'product_id': product.id,
                    'price_unit': -2000.0,
                    'analytic_distribution': {an_acc_1: 25.0, an_acc_2: 75.0},
                    'tax_ids': [Command.set(tax_20.ids)],
                }),
            ],
        })
        so.action_confirm()
        self.assertRecordValues(so, [{
            'amount_untaxed': 6000.0,
            'amount_tax': 750.0,
            'amount_total': 6750.0,
        }])

        wizard = (
            self.env['sale.advance.payment.inv']
            .with_context(active_model=so._name, active_ids=so.ids)
            .create({
                'advance_payment_method': 'percentage',
                'amount': 50,
            })
        )
        action_values = wizard.create_invoices()

        dp_invoice = self.env['account.move'].browse(action_values['res_id'])
        dp_invoice.action_post()
        self.assertRecordValues(dp_invoice, [{
            'amount_untaxed': 3000.0,
            'amount_tax': 375.0,
            'amount_total': 3375.0,
        }])
        self.assertRecordValues(dp_invoice.line_ids, [
            # Product line:
            {'tax_ids': tax_15.ids,             'analytic_distribution': {an_acc_1: 66.67, an_acc_2: 33.33},    'balance': -1500.0},
            {'tax_ids': tax_10.ids,             'analytic_distribution': {an_acc_1: 83.33, an_acc_2: 16.67},    'balance': -1500.0},
            # Tax 15%:
            {'tax_ids': [],                     'analytic_distribution': False,                                 'balance': -225.0},
            # Tax 10%:
            {'tax_ids': [],                     'analytic_distribution': False,                                 'balance': -150.0},
            # Receivable line:
            {'tax_ids': [],                     'analytic_distribution': False,                                 'balance': 3375.0},
        ])
