# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleStockMultiCompany(TestSaleCommon, ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

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

    def test_sale_product_from_parent_company(self):
        """
        Check that a product from a company can be sold by a branch
        and that the resulting move can be created.
        """
        parent_company = self.env.company
        branch_company = self.env['res.company'].create({
            'name': 'Branch Company',
            'parent_id': parent_company.id,
        })

        self.product_a.company_id = parent_company

        sale_order = self.env['sale.order'].with_company(branch_company).create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
            })],
        })

        sale_order.action_confirm()

        self.assertTrue(sale_order.picking_ids.move_ids)

    def test_intercompany_transfer_sale_order_workflow(self):
        company2 = self.company_data_2['company']

        so = self.env['sale.order'].create({
            'partner_id': company2.partner_id.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 5.0,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': self.product_a.list_price})],
        })
        so.action_confirm()

        picking = so.picking_ids

        # create another move
        self.env['stock.move'].create({
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'name': self.product_b.name,
            'product_id': self.product_b.id,
            'product_uom_qty': 1,
            'product_uom': self.product_b.uom_id.id,
            'quantity': 1,
        })

        # ensure we have to moves in the picking
        self.assertEqual(len(picking.move_ids), 2)

        # make the moves as picked
        picking.move_ids.picked = True

        picking.button_validate()

        # make sure an order line is created for the new stock move
        self.assertEqual(len(picking.sale_id.order_line), 2)
