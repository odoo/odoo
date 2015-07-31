# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.mrp.tests.test_order_demo import TestOrderDemo


class TestOrderProcess(TestOrderDemo):

    def test_00_order_process(self):

    # I compute the production order.
        self.mrp_production_test1.action_compute()

    # I check production lines after compute.
        self.assertEqual(len(self.mrp_production_test1.product_lines), 5, "Production lines are not generated proper.")


    # from openerp.tools import float_compare
    # def assert_equals(value1, value2, msg, float_compare=float_compare):
    #     assert float_compare(value1, value2, precision_digits=2) == 0, msg
    # order = self.browse(cr, uid, ref("mrp_production_test1"), context=context)
    # assert len(order.workcenter_lines), "Workcenter lines are not generated proper."

    # # Now I check workcenter lines.

    # from openerp.tools import float_compare

    # def assert_equals(value1, value2, msg, float_compare=float_compare):
    #     assert float_compare(value1, value2, precision_digits=2) == 0, msg
    # self.assertTrue(len(self.mrp_production_test1.workcenter_lines), "Workcenter lines are not generated proper.")
