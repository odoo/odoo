# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_pos_accounting import TestPosAccounting
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


class TestPosAccountingStock(TestPosAccounting, ValuationReconciliationTestCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        warehouse = self.company_data['default_warehouse']
        self.location = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'location_id': warehouse.lot_stock_id.id,
        })
        self.adjust_inventory(
            [self.product_6, self.product_12, self.product_21],
            [100, 50, 50],
        )

    @classmethod
    def adjust_inventory(self, products, quantities):
        StockQuant = self.env['stock.quant']
        for product, qty in zip(products, quantities):
            StockQuant.with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': qty,
                'location_id': self.location.id,
            }).action_apply_inventory()

    def test_available_stock_order_no_invoice(self):
        start_product_6_qty = self.product_6.qty_available
        start_product_12_qty = self.product_12.qty_available
        start_product_21_qty = self.product_21.qty_available

        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 106}]],
            products=[[self.product_6, {'qty': 10}]],
            extra_data={'partner_id': self.partner_1.id},
        )
        self.assertFalse(order.account_move)
        self.assertEqual(order.picking_ids.state, 'done')
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 224}]],
            products=[[self.product_12, {'qty': 20}]],
            extra_data={'partner_id': self.partner_1.id},
        )
        self.assertFalse(order.account_move)
        self.assertEqual(order.picking_ids.state, 'done')
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 363}]],
            products=[[self.product_21, {'qty': 30}]],
            extra_data={'partner_id': self.partner_1.id},
        )
        self.assertFalse(order.account_move)
        self.assertEqual(order.picking_ids.state, 'done')
        self.close_session()

        product_6_qty = self.product_6.qty_available
        product_12_qty = self.product_12.qty_available
        product_21_qty = self.product_21.qty_available

        self.assertEqual(product_6_qty, start_product_6_qty - 10)
        self.assertEqual(product_12_qty, start_product_12_qty - 20)
        self.assertEqual(product_21_qty, start_product_21_qty - 30)

        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': -363}]],
            products=[[self.product_21, {'qty': -30}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'is_refund': True,
                'refunded_order_id': order.id,
            },
        )
        self.close_session()
        self.assertEqual(order.picking_ids.state, 'done')
        self.assertEqual(order.account_move.state, 'posted')
        product_21_qty = self.product_21.qty_available
        self.assertEqual(product_21_qty, start_product_21_qty)

    def test_available_stock_order_with_invoice(self):
        start_product_6_qty = self.product_6.qty_available
        start_product_12_qty = self.product_12.qty_available
        start_product_21_qty = self.product_21.qty_available

        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 106}]],
            products=[[self.product_6, {'qty': 10}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertTrue(order.account_move)
        self.assertEqual(order.picking_ids.state, 'done')
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 224}]],
            products=[[self.product_12, {'qty': 20}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertTrue(order.account_move)
        self.assertEqual(order.picking_ids.state, 'done')
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 363}]],
            products=[[self.product_21, {'qty': 30}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertTrue(order.account_move)
        self.assertEqual(order.picking_ids.state, 'done')
        self.close_session()

        product_6_qty = self.product_6.qty_available
        product_12_qty = self.product_12.qty_available
        product_21_qty = self.product_21.qty_available

        self.assertEqual(product_6_qty, start_product_6_qty - 10)
        self.assertEqual(product_12_qty, start_product_12_qty - 20)
        self.assertEqual(product_21_qty, start_product_21_qty - 30)

        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': -363}]],
            products=[[self.product_21, {'qty': -30}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'is_refund': True,
                'refunded_order_id': order.id,
            },
        )
        self.close_session()
        self.assertEqual(order.picking_ids.state, 'done')
        self.assertEqual(order.account_move.state, 'posted')
        product_21_qty = self.product_21.qty_available
        self.assertEqual(product_21_qty, start_product_21_qty)
