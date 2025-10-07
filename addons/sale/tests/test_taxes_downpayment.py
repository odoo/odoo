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
        cls.company_data['company'].downpayment_account_id = cls.env['account.account'].create({
            'name': 'Downpayment account',
            'account_type': 'liability_current',
            'code': 'TestDownpayment',
            'reconcile': True,
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def assert_sale_order_document_down_payment(
        self,
            document,
        amount_type,
        amount,
        expected_values,
        soft_checking=False,
    ):
        """ Assert the expected values for the tax totals summary of the
        down payment invoice generated from the sale order passed as parameter.
        Then, generate the final invoice and assert its total is well the original
        total amount of the sale order minus the previously generated down payment.

        :param document:        The document dictionary to generate the sale.order record.
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
        sale_order = self.convert_document_to_sale_order(document)
        sale_order.action_confirm()
        original_amount_total = sale_order.amount_total
        invoice = self._create_down_payment_invoice(sale_order, amount_type, amount)
        self._assert_tax_totals_summary(invoice.tax_totals, expected_values, soft_checking=soft_checking)

        # Full invoice.
        invoice = self._create_final_invoice(sale_order)
        self.assertRecordValues(invoice, [
            {'amount_total': original_amount_total - expected_values['total_amount_currency']},
        ])

    # -------------------------------------------------------------------------
    # GENERIC TAXES TEST SUITE
    # -------------------------------------------------------------------------

    def test_taxes_l10n_in_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_sale_order_document_down_payment(document, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_br_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_sale_order_document_down_payment(document, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_be_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_sale_order_document_down_payment(document, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_fixed_tax_last_position_sale_orders(self):
        for test_mode, document, amount_type, amount, expected_values in self._test_taxes_fixed_tax_last_position():
            with self.subTest(test_code=test_mode):
                self.assert_sale_order_document_down_payment(document, amount_type, amount, expected_values)

    def test_no_taxes_sale_orders(self):
        document, amount_type, amount, expected_values = self._test_no_taxes()
        self.assert_sale_order_document_down_payment(document, amount_type, amount, expected_values)

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

        so = self._create_sale_order(
            order_line=[
                self._prepare_order_line(
                    name=name,
                    product_id=product_id,
                    price_unit=price_unit,
                    discount=discount,
                    tax_ids=tax_ids,
                )
                for name, product_id, price_unit, discount, tax_ids in (
                    ('line_1', product_1, 2000.0, 50.0, None),  # Standalone line, no tax
                    ('line_2', product_1, 4000.0, 50.0, tax_15),  # These next 2 lines will be merged together because same account, same tax
                    ('line_3', product_2, 3000.0, None, tax_15),
                    ('line_4', product_3, 3000.0, None, tax_15),  # Line linked to the same tax as the ones above but doesn't have the same account
                    ('line_5', product_1, 5000.0, None, tax_10 + tax_15),  # Multiple taxes on the line. One tax detail will be squashed but not the other
                )
            ],
        )
        self.assertRecordValues(so, [{
            'amount_untaxed': 14000.0,
            'amount_tax': 2450.0,
            'amount_total': 16450.0,
        }])

        # Create a down payment invoice of 30%.
        dp_invoice = self._create_down_payment_invoice(so, 'percent', 30)
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
            {'name': down_payment_label,    'tax_ids': (tax_10 + tax_15).ids,       'price_subtotal': 0.0},
        ])

        dp_invoice.action_post()
        self.assertRecordValues(dp_invoice, [{
            'amount_untaxed': 4200.0,
            'amount_tax': 735.0,
            'amount_total': 4935.0,
        }])
        account_id = dp_invoice.company_id.downpayment_account_id.id
        self.assertRecordValues(dp_invoice.line_ids, [
            # Down payment product lines:
            {'account_id': account_id,    'tax_ids': [],                      'balance': -300.0},
            {'account_id': account_id,    'tax_ids': tax_15.ids,              'balance': -2400.0},
            {'account_id': account_id,    'tax_ids': (tax_10 + tax_15).ids,   'balance': -1500.0},
            # Tax 15%:
            {'account_id': tax_account.id,          'tax_ids': [],                      'balance': -585.0},
            # Tax 10%:
            {'account_id': tax_account.id,          'tax_ids': [],                      'balance': -150.0},
            # Receivable line:
            {'account_id': receivable.id,           'tax_ids': [],                      'balance': 4935.0},
        ])

        # Create the final invoice.
        final_invoice = self._create_final_invoice(so)

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
            {'account_id': account_id,              'tax_ids': [],                      'balance': 300.0},
            {'account_id': account_id,              'tax_ids': tax_15.ids,              'balance': 2400.0},
            {'account_id': account_id,              'tax_ids': (tax_10 + tax_15).ids,   'balance': 1500.0},
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

        so = self._create_sale_order_one_line(price_unit=1000.0, product_id=product, tax_ids=tax_15)

        self.assertRecordValues(so, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        }])

        # First down payment of 30% but remove the tax from the invoice.
        dp_invoice_1 = self._create_down_payment_invoice(so, 'percent', 30)
        dp_invoice_1.invoice_line_ids.tax_ids = [Command.clear()]
        dp_invoice_1.action_post()
        self.assertRecordValues(dp_invoice_1, [{
            'amount_untaxed': 300.0,
            'amount_tax': 0.0,
            'amount_total': 300.0,
        }])

        # Second down payment of 20%.
        dp_invoice_2 = self._create_down_payment_invoice(so, 'percent', 20)
        dp_invoice_2.action_post()
        self.assertRecordValues(dp_invoice_2, [{
            'amount_untaxed': 200.0,
            'amount_tax': 30.0,
            'amount_total': 230.0,
        }])

        # Create the final invoice.
        final_invoice = self._create_final_invoice(so)
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
            # Tax 15% - on account income account:
            {'tax_ids': [],                     'balance': -150.0},
            # Tax 15% - on downpayment account, we need to add the 30 we removed on dp_invoice_2:
            {'tax_ids': [],                     'balance': 30.0},
            # Receivable line:
            {'tax_ids': [],                     'balance': 620.0},
        ])

    def test_down_payment_invoice_foreign_currency_different_dates(self):
        product = self.company_data['product_order_cost']
        tax_15 = self.percent_tax(15.0)

        with freeze_time('2016-01-01'):
            self.foreign_currency_pricelist.currency_id = self.other_currency
            so = self._create_sale_order_one_line(
                price_unit=1200.0,
                product_id=product,
                tax_ids=tax_15,
                currency_id=self.other_currency.id,
                pricelist_id=self.foreign_currency_pricelist.id,
            )

        self.assertRecordValues(so, [{
            'amount_untaxed': 1200.0,
            'amount_tax': 180.0,
            'amount_total': 1380.0,
        }])

        # First down payment of 30% but remove the tax from the invoice.
        with freeze_time('2016-01-01'):
            dp_invoice = self._create_down_payment_invoice(so, 'percent', 30, post=True)

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
            final_invoice = self._create_final_invoice(so)

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
                {'tax_ids': [],                     'amount_currency': -180.0,      'balance': -90.0},
                # Tax 15%:
                {'tax_ids': [],                     'amount_currency': 54.0,        'balance': 27.0},
                # Receivable line:
                {'tax_ids': [],                     'amount_currency': 966.0,       'balance': 483.0},
            ])

    def test_down_payment_invoice_then_refunded_then_invoiced_again(self):
        product = self.company_data['product_order_cost']
        tax_15 = self.percent_tax(15.0)

        so = self._create_sale_order_one_line(name='line_1', product_id=product, price_unit=1000.0, tax_ids=tax_15)

        self.assertRecordValues(so, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        }])

        # First down payment of 30%.
        dp_invoice_1 = self._create_down_payment_invoice(so, 'percent', 30)

        draft_down_payment_label = f"Down Payment: {so.create_date.strftime('%m/%d/%Y')} (Draft)"
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                  'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",           'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': draft_down_payment_label,  'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        dp_invoice_1.action_post()
        self.assertRecordValues(dp_invoice_1, [{
            'amount_untaxed': 300.0,
            'amount_tax': 45.0,
            'amount_total': 345.0,
        }])

        down_payment_dp_invoice_1 = f"Down Payment (ref: {dp_invoice_1.name} on {dp_invoice_1.invoice_date.strftime('%m/%d/%Y')})"
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                      'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",               'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1,     'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        # Credit note on the down payment.
        self._reverse_invoice(dp_invoice_1, post=True)

        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                      'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",               'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1,     'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        # Second down payment of 50%.
        dp_invoice_2 = self._create_down_payment_invoice(so, 'percent', 50)
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                  'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",           'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1, 'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
            {'name': draft_down_payment_label,  'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        dp_invoice_2.action_post()
        self.assertRecordValues(dp_invoice_2, [{
            'amount_untaxed': 500.0,
            'amount_tax': 75.0,
            'amount_total': 575.0,
        }])

        down_payment_dp_invoice_2 = f"Down Payment (ref: {dp_invoice_2.name} on {dp_invoice_2.invoice_date.strftime('%m/%d/%Y')})"
        self.assertRecordValues(so.order_line, [
            {'name': 'line_1',                  'tax_ids': tax_15.ids,                  'price_subtotal': 1000.0},
            {'name': "Down Payments",           'tax_ids': [],                          'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_1, 'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
            {'name': down_payment_dp_invoice_2, 'tax_ids': tax_15.ids,                  'price_subtotal': 0.0},
        ])

        # Create the final invoice.
        final_invoice_1 = self._create_final_invoice(so, post=True)
        self.assertRecordValues(final_invoice_1, [{
            'amount_untaxed': so.amount_untaxed - dp_invoice_2.amount_untaxed,
            'amount_tax': so.amount_tax - dp_invoice_2.amount_tax,
            'amount_total': so.amount_total - dp_invoice_2.amount_total,
        }])

        # Credit note on the final invoice.
        self._reverse_invoice(final_invoice_1, post=True)

        # Create a new final invoice.
        final_invoice_2 = self._create_final_invoice(so, post=True)
        self.assertRecordValues(final_invoice_2, [{
            'amount_untaxed': so.amount_untaxed - dp_invoice_2.amount_untaxed,
            'amount_tax': so.amount_tax - dp_invoice_2.amount_tax,
            'amount_total': so.amount_total - dp_invoice_2.amount_total,
        }])

    @freeze_time('2018-01-01')
    def test_down_payment_100_first_then_0_final_invoice_round_per_line(self):
        self.env.company.tax_calculation_rounding_method = 'round_per_line'
        product = self.company_data['product_order_cost']
        tax_23 = self.percent_tax(23.0)
        other_currency = self.setup_other_currency('EUR', rates=[('2017-01-01', 1.2834)])
        self.foreign_currency_pricelist.currency_id = other_currency

        so = self._create_sale_order(
            currency_id=other_currency.id,
            pricelist_id=self.foreign_currency_pricelist.id,
            order_line=[
                self._prepare_order_line(
                    product_id=product,
                    price_unit=price_unit,
                    product_uom_qty=qty,
                    discount=discount,
                    tax_ids=tax_23,
                )
                for qty, price_unit, discount in (
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
        )
        self.assertRecordValues(so, [{
            'amount_untaxed': 1196.87,
            'amount_tax': 275.27,
            'amount_total': 1472.14,
        }])

        # Create a down payment invoice of 100%.
        dp_invoice = self._create_down_payment_invoice(so, 'percent', 100, post=True)
        self.assertRecordValues(dp_invoice, [{
            'amount_untaxed': 1196.87,
            'amount_tax': 275.27,
            'amount_total': 1472.14,
        }])
        self.assert_invoice_tax_totals_summary(dp_invoice, {
            'same_tax_base': True,
            'currency_id': other_currency.id,
            'company_currency_id': self.env.company.currency_id.id,
            'base_amount_currency': 1196.87,
            'base_amount': 932.57,
            'tax_amount_currency': 275.27,
            'tax_amount': 214.49,
            'total_amount_currency': 1472.14,
            'total_amount': 1147.06,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1196.87,
                    'base_amount': 932.57,
                    'tax_amount_currency': 275.27,
                    'tax_amount': 214.49,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 1196.87,
                            'base_amount': 932.57,
                            'tax_amount_currency': 275.27,
                            'tax_amount': 214.49,
                            'display_base_amount_currency': 1196.87,
                            'display_base_amount': 932.57,
                        },
                    ],
                },
            ],
        })

        # Create the final invoice.
        final_invoice = self._create_final_invoice(so)
        self.assertRecordValues(final_invoice, [{
            'amount_untaxed': 0.0,
            'amount_tax': 0.0,
            'amount_total': 0.0,
        }])
        self.assert_invoice_tax_totals_summary(final_invoice, {
            'same_tax_base': True,
            'currency_id': other_currency.id,
            'company_currency_id': self.env.company.currency_id.id,
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
            'total_amount_currency': 0.0,
            'total_amount': 0.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 0.0,
                    'base_amount': 0.0,
                    'tax_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 0.0,
                            'base_amount': 0.0,
                            'tax_amount_currency': 0.0,
                            'tax_amount': 0.0,
                            'display_base_amount_currency': 0.0,
                            'display_base_amount': 0.0,
                        },
                    ],
                },
            ],
        })

    @freeze_time('2018-01-01')
    def test_down_payment_100_first_then_0_final_invoice_round_globally(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        product = self.company_data['product_order_cost']
        tax_23 = self.percent_tax(23.0)
        other_currency = self.setup_other_currency('EUR', rates=[('2017-01-01', 1.2834)])
        self.foreign_currency_pricelist.currency_id = other_currency

        so = self._create_sale_order(
            currency_id=other_currency.id,
            pricelist_id=self.foreign_currency_pricelist.id,
            order_line=[
                self._prepare_order_line(
                    product_id=product,
                    price_unit=price_unit,
                    product_uom_qty=qty,
                    discount=discount,
                    tax_ids=tax_23,
                )
                for qty, price_unit, discount in (
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
        )
        self.assertRecordValues(so, [{
            'amount_untaxed': 1196.89,
            'amount_tax': 275.28,
            'amount_total': 1472.17,
        }])

        # Create a down payment invoice of 100%.
        dp_invoice = self._create_down_payment_invoice(so, 'percent', 100, post=True)
        self.assertRecordValues(dp_invoice, [{
            'amount_untaxed': 1196.89,
            'amount_tax': 275.28,
            'amount_total': 1472.17,
        }])
        self.assert_invoice_tax_totals_summary(dp_invoice, {
            'same_tax_base': True,
            'currency_id': other_currency.id,
            'company_currency_id': self.env.company.currency_id.id,
            'base_amount_currency': 1196.89,
            'base_amount': 932.59,
            'tax_amount_currency': 275.28,
            'tax_amount': 214.5,
            'total_amount_currency': 1472.17,
            'total_amount': 1147.09,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1196.89,
                    'base_amount': 932.59,
                    'tax_amount_currency': 275.28,
                    'tax_amount': 214.5,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 1196.89,
                            'base_amount': 932.59,
                            'tax_amount_currency': 275.28,
                            'tax_amount': 214.5,
                            'display_base_amount_currency': 1196.89,
                            'display_base_amount': 932.59,
                        },
                    ],
                },
            ],
        })

        # Create the final invoice.
        final_invoice = self._create_final_invoice(so)
        self.assertRecordValues(final_invoice, [{
            'amount_untaxed': 0.0,
            'amount_tax': 0.0,
            'amount_total': 0.0,
        }])
        self.assert_invoice_tax_totals_summary(final_invoice, {
            'same_tax_base': True,
            'currency_id': other_currency.id,
            'company_currency_id': self.env.company.currency_id.id,
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
            'total_amount_currency': 0.0,
            'total_amount': 0.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 0.0,
                    'base_amount': 0.0,
                    'tax_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 0.0,
                            'base_amount': 0.0,
                            'tax_amount_currency': 0.0,
                            'tax_amount': 0.0,
                            'display_base_amount_currency': 0.0,
                            'display_base_amount': 0.0,
                        },
                    ],
                },
            ],
        })

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

        so = self._create_sale_order(
            order_line=[
                self._prepare_order_line(
                    product_id=product,
                    price_unit=price_unit,
                    tax_ids=tax,
                    analytic_distribution=analytic_distribution,
                )
                for price_unit, tax, analytic_distribution in (
                    (1000, tax_15, {an_acc_1: 100.0}),
                    (2000, tax_15, {an_acc_1: 50.0, an_acc_2: 50.0}),
                    (1000, tax_10, {an_acc_2: 100.0}),
                    (2000, tax_10, {an_acc_1: 125.0, an_acc_2: -25.0}),
                    (2000, tax_20, {an_acc_1: 75.0, an_acc_2: 25.0}),
                    (-2000, tax_20, {an_acc_1: 25.0, an_acc_2: 75.0}),
                )
            ],
        )
        self.assertRecordValues(so, [{
            'amount_untaxed': 6000.0,
            'amount_tax': 750.0,
            'amount_total': 6750.0,
        }])

        dp_invoice = self._create_down_payment_invoice(so, 'percent', 50, post=True)
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

    def test_downpayment_invoice_lines_with_down_payment_account(self):
        # Make a sale order with multiple lines. Total amount of sale order is equal to 1680$
        sale_order = self._create_sale_order(
            order_line=[
                self._prepare_order_line(product_id=product, product_uom_qty=qty)
                for qty, product in (
                    (1, self.company_data['product_order_no']),
                    (2, self.company_data['product_order_sales_price']),
                    (3, self.company_data['product_order_cost']),
                )
            ],
        )
        # Make a down payment of 50%
        invoice = self._create_down_payment_invoice(sale_order, 'percent', 50)
        # Make sure we only have one line and we don't split into multiple lines
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids.account_id.id, self.company_data['company'].downpayment_account_id.id)
        # We should have half the amount of the Sale Order -> 840$
        self.assertEqual(invoice.amount_total, 840)

    def test_down_payment_with_global_discount(self):
        """ This test checks that the down payment invoice lines are
        correctly computed when a global discount is applied to the sale order.

        Test data:
        - A single sale order line with a 14,990.00 price and a 0% tax.
        - A global discount of 990.00 is applied to the sale order.
        - A down payment invoice of 1,000.00 is created.

        Assert that the down payment invoice has one line with price_unit 1070.71
        and one line with price_unit -70.71.

        Since in saas-18.4 there is no longer the possibility to split the down payment lines
        into multiple down payment accounts, we assert the result of `_prepare_down_payment_lines`
        after passing a grouping_function that creates two different down payment lines
        """
        self.env.company.downpayment_account_id = self.company_data['default_account_assets']
        product = self.company_data['product_order_cost']
        tax_0 = self.percent_tax(0.0)

        so = self._create_sale_order_one_line(product_id=product, price_unit=14990.00, tax_ids=tax_0)
        self.assertRecordValues(so, [{
            'amount_untaxed': 14990.00,
            'amount_tax': 0.0,
            'amount_total': 14990.00,
        }])

        # Put a discount of 990.00 on the sale order.
        self._apply_sale_order_discount(so, 'fixed', 990.00)

        # Create a down payment invoice for 1,000.00.
        self._create_down_payment_invoice(so, 'fixed', 1000.00)

        so_base_lines = [
            order_line._prepare_base_line_for_taxes_computation()
            for order_line in so.order_line
        ]
        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(so_base_lines, self.env.company)
        AccountTax._round_base_lines_tax_details(so_base_lines, self.env.company)

        dp_lines = AccountTax._prepare_down_payment_lines(
            base_lines=so_base_lines,
            company=self.env.company,
            amount_type='fixed',
            amount=1000.00,
            # Group the product and global discount separately.
            grouping_function=lambda line: {
                'special_type': line['special_type'],
            },
        )

        self.assertAlmostEqual(dp_lines[0]['price_unit'], 1070.71, 2)
        self.assertAlmostEqual(dp_lines[1]['price_unit'], -70.71, 2)
