from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesGlobalDiscountPOS(TestTaxCommonPOS):

    _test_user_groups = None  # FIXME list needed groups

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
