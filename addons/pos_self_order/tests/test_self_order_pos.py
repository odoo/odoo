# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderPos(TestPointOfSaleHttpCommon):

    def test_table_stand_number_exported(self):
        """
        Tests that even after being modified in the PoS, an
        order's table_stand_number is not deleted or altered
        """

        self.main_pos_config.open_ui()

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product_a.id,
                'price_unit': 1000,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 1000,
                'price_subtotal_incl': 1000,
            })],
            'pricelist_id': self.main_pos_config.pricelist_id.id,
            'amount_paid': 0.0,
            'amount_total': 1000.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'table_stand_number': 9,
            'pos_reference': 'POS/12345678901234',
        })
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, "test_table_stand_number_exported", login="pos_user")
        self.assertEqual(order.table_stand_number, '9')
