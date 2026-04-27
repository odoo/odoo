from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTaxesTaxTotalsSummaryL10nItPos(TestTaxCommonPOS, TestTaxesTaxTotalsSummary):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('it')
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.it_fiscal_printer_ip = "0.0.0.0"

    def _jsonify_document_line(self, document, index, line):
        # EXTENDS 'account'
        values = super()._jsonify_document_line(document, index, line)
        values['l10n_it_epson_printer'] = line['l10n_it_epson_printer']
        return values

    def _test_taxes_l10n_it_epson_printer(self):
        tax = self.percent_tax(22.0, price_include_override='tax_excluded', tax_group_id=self.tax_groups[0].id)
        document_params = self.init_document(
            lines=[
                {'price_unit': 5.16, 'quantity': 3.0, 'tax_ids': tax, 'l10n_it_epson_printer': True},
            ],
        )
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 15.49,
            'tax_amount_currency': 3.41,
            'total_amount_currency': 18.9,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 15.49,
                    'tax_amount_currency': 3.41,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 15.49,
                            'tax_amount_currency': 3.41,
                            'display_base_amount_currency': 15.49,
                        },
                    ],
                },
            ],
        }
        yield 1, self.populate_document(document_params), expected_values

        document_params = self.init_document(
            lines=[
                {'price_unit': 2.20, 'quantity': 3.0, 'tax_ids': tax, 'l10n_it_epson_printer': True},
            ],
        )
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 6.59,
            'tax_amount_currency': 1.45,
            'total_amount_currency': 8.04,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 6.59,
                    'tax_amount_currency': 1.45,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 6.59,
                            'tax_amount_currency': 1.45,
                            'display_base_amount_currency': 6.59,
                        },
                    ],
                },
            ],
        }
        yield 2, self.populate_document(document_params), expected_values

        document_params = self.init_document(
            lines=[
                {'price_unit': 5.16, 'quantity': 3.0, 'tax_ids': tax, 'l10n_it_epson_printer': True},
                {'price_unit': 2.20, 'quantity': 3.0, 'tax_ids': tax, 'l10n_it_epson_printer': True},
            ],
        )
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 22.08,
            'tax_amount_currency': 4.86,
            'total_amount_currency': 26.94,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 22.08,
                    'tax_amount_currency': 4.86,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 22.08,
                            'tax_amount_currency': 4.86,
                            'display_base_amount_currency': 22.08,
                        },
                    ],
                },
            ],
        }
        yield 3, self.populate_document(document_params), expected_values

        document_params = self.init_document(
            lines=[
                {'price_unit': 50, 'quantity': 1.0, 'discount': 50.0, 'tax_ids': tax, 'l10n_it_epson_printer': True},
            ],
        )
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 25.00,
            'tax_amount_currency': 5.50,
            'total_amount_currency': 30.50,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 25.00,
                    'tax_amount_currency': 5.50,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 25.00,
                            'tax_amount_currency': 5.50,
                            'display_base_amount_currency': 25.00,
                        },
                    ],
                },
            ],
        }
        yield 4, self.populate_document(document_params), expected_values

    def test_taxes_l10n_it_epson_printer_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_it_epson_printer():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_it_epson_printer_pos(self):
        tests = self._test_taxes_l10n_it_epson_printer()
        test1 = next(tests)
        self.ensure_products_on_document(test1[1], 'product_1')
        test2 = next(tests)
        self.ensure_products_on_document(test2[1], 'product_2')
        test3 = next(tests)
        self.ensure_products_on_document(test3[1], 'product_3')
        test4 = next(tests)
        self.ensure_products_on_document(test4[1], 'product_4')
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_taxes_l10n_it_epson_printer_pos')
            orders = self.env['pos.order'].search([('session_id', '=', session.id)])
            for order, (test_index, document, expected_values) in zip(orders, tests):
                self.assert_pos_order_totals(order, expected_values)
                if order.account_move:
                    self.assert_invoice_totals(order.account_move, expected_values)
