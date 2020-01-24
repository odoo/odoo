# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo.addons.sale.tests.test_sale_common import TestSaleCommon
from odoo.tests import tagged
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestSaleStockMultiCompany(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_B = cls.env['res.company'].create({'name': 'Company B'})
        cls.warehouse_A = cls.env['stock.warehouse'].create({'name': 'WH A', 'code': 'WHA', 'company_id': cls.env.company.id, 'partner_id': cls.env.company.partner_id.id})
        cls.warehouse_A2 = cls.env['stock.warehouse'].create({'name': 'WH A 2', 'code': 'WHA2', 'company_id': cls.env.company.id, 'partner_id': cls.env.company.partner_id.id, 'sequence': 5})
        cls.warehouse_B = cls.env['stock.warehouse'].create({'name': 'WH B', 'code': 'WHB', 'company_id': cls.company_B.id, 'partner_id': cls.company_B.partner_id.id})
        cls.warehouse_user = new_test_user(cls.env, 'WarehouseUser', groups='base.group_user,stock.group_stock_user,stock.group_stock_multi_locations,sales_team.group_sale_salesman', company_ids=[(6, 0, (cls.env.company | cls.company_B).ids)])
        cls.warehouse_user.with_company(cls.env.company).property_warehouse_id = cls.warehouse_A.id
        cls.warehouse_user.with_company(cls.company_B).property_warehouse_id = cls.warehouse_B.id

    def test_warehouse_definition_on_so(self):

        partner = self.partner
        product = self.products['prod_del']

        sale_order_vals = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'user_id': False,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 10,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        sale_order = self.env['sale.order']

        so_no_user = sale_order.create(sale_order_vals)
        self.assertFalse(so_no_user.user_id.property_warehouse_id)
        self.assertEqual(so_no_user.warehouse_id.id, self.warehouse_A2.id)

        sale_order_vals2 = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'user_id': self.warehouse_user.id,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 10,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        so_company_A = sale_order.with_company(self.env.company).create(sale_order_vals2)
        self.assertEqual(so_company_A.warehouse_id.id, self.warehouse_A.id)

        sale_order_vals3 = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'user_id': self.warehouse_user.id,
            'company_id': self.company_B.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 10,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        so_company_B = sale_order.with_company(self.company_B).create(sale_order_vals3)
        self.assertEqual(so_company_B.warehouse_id.id, self.warehouse_B.id)
