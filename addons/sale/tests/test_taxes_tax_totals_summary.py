from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.addons.sale.tests.common import TestTaxCommonSale
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesTaxTotalsSummarySale(TestTaxCommonSale, TestTaxesTaxTotalsSummary):

    def test_taxes_l10n_in_sale_orders(self):
        for test_index, document, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_taxes_l10n_br_sale_orders(self):
        for test_index, document, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_taxes_l10n_be_sale_orders(self):
        for test_index, document, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_taxes_l10n_mx_sale_orders(self):
        for test_index, document, expected_values in self._test_taxes_l10n_mx():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_taxes_l10n_pt_sale_orders(self):
        for test_index, document, expected_values in self._test_taxes_l10n_pt():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_reverse_charge_taxes_1_generic_helpers(self):
        for document, expected_values in self._test_reverse_charge_taxes_1():
            sale_order = self.convert_document_to_sale_order(document)
            self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_reverse_charge_taxes_2_generic_helpers(self):
        for document, expected_values in self._test_reverse_charge_taxes_2():
            sale_order = self.convert_document_to_sale_order(document)
            self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_mixed_combined_standalone_taxes_sale_orders(self):
        for test_index, document, expected_values in self._test_mixed_combined_standalone_taxes():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_preceding_subtotal_sale_orders(self):
        for test_index, document, expected_values in self._test_preceding_subtotal():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_preceding_subtotal_with_tax_group_sale_orders(self):
        for test_index, document, expected_values in self._test_preceding_subtotal_with_tax_group():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_preceding_subtotal_with_include_base_amount_sale_orders(self):
        document, expected_values = self._test_preceding_subtotal_with_include_base_amount()
        sale_order = self.convert_document_to_sale_order(document)
        self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_reverse_charge_percent_tax_sale_orders(self):
        for test_index, document, expected_values in self._test_reverse_charge_percent_tax():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)
                self.assertRecordValues(sale_order.order_line, [{
                    'price_subtotal': expected_values['total_amount_currency'],
                    'price_total': expected_values['total_amount_currency'],
                }])

    def test_reverse_charge_division_tax_sale_orders(self):
        for test_index, document, expected_values in self._test_reverse_charge_division_tax():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)
                self.assertRecordValues(sale_order.order_line, [{
                    'price_subtotal': expected_values['total_amount_currency'],
                    'price_total': expected_values['total_amount_currency'],
                }])

    def test_discount_with_round_globally_sale_orders(self):
        for test_index, document, expected_values in self._test_discount_with_round_globally():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)

    def test_apply_mixed_epd_discount(self):
        """
        When applying an epd - mixed payment term, the tax should be computed based on the discounted untaxed amount.
        """
        tax_a = self.percent_tax(15.0)
        early_payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 20,
                }),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'payment_term_id': early_payment_term.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 100,
                    'tax_id': [Command.set(tax_a.ids)],
                }),
            ],
        })
        self.assert_sale_order_tax_totals_summary(
            sale_order,
            {
                'base_amount_currency': 100.0,
                'tax_amount_currency': 13.5,
                'total_amount_currency': 113.5,
            },
            soft_checking=True,
        )

    def test_apply_mixed_epd_discount_fixed_tax(self):
        """
        When applying an epd - mixed payment term, the fixed tax amount should be the same.
        """
        tax_a = self.fixed_tax(20.0)
        early_payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 20,
                }),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'payment_term_id': early_payment_term.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 100,
                    'tax_id': [Command.set(tax_a.ids)],
                }),
            ],
        })
        self.assert_sale_order_tax_totals_summary(
            sale_order,
            {
                'base_amount_currency': 100.0,
                'tax_amount_currency': 20.0,
                'total_amount_currency': 120.0,
            },
            soft_checking=True,
        )

    def test_apply_mixed_epd_discount_percent_and_fixed_tax(self):
        """
        When applying an epd - mixed payment term, the percent tax should be computed based on the discounted untaxed amount.
        """
        tax_a = self.percent_tax(15.0)
        tax_b = self.fixed_tax(20.0)
        early_payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 20,
                }),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'payment_term_id': early_payment_term.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 100,
                    'tax_id': [Command.set((tax_a + tax_b).ids)],
                }),
            ],
        })
        self.assert_sale_order_tax_totals_summary(
            sale_order,
            {
                'base_amount_currency': 100.0,
                'tax_amount_currency': 33.5,
                'total_amount_currency': 133.5,
            },
            soft_checking=True,
        )
