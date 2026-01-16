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

    def test_pos_global_discount_sell_and_refund(self):
        self.desk_pad.standard_price = 1.0
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_pos_global_discount_sell_and_refund')
        orders = self.main_pos_config.current_session_id.order_ids
        self.assertEqual(len(orders), 2)
        refund_order = orders[0]
        self.assertAlmostEqual(refund_order.amount_total, -2.85)
        self.assertEqual(len(refund_order.lines), 2)
        self.assertEqual(refund_order.lines[1].product_id.id, self.main_pos_config.discount_product_id.id)
        self.assertAlmostEqual(refund_order.lines[1].price_subtotal_incl, -0.15)
        self.assertAlmostEqual(refund_order.lines[0].margin, -2.0)
        self.assertAlmostEqual(refund_order.lines[0].margin_percent, 0.6667)
        self.assertAlmostEqual(refund_order.margin, -1.85)
        self.assertAlmostEqual(refund_order.margin_percent, 0.6491)
        pos_order = orders[1]
        self.assertAlmostEqual(pos_order.amount_total, 2.85)
        self.assertEqual(len(pos_order.lines), 2)
        self.assertEqual(pos_order.lines[1].product_id.id, self.main_pos_config.discount_product_id.id)
        self.assertAlmostEqual(pos_order.lines[1].price_subtotal_incl, -0.15)
        self.assertAlmostEqual(pos_order.lines[0].margin, 2.0)
        self.assertAlmostEqual(pos_order.lines[0].margin_percent, 0.6667)
        self.assertAlmostEqual(pos_order.margin, 1.85)
        self.assertAlmostEqual(pos_order.margin_percent, 0.6491)
