from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericLocalization(TestPointOfSaleHttpCommon):
    allow_inherited_tests_method = True

    def setUp(self):
        super().setUp()
        self.genericTourName = 'generic_localization_tour'
        self.test_product_1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'type': 'consu',
            'list_price': 10.0,
            'categ_id': self.env.ref('product.product_category_all').id,
            'available_in_pos': True,
            'taxes_id': [Command.set(self.tax_sale_a.ids)],
            'standard_price': 5.0,
        })
        self.test_product_2 = self.env['product.product'].create({
            'name': 'Test Product 2',
            'type': 'consu',
            'list_price': 20.0,
            'categ_id': self.env.ref('product.product_category_all').id,
            'available_in_pos': True,
            'taxes_id': [Command.set(self.tax_sale_a.ids)],
            'standard_price': 15.0,
        })

    def test_generic_localization(self):
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id
        self.start_pos_tour(self.genericTourName, login="accountman")
        self.assertEqual(current_session.state, 'closed')
