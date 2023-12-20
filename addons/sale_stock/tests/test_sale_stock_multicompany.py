# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleStockMultiCompany(TestSaleCommon, ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.warehouse_A = cls.company_data['default_warehouse']
        cls.warehouse_A2 = cls.env['stock.warehouse'].create({
            'name': 'WH B',
            'code': 'WHB',
            'company_id': cls.env.company.id,
            'partner_id': cls.env.company.partner_id.id,
        })
        cls.warehouse_B = cls.company_data_2['default_warehouse']

        cls.env.user.groups_id |= cls.env.ref('stock.group_stock_user')
        cls.env.user.groups_id |= cls.env.ref('stock.group_stock_multi_locations')
        cls.env.user.groups_id |= cls.env.ref('sales_team.group_sale_salesman')

        cls.env.user.with_company(cls.company_data['company']).property_warehouse_id = cls.warehouse_A.id
        cls.env.user.with_company(cls.company_data_2['company']).property_warehouse_id = cls.warehouse_B.id

    def test_warehouse_definition_on_so(self):

        partner = self.partner_a
        product = self.test_product_order

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
        }
        sale_order = self.env['sale.order']

        so_no_user = sale_order.create(sale_order_vals)
        self.assertFalse(so_no_user.user_id.property_warehouse_id)
        self.assertEqual(so_no_user.warehouse_id.id, self.warehouse_A.id)

        sale_order_vals2 = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 10,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
        }
        so_company_A = sale_order.with_company(self.env.company).create(sale_order_vals2)
        self.assertEqual(so_company_A.warehouse_id.id, self.warehouse_A.id)

        sale_order_vals3 = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'company_id': self.company_data_2['company'].id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 10,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
        }
        so_company_B = sale_order.with_company(self.company_data_2['company']).create(sale_order_vals3)
        self.assertEqual(so_company_B.warehouse_id.id, self.warehouse_B.id)
