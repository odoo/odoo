from odoo import Command
from odoo.addons.account.tests.test_taxes_downpayment import TestTaxesDownPayment
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.addons.sale.tests.common import TestTaxCommonSale
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesDownPaymentPOS(TestTaxCommonPOS, TestTaxCommonSale, TestTaxesDownPayment):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.down_payment_product_id = cls.env['product.product'].create({
            'name': 'downpayment',
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(cls.pos_desk_misc_test.ids)],
        })
        cls.main_pos_config.pricelist_id = None
        cls.main_pos_config.available_pricelist_ids = [Command.clear()]

    def assert_pos_orders_and_invoices(self, tour, tests_with_orders):
        all_so = self.env['sale.order']
        for _test_code, document, _soft_checking, _amount_type, _amount, _expected_values in tests_with_orders:
            so = self.convert_document_to_sale_order(document)
            so.currency_id = self.env.company.currency_id  # No foreign currency in the POS
            so.action_confirm()
            all_so += so
        super().assert_pos_orders_and_invoices(tour, tests_with_orders)
        all_so.action_cancel()

    def test_taxes_l10n_in_pos(self):
        tests = self._test_taxes_l10n_in()
        round_per_line_excluded_tests = [next(tests) for _i in range(22)]
        self.ensure_products_on_document(round_per_line_excluded_tests[0][1], 'product_1')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_downpayment_round_per_line_price_excluded', [
            round_per_line_excluded_tests[19],
            round_per_line_excluded_tests[18],
            round_per_line_excluded_tests[7],
            round_per_line_excluded_tests[6],
            round_per_line_excluded_tests[1],
            round_per_line_excluded_tests[0],
        ])

        round_globally_excluded_tests = [next(tests) for _i in range(22)]
        self.ensure_products_on_document(round_globally_excluded_tests[0][1], 'product_2')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_downpayment_round_globally_price_excluded', [
            round_globally_excluded_tests[19],
            round_globally_excluded_tests[18],
            round_globally_excluded_tests[7],
            round_globally_excluded_tests[6],
            round_globally_excluded_tests[1],
            round_globally_excluded_tests[0],
        ])

        round_per_line_included_tests = [next(tests) for _i in range(22)]
        self.ensure_products_on_document(round_per_line_included_tests[0][1], 'product_3')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_downpayment_round_per_line_price_included', [
            round_per_line_included_tests[19],
            round_per_line_included_tests[18],
            round_per_line_included_tests[7],
            round_per_line_included_tests[6],
            round_per_line_included_tests[1],
            round_per_line_included_tests[0],
        ])

        round_globally_included_tests = [next(tests) for _i in range(22)]
        self.ensure_products_on_document(round_globally_included_tests[0][1], 'product_4')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_downpayment_round_globally_price_included', [
            round_globally_included_tests[19],
            round_globally_included_tests[18],
            round_globally_included_tests[7],
            round_globally_included_tests[6],
            round_globally_included_tests[1],
            round_globally_included_tests[0],
        ])

    def test_taxes_l10n_br_pos(self):
        tests = self._test_taxes_l10n_br()
        round_per_line_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_excluded_tests[0][1], 'product_1')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_downpayment_round_per_line_price_excluded', [
            round_per_line_excluded_tests[0],
        ])

        round_globally_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_excluded_tests[0][1], 'product_2')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_downpayment_round_globally_price_excluded', [
            round_globally_excluded_tests[0],
        ])

        round_per_line_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_included_tests[0][1], 'product_3')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_downpayment_round_per_line_price_included', [
            round_per_line_included_tests[0],
        ])

        round_globally_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_included_tests[0][1], 'product_4')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_downpayment_round_globally_price_included', [
            round_globally_included_tests[0],
        ])

    def test_taxes_l10n_be_pos(self):
        tests = self._test_taxes_l10n_be()
        round_per_line_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_excluded_tests[0][1], 'product_1')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_downpayment_round_per_line_price_excluded', [
            round_per_line_excluded_tests[0],
        ])

        round_globally_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_excluded_tests[0][1], 'product_2')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_downpayment_round_globally_price_excluded', [
            round_globally_excluded_tests[0],
        ])

        round_per_line_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_included_tests[0][1], 'product_3')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_downpayment_round_per_line_price_included', [
            round_per_line_included_tests[0],
        ])

        round_globally_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_included_tests[0][1], 'product_4')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_downpayment_round_globally_price_included', [
            round_globally_included_tests[0],
        ])
