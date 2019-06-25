# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.tests.test_website_sale_product_attribute_value_config import TestWebsiteSaleProductAttributeValueConfig


class TestWebsiteSaleStockProductWarehouse(TestWebsiteSaleProductAttributeValueConfig):

    def test_get_combination_info(self):
        """ Checked that correct product quantity is shown in website according to the warehouse
        which is set in current website.
            - Create two warehouse
            - Create two stockable products
            - Update quantity of Product A in Warehouse 1
            - Update quantity of Product B in Warehouse 2
            - Set Warehouse 1 in website
            - Check available quantity of Product A and Product B in website
        Product A should be available in the website as it is available in warehouse 1 but Product B
        should not be available in website as it is stored in warehouse 2.
        """
        # Create two warehouses
        warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 1',
            'code': 'WH1'
        })
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 2',
            'code': 'WH2'
        })

        # Create two stockable products
        product_1 = self.env['product.product'].create({
            'name': 'Product A',
            'inventory_availability': 'always',
            'type': 'product',
            'default_code': 'E-COM1',
        })

        product_2 = self.env['product.product'].create({
            'name': 'Product B',
            'inventory_availability': 'always',
            'type': 'product',
            'default_code': 'E-COM2',
        })

        # Update quantity of Product A in Warehouse 1
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product_1.id,
            'inventory_quantity': 10.0,
            'location_id': warehouse_1.lot_stock_id.id,
        })

        # Update quantity of Product B in Warehouse 2
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product_2.id,
            'inventory_quantity': 10.0,
            'location_id': warehouse_2.lot_stock_id.id,
        })

        # Get current website and set warehouse_id of Warehouse 1
        current_website = self.env['website'].get_current_website()
        current_website.warehouse_id = warehouse_1

        product = product_1.with_context(website_id=current_website.id)
        combination_info = product.product_tmpl_id.with_context(website_sale_stock_get_quantity=True)._get_combination_info()

        # Check available quantity of product is according to warehouse
        self.assertEqual(combination_info['virtual_available'], 10, "10 units of Product A should be available in warehouse 1.")

        product = product_2.with_context(website_id=current_website.id)
        combination_info = product.product_tmpl_id.with_context(website_sale_stock_get_quantity=True)._get_combination_info()

        # Check available quantity of product is according to warehouse
        self.assertEqual(combination_info['virtual_available'], 0, "Product B should not be available in warehouse 1.")
