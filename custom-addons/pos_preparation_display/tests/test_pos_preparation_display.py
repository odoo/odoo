# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosPreparationDisplay(TestPoSCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.config = cls.basic_config

    def test_correct_amount_preparation_display_lines(self):
        self.open_new_session()

        order = self.create_ui_order_data([(self.product_a, 1), (self.product_a, 1)])
        ref = self.env['pos.order'].create_from_ui([order])[0]['pos_reference']

        prep_line = self.env['pos_preparation_display.orderline'].search([
            ('preparation_display_order_id.pos_order_id.pos_reference', '=', ref),
        ])
        self.assertEqual(prep_line.product_quantity, 2)
