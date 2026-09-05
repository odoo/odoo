# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductWarehouse(
    TestSaleProductAttributeValueCommon, WebsiteSaleStockCommon
):

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
        cls.warehouse_1 = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.company.id)
        ])
        cls.warehouse_2 = cls._create_warehouse()
        cls.product_A = cls._create_product()
        cls.product_B = cls._create_product()
        cls.test_env = cls.env['base'].with_context(
            website_id=cls.website.id,
            website_sale_stock_get_quantity=True,
        ).env

        # Add 10 Product A in WH1 and 15 Product 1 in WH2
        cls._add_product_qty_to_wh(cls.product_A.id, 10, cls.warehouse_1.lot_stock_id.id)
        cls._add_product_qty_to_wh(cls.product_A.id, 15, cls.warehouse_2.lot_stock_id.id)

        # Add 10 Product 2 in WH2
        cls._add_product_qty_to_wh(cls.product_B.id, 10, cls.warehouse_2.lot_stock_id.id)

    def test_get_combination_info_free_qty_when_warehouse_is_set(self):
        self.website.warehouse_id = self.warehouse_2
        combination_info = self.product_A.with_env(self.test_env)._get_combination_info_variant()
        self.assertEqual(combination_info['free_qty'], 15)
        combination_info = self.product_B.with_env(self.test_env)._get_combination_info_variant()
        self.assertEqual(combination_info['free_qty'], 10)

    def test_get_combination_info_free_qty_when_no_warehouse_is_set(self):
        self.website.warehouse_id = False
        combination_info = self.product_A.with_env(self.test_env)._get_combination_info_variant()
        self.assertEqual(combination_info['free_qty'], 25)
        combination_info = self.product_B.with_env(self.test_env)._get_combination_info_variant()
        self.assertEqual(combination_info['free_qty'], 10)

    def test_sold_out_with_a_variant_in_stock(self):
        """ A template is sold out only when all of its variants are, not when
        its first variant is. """
        attribute = self.env['product.attribute'].create({
            'name': 'Flavour',
            'value_ids': [
                Command.create({'name': 'Vanilla'}),
                Command.create({'name': 'Unflavored'}),
            ],
        })
        template = self.env['product.template'].create({
            'name': 'Protein',
            'is_storable': True,
            'allow_out_of_stock_order': False,
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute.id,
                'value_ids': [Command.set(attribute.value_ids.ids)],
            })],
        })
        self.website.warehouse_id = self.warehouse_1
        # Only the second variant is in stock.
        self._add_product_qty_to_wh(
            template.product_variant_ids[1].id, 10, self.warehouse_1.lot_stock_id.id
        )

        with MockRequest(self.env, website=self.website):
            self.assertFalse(template._is_sold_out())
            self.assertTrue(template._website_show_quick_add())

            self._add_product_qty_to_wh(
                template.product_variant_ids[1].id, 0, self.warehouse_1.lot_stock_id.id
            )
            template.invalidate_recordset()

            self.assertTrue(template._is_sold_out())
            self.assertFalse(template._website_show_quick_add())

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
            self.assertEqual(
                website_so.order_line.product_id.virtual_available,
                25,
                "This quantity should be based on all warehouses.",
            )

            values = so._cart_update(
                product_id=self.product_A.id, line_id=so.order_line.id, set_qty=30
            )
            self.assertTrue(values.get('warning', False))
            self.assertEqual(values.get('quantity'), 25)
