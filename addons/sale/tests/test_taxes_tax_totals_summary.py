from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.addons.sale.tests.common import TestTaxCommonSale
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

    def test_reverse_charge_percent_tax_sale_orders(self):
        for test_index, document, expected_values in self._test_reverse_charge_percent_tax():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)
                self.assertRecordValues(sale_order.order_line, [{
                    'price_subtotal': 100.0,
                    'price_total': 100.0,
                }])

    def test_reverse_charge_division_tax_sale_orders(self):
        for test_index, document, expected_values in self._test_reverse_charge_division_tax():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)
                self.assertRecordValues(sale_order.order_line, [{
                    'price_subtotal': 79.0,
                    'price_total': 79.0,
                }])

    def test_discount_with_round_globally_sale_orders(self):
        for test_index, document, expected_values in self._test_discount_with_round_globally():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)
