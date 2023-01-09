# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tools import MockRequest
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductWarehouse(TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Run the tests in another company, so the tests do not rely on the
        # database state (eg the default company's warehouse)
        cls.company = cls.env['res.company'].create({'name': 'Company C'})
        cls.env.user.company_id = cls.company
        cls.website = cls.env['website'].create({'name': 'Website Company C'})
        cls.website.company_id = cls.company

            # Set two warehouses (one was created on company creation)
        cls.warehouse_1 = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)])
        cls.warehouse_2 = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 2',
            'code': 'WH2'
        })

        # Create two stockable products
        cls.product_A = cls.env['product.product'].create({
            'name': 'Product A',
            'allow_out_of_stock_order': False,
            'type': 'product',
            'default_code': 'E-COM1',
        })

        cls.product_B = cls.env['product.product'].create({
            'name': 'Product B',
            'allow_out_of_stock_order': False,
            'type': 'product',
            'default_code': 'E-COM2',
        })

        # Add 10 Product A in WH1 and 15 Product 1 in WH2
        quants = cls.env['stock.quant'].with_context(inventory_mode=True).create([{
            'product_id': cls.product_A.id,
            'inventory_quantity': qty,
            'location_id': wh.lot_stock_id.id,
        } for wh, qty in [(cls.warehouse_1, 10.0), (cls.warehouse_2, 15.0)]])

        # Add 10 Product 2 in WH2
        quants |= cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.product_B.id,
            'inventory_quantity': 10.0,
            'location_id': cls.warehouse_2.lot_stock_id.id,
        })
        quants.action_apply_inventory()

    def test_01_get_combination_info(self):
        """ Checked that correct product quantity is shown in website according
        to the warehouse which is set in current website.
          - Set Warehouse 1, Warehouse 2 or none in website and:
            - Check available quantity of Product A and Product B in website
        When the user doesn't set any warehouse, the module should still select
        a default one.
        """

        for wh, qty_a, qty_b in [(self.warehouse_1, 10, 0), (self.warehouse_2, 15, 10), (False, 10, 0)]:
            # set warehouse_id
            self.website.warehouse_id = wh

            product = self.product_A.with_context(website_id=self.website.id)
            combination_info = product.product_tmpl_id.with_context(website_sale_stock_get_quantity=True)._get_combination_info()

            # Check available quantity of product is according to warehouse
            self.assertEqual(combination_info['free_qty'], qty_a, "%s units of Product A should be available in warehouse %s" % (qty_a, wh))

            product = self.product_B.with_context(website_id=self.website.id)
            combination_info = product.product_tmpl_id.with_context(website_sale_stock_get_quantity=True)._get_combination_info()

            # Check available quantity of product is according to warehouse
            self.assertEqual(combination_info['free_qty'], qty_b, "%s units of Product B should be available in warehouse %s" % (qty_b, wh))

    def test_02_update_cart_with_multi_warehouses(self):
        """ When the user updates his cart and increases a product quantity, if
        this quantity is not available in the SO's warehouse, a warning should
        be returned and the quantity updated to its maximum. """

        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'order_line': [(0, 0, {
                'name': self.product_A.name,
                'product_id': self.product_A.id,
                'product_uom_qty': 5,
                'product_uom': self.product_A.uom_id.id,
                'price_unit': self.product_A.list_price,
            })]
        })

        with MockRequest(self.env, website=self.website, sale_order_id=so.id):
            website_so = self.website.sale_get_order()
            self.assertEqual(website_so.order_line.product_id.virtual_available, 10, "This quantity should be based on SO's warehouse")

            values = so._cart_update(product_id=self.product_A.id, line_id=so.order_line.id, set_qty=20)
            self.assertTrue(values.get('warning', False))
            self.assertEqual(values.get('quantity'), 10)
