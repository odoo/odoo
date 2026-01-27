# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.test_product_attribute_value_config import (
    TestProductAttributeValueCommon,
)
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductWarehouse(
    TestProductAttributeValueCommon, WebsiteSaleStockCommon, HttpCase,
):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set two warehouses (one was created on company creation)
        cls.warehouse_1 = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.company.id)
        ])
        cls.warehouse_2 = cls._create_warehouse()
        cls.product_A = cls._create_product()
        cls.product_B = cls._create_product()

        # Add 10 Product A in WH1 and 15 Product 1 in WH2
        cls._add_product_qty_to_wh(cls.product_A.id, 10, cls.warehouse_1.lot_stock_id.id)
        cls._add_product_qty_to_wh(cls.product_A.id, 15, cls.warehouse_2.lot_stock_id.id)

        # Add 10 Product 2 in WH2
        cls._add_product_qty_to_wh(cls.product_B.id, 10, cls.warehouse_2.lot_stock_id.id)

    def test_get_combination_info_free_qty_when_warehouse_is_set(self):
        self.website.warehouse_id = self.warehouse_2
        combination_info = self.make_jsonrpc_request(
            "/website_sale/get_combination_info",
            {
                'product_template_id': self.product_A.product_tmpl_id.id,
                'product_id': None,
                'combination': [],
                'add_qty': 1,
            },
        )
        self.assertEqual(combination_info['free_qty'], 15)
        combination_info = self.make_jsonrpc_request(
            "/website_sale/get_combination_info",
            {
                'product_template_id': self.product_B.product_tmpl_id.id,
                'product_id': None,
                'combination': [],
                'add_qty': 1,
            },
        )
        self.assertEqual(combination_info['free_qty'], 10)

    def test_get_combination_info_free_qty_when_no_warehouse_is_set(self):
        self.website.warehouse_id = False
        combination_info = self.make_jsonrpc_request(
            "/website_sale/get_combination_info",
            {
                'product_template_id': self.product_A.product_tmpl_id.id,
                'product_id': None,
                'combination': [],
                'add_qty': 1,
            },
        )
        self.assertEqual(combination_info['free_qty'], 25)
        combination_info = self.make_jsonrpc_request(
            "/website_sale/get_combination_info",
            {
                'product_template_id': self.product_B.product_tmpl_id.id,
                'product_id': None,
                'combination': [],
                'add_qty': 1,
            },
        )
        self.assertEqual(combination_info['free_qty'], 10)

    def test_02_update_cart_with_multi_warehouses(self):
        """ When the user updates his cart and increases a product quantity, if
        this quantity is not available in the SO's warehouse, a warning should
        be returned and the quantity updated to its maximum. """

        so = self.env['sale.order'].create({
            'website_id': self.website.id,
            'partner_id': self.env.user.partner_id.id,
            'order_line': [(0, 0, {
                'name': self.product_A.name,
                'product_id': self.product_A.id,
                'product_uom_qty': 5,
                'price_unit': self.product_A.list_price,
            })]
        })

        with self.mock_request(sale_order_id=so.id) as req:
            website_so = req.cart
            self.assertEqual(website_so, so)
            self.assertEqual(
                website_so.order_line.product_id.virtual_available,
                25,
                "This quantity should be based on all warehouses.",
            )

            values = so._cart_update_line_quantity(line_id=so.order_line.id, quantity=30)
            self.assertTrue(values.get('warning', False))
            self.assertEqual(values.get('quantity'), 25)
