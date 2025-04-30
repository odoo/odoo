from odoo import Command
from odoo.addons.account.tests.test_taxes_global_discount import TestTaxesGlobalDiscount
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesGlobalDiscountPOS(TestTaxCommonPOS, TestTaxesGlobalDiscount):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.iface_discount = True
        cls.main_pos_config.module_pos_discount = True
        cls.main_pos_config.discount_product_id = cls.env['product.product'].create({
            'name': 'discount',
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(cls.pos_desk_misc_test.ids)],
        })

    def test_taxes_l10n_in_pos(self):
        tests = self._test_taxes_l10n_in()
        round_per_line_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_excluded_tests[0][1], 'product_1')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_global_discount_round_per_line_price_excluded', [
            round_per_line_excluded_tests[16],
            round_per_line_excluded_tests[5],
            round_per_line_excluded_tests[0],
        ])

        round_globally_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_excluded_tests[0][1], 'product_2')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_global_discount_round_globally_price_excluded', [
            round_globally_excluded_tests[16],
            round_globally_excluded_tests[5],
            round_globally_excluded_tests[0],
        ])

        round_per_line_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_included_tests[0][1], 'product_3')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_global_discount_round_per_line_price_included', [
            round_per_line_included_tests[16],
            round_per_line_included_tests[5],
            round_per_line_included_tests[0],
        ])

        round_globally_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_included_tests[0][1], 'product_4')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_in_pos_global_discount_round_globally_price_included', [
            round_globally_included_tests[16],
            round_globally_included_tests[5],
            round_globally_included_tests[0],
        ])

    def test_taxes_l10n_br_pos(self):
        tests = self._test_taxes_l10n_br()
        round_per_line_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_excluded_tests[0][1], 'product_1')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_global_discount_round_per_line_price_excluded', [
            round_per_line_excluded_tests[0],
        ])

        round_globally_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_excluded_tests[0][1], 'product_2')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_global_discount_round_globally_price_excluded', [
            round_globally_excluded_tests[0],
        ])

        round_per_line_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_included_tests[0][1], 'product_3')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_global_discount_round_per_line_price_included', [
            round_per_line_included_tests[0],
        ])

        round_globally_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_included_tests[0][1], 'product_4')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_br_pos_global_discount_round_globally_price_included', [
            round_globally_included_tests[0],
        ])

    def test_taxes_l10n_be_pos(self):
        tests = self._test_taxes_l10n_be()
        round_per_line_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_excluded_tests[0][1], 'product_1')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_global_discount_round_per_line_price_excluded', [
            round_per_line_excluded_tests[0],
        ])

        round_globally_excluded_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_excluded_tests[0][1], 'product_2')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_global_discount_round_globally_price_excluded', [
            round_globally_excluded_tests[0],
        ])

        round_per_line_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_per_line_included_tests[0][1], 'product_3')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_global_discount_round_per_line_price_included', [
            round_per_line_included_tests[0],
        ])

        round_globally_included_tests = [next(tests) for _i in range(19)]
        self.ensure_products_on_document(round_globally_included_tests[0][1], 'product_4')
        self.assert_pos_orders_and_invoices('test_taxes_l10n_be_pos_global_discount_round_globally_price_included', [
            round_globally_included_tests[0],
        ])
